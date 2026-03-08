import csv
import json
import os
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv


FAILED_DIR = Path("./failed_classes")
DEFAULT_HEALING_LIMIT = 5


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _benchmark_csv_path() -> Path:
    return _project_root() / "artifacts" / "benchmark" / "benchmark_outcomes.csv"


def _summary_root() -> Path:
    return _project_root() / "artifacts" / "benchmark" / "gemini_agentic"


def _default_gemini_command() -> str:
    raw = os.getenv("GEMINI_CLI_COMMAND")
    if raw and raw.strip():
        return raw.strip()
    return "gemini.cmd" if os.name == "nt" else "gemini"


def _gemini_command_prefix() -> list[str]:
    raw = _default_gemini_command()
    return shlex.split(raw, posix=(os.name != "nt"))


def _extract_json_objects(stdout: str) -> list[dict]:
    payloads: list[dict] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            payloads.append(parsed)
    if not payloads:
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                payloads.append(parsed)
        except json.JSONDecodeError:
            pass
    return payloads


def _collect_text_values(value) -> list[str]:
    texts: list[str] = []
    if isinstance(value, str):
        texts.append(value)
        return texts
    if isinstance(value, list):
        for item in value:
            texts.extend(_collect_text_values(item))
        return texts
    if isinstance(value, dict):
        for key, nested in value.items():
            key_lower = str(key).lower()
            if key_lower in {"text", "content", "output", "response", "message"}:
                texts.extend(_collect_text_values(nested))
            else:
                texts.extend(_collect_text_values(nested))
        return texts
    return texts


def _first_int(patterns: list[str], text: str):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _first_float(patterns: list[str], text: str):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _extract_telemetry(stdout: str, stderr: str, payloads: list[dict], elapsed_seconds: float) -> dict:
    merged = "\n".join([stdout, stderr])
    prompt_tokens = _first_int(
        [
            r"prompt[_\s-]*tokens?[^0-9]*(\d+)",
            r"input[_\s-]*tokens?[^0-9]*(\d+)",
        ],
        merged,
    )
    completion_tokens = _first_int(
        [
            r"completion[_\s-]*tokens?[^0-9]*(\d+)",
            r"output[_\s-]*tokens?[^0-9]*(\d+)",
        ],
        merged,
    )
    total_tokens = _first_int([r"total[_\s-]*tokens?[^0-9]*(\d+)"], merged)
    response_seconds = _first_float(
        [
            r"response[_\s-]*time[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*ms",
            r"latency[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*ms",
        ],
        merged,
    )
    if response_seconds is not None:
        response_seconds = round(response_seconds / 1000.0, 6)
    else:
        response_seconds = _first_float(
            [
                r"response[_\s-]*time[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*s",
                r"latency[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*s",
            ],
            merged,
        )

    for payload in payloads:
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
            completion_tokens = usage.get("completion_tokens", completion_tokens)
            total_tokens = usage.get("total_tokens", total_tokens)
            if response_seconds is None:
                ms = usage.get("response_ms")
                if isinstance(ms, (int, float)):
                    response_seconds = round(float(ms) / 1000.0, 6)

    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = int(prompt_tokens) + int(completion_tokens)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "response_seconds": response_seconds if response_seconds is not None else round(elapsed_seconds, 6),
        "raw_stdout": stdout,
        "raw_stderr": stderr,
    }


def _strip_markdown_fence(text: str) -> str:
    if not text:
        return text
    match = re.search(r"```(?:java)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def _ensure_package_and_class_name(code: str, test_class_name: str, package_name=None) -> str:
    cleaned = _strip_markdown_fence(code)
    class_match = re.search(r"\bclass\s+([A-Za-z_]\w*)", cleaned)
    if class_match and class_match.group(1) != test_class_name:
        cleaned = re.sub(
            r"\bclass\s+([A-Za-z_]\w*)",
            f"class {test_class_name}",
            cleaned,
            count=1,
        )

    if package_name:
        package_pattern = re.compile(r"^\s*package\s+[\w.]+\s*;", re.MULTILINE)
        if package_pattern.search(cleaned) is None:
            cleaned = f"package {package_name};\n\n{cleaned}"

    return cleaned


def _extract_package_name(java_source: str):
    if not java_source:
        return None
    match = re.search(r"^\s*package\s+([\w.]+)\s*;", java_source, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def _validate_and_normalize_healing_candidate(candidate: str, expected_class_name: str, package_name=None):
    normalized = _ensure_package_and_class_name(candidate, expected_class_name, package_name).strip()
    if not normalized:
        return None, "empty_candidate"
    if "```" in normalized:
        return None, "contains_markdown_fence"
    if normalized.lstrip().startswith("<"):
        return None, "looks_like_xml_or_non_java"
    if re.search(r"\b(class|interface|enum)\s+[A-Za-z_]\w*", normalized) is None:
        return None, "missing_java_type_declaration"
    return normalized, None


def _run_gemini_cli(prompt: str, stdin_text=None, timeout_seconds=None) -> dict:
    timeout = timeout_seconds or int(os.getenv("GEMINI_TIMEOUT_SECONDS", "240"))
    command = _gemini_command_prefix() + ["--yolo", "--output-format", "json", "--prompt", prompt]
    model = os.getenv("GEMINI_MODEL")
    if model:
        command.extend(["--model", model])
    # Keep Gemini credentials available even if parent code changed env state.
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    env = os.environ.copy()

    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "code": None,
            "text": "",
            "error": f"timeout_after_seconds:{timeout}",
            "returncode": -1,
            "telemetry": {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "response_seconds": round(time.monotonic() - started, 6),
                "raw_stdout": exc.stdout or "",
                "raw_stderr": exc.stderr or "",
            },
        }

    elapsed = time.monotonic() - started
    payloads = _extract_json_objects(result.stdout or "")
    text_fragments: list[str] = []
    for payload in payloads:
        text_fragments.extend(_collect_text_values(payload))
    if not text_fragments:
        text_fragments = [result.stdout or ""]

    text_output = "\n".join(fragment for fragment in text_fragments if fragment).strip()
    telemetry = _extract_telemetry(result.stdout or "", result.stderr or "", payloads, elapsed)
    error_message = None
    if result.returncode != 0:
        error_message = (result.stderr or result.stdout or "").strip()
    else:
        for payload in payloads:
            payload_error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(payload_error, dict):
                error_message = str(payload_error.get("message") or payload_error)
                break

    return {
        "success": result.returncode == 0 and bool(text_output),
        "code": _strip_markdown_fence(text_output) if text_output else None,
        "text": text_output,
        "error": error_message,
        "returncode": result.returncode,
        "telemetry": telemetry,
    }


def _summarize_telemetry(records: list[dict]) -> dict:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    total_seconds = 0.0
    has_prompt = False
    has_completion = False
    has_total = False
    for record in records:
        pt = record.get("prompt_tokens")
        ct = record.get("completion_tokens")
        tt = record.get("total_tokens")
        rs = record.get("response_seconds")
        if isinstance(pt, int):
            prompt_tokens += pt
            has_prompt = True
        if isinstance(ct, int):
            completion_tokens += ct
            has_completion = True
        if isinstance(tt, int):
            total_tokens += tt
            has_total = True
        if isinstance(rs, (int, float)):
            total_seconds += float(rs)
    if not has_total and has_prompt and has_completion:
        total_tokens = prompt_tokens + completion_tokens
        has_total = True
    return {
        "prompt_tokens": prompt_tokens if has_prompt else None,
        "completion_tokens": completion_tokens if has_completion else None,
        "total_tokens": total_tokens if has_total else None,
        "response_seconds": round(total_seconds, 6),
    }


def _collect_jacoco_coverage(project_path: str) -> dict:
    root = Path(project_path)
    if not root.exists():
        return {"line_coverage_pct": None, "branch_coverage_pct": None, "method_coverage_pct": None}

    counters = {
        "LINE": [0, 0],
        "BRANCH": [0, 0],
        "METHOD": [0, 0],
    }
    xml_files = list(root.rglob("jacoco.xml"))
    for xml_path in xml_files:
        try:
            report = ET.parse(xml_path).getroot()
        except ET.ParseError:
            continue
        for counter in report.findall("./counter"):
            counter_type = counter.attrib.get("type")
            if counter_type not in counters:
                continue
            missed = int(counter.attrib.get("missed", 0))
            covered = int(counter.attrib.get("covered", 0))
            counters[counter_type][0] += missed
            counters[counter_type][1] += covered

    def pct(missed_covered: list[int]):
        missed, covered = missed_covered
        total = missed + covered
        if total == 0:
            return None
        return round((covered / total) * 100.0, 4)

    return {
        "line_coverage_pct": pct(counters["LINE"]),
        "branch_coverage_pct": pct(counters["BRANCH"]),
        "method_coverage_pct": pct(counters["METHOD"]),
    }


def _write_summary_file(project: str, track: str, test_class_name: str, payload: dict) -> str:
    summary_dir = _summary_root() / str(project) / track
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{test_class_name}.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(summary_path)


def _append_benchmark_row(row: dict) -> None:
    csv_path = _benchmark_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    existing_rows: list[dict] = []
    headers: list[str] = []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            existing_rows = [dict(item) for item in reader]

    for key in row.keys():
        if key not in headers:
            headers.append(key)
    if not headers:
        headers = list(row.keys())

    normalized_existing: list[dict] = []
    for item in existing_rows:
        normalized_existing.append({header: item.get(header, "") for header in headers})
    normalized_existing.append({header: row.get(header, "") for header in headers})

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(normalized_existing)


def log_track_outcome(
    project: str,
    test_type: str,
    technique: str,
    track: str,
    test_path: str,
    project_path: str,
    success: bool,
    stop_reason: str,
    error,
    telemetry_records: list[dict],
    iterations: int,
) -> str:
    telemetry = _summarize_telemetry(telemetry_records)
    coverage = _collect_jacoco_coverage(project_path)
    test_class_name = Path(test_path).stem
    summary_payload = {
        "generated_at_utc": _utc_now_iso(),
        "project": str(project),
        "test_type": test_type,
        "technique": technique,
        "track": track,
        "test_path": test_path,
        "success": bool(success),
        "stop_reason": stop_reason,
        "error": error,
        "iterations": iterations,
        "telemetry": telemetry,
        "coverage": coverage,
        "per_iteration": telemetry_records,
    }
    summary_path = _write_summary_file(str(project), track, test_class_name, summary_payload)

    row = {
        "case_id": f"{project}_{test_class_name}",
        "repo_id": str(project),
        "approach": f"agone_{track}",
        "status": "ok" if success else ("error" if error else "fail"),
        "success": bool(success),
        "duration_seconds": telemetry.get("response_seconds"),
        "stop_reason": stop_reason,
        "error": error or "",
        "summary_path": summary_path,
        "timestamp_utc": _utc_now_iso(),
        "project": str(project),
        "test_type": test_type,
        "technique": technique,
        "track": track,
        "test_path": test_path,
        "iterations": iterations,
        "prompt_tokens": telemetry.get("prompt_tokens"),
        "completion_tokens": telemetry.get("completion_tokens"),
        "total_tokens": telemetry.get("total_tokens"),
        "line_coverage_pct": coverage.get("line_coverage_pct"),
        "branch_coverage_pct": coverage.get("branch_coverage_pct"),
        "method_coverage_pct": coverage.get("method_coverage_pct"),
    }
    _append_benchmark_row(row)
    return summary_path


def generate_regenerative_test(
    focal_path: str,
    focal_class: str,
    name_test_class: str,
    package_test_class=None,
    java_version=None,
    testing_framework=None,
) -> tuple[str | None, dict]:
    constraints = []
    if java_version:
        constraints.append(
            f"Target Java version is {java_version}. Do not use language features newer than this version."
        )
    if testing_framework:
        constraints.append(f"Use {testing_framework}.")
    constraints_text = " ".join(constraints).strip()
    prompt = " ".join(
        part for part in [
            "Read this source code and write a brand new JUnit test from scratch to cover the focal method.",
            constraints_text,
            "Output only the code.",
        ] if part
    )
    input_payload = f"=== SOURCE_FILE ({focal_path}) ===\n{focal_class}\n"
    result = _run_gemini_cli(prompt=prompt, stdin_text=input_payload)
    telemetry = [result.get("telemetry", {})]
    if not result.get("success") or not result.get("code"):
        return None, {"telemetry": telemetry, "error": result.get("error")}
    code = _ensure_package_and_class_name(result["code"], name_test_class, package_test_class)
    return code, {"telemetry": telemetry, "error": result.get("error")}


def correct_errors(
    project,
    test_type,
    technique,
    test_path,
    project_path,
    project_df,
    system,
    messages,
    errori,
    dictionary_for_restore,
    chance,
    type_project,
):
    print(f"Package command failed for project: {project}, test type: {test_type}, technique: {technique}\n")
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    save_class(test_path, "_failed", str(FAILED_DIR))

    current_error = errori or "Compilation failed but no stderr details were captured."
    max_iterations = int(os.getenv("GEMINI_HEALING_MAX_ITERS", str(DEFAULT_HEALING_LIMIT)))
    telemetry_records: list[dict] = []

    original_content = dictionary_for_restore.get(test_path)
    if original_content is None and os.path.exists(test_path):
        with open(test_path, "r", encoding="utf-8", errors="replace") as handle:
            original_content = handle.read()

    if type_project == "Maven":
        import mavenLib
        runner = mavenLib.run_maven_test_command
    else:
        import gradleLib
        runner = gradleLib.run_gradle_test_command

    iterations_used = 0
    for iteration in range(1, max_iterations + 1):
        iterations_used = iteration
        try:
            broken_test = Path(test_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            current_error = f"Cannot read broken test file: {exc}"
            break
        package_test_class = _extract_package_name(broken_test)

        prompt = (
            "You are an autonomous AI. Read this compiler error and the test file. "
            "Apply a localized fix to resolve the error. Output the fixed code."
        )
        input_payload = (
            "=== BrokenTest.java ===\n"
            f"{broken_test}\n\n"
            "=== stderr.log ===\n"
            f"{current_error}\n"
        )
        result = _run_gemini_cli(prompt=prompt, stdin_text=input_payload)
        telemetry = result.get("telemetry", {})
        telemetry["iteration"] = iteration
        telemetry_records.append(telemetry)

        candidate = result.get("code")
        if not candidate:
            current_error = result.get("error") or current_error
            continue

        normalized_candidate, validation_error = _validate_and_normalize_healing_candidate(
            candidate,
            expected_class_name=Path(test_path).stem,
            package_name=package_test_class,
        )
        if validation_error:
            telemetry["validation_error"] = validation_error
            current_error = (
                f"Healing iteration {iteration} produced invalid non-code output "
                f"({validation_error}). Previous compiler error:\n{current_error}"
            )
            continue

        Path(test_path).write_text(normalized_candidate, encoding="utf-8")
        save_class(test_path, f"_processed_iter{iteration}", str(FAILED_DIR))

        build_outcome = runner(project_path, project_df, system)
        if isinstance(build_outcome, tuple):
            build_success = bool(build_outcome[0])
            current_error = build_outcome[1]
        else:
            build_success = bool(build_outcome)
            current_error = None

        if build_success:
            save_class(test_path, "_corrected", str(FAILED_DIR))
            log_track_outcome(
                project=project,
                test_type=test_type,
                technique=technique,
                track="iterative_healing",
                test_path=test_path,
                project_path=project_path,
                success=True,
                stop_reason="build_success",
                error=None,
                telemetry_records=telemetry_records,
                iterations=iteration,
            )
            return True, None, {
                "iterations_used": iteration,
                "telemetry": telemetry_records,
            }

    if original_content is not None:
        Path(test_path).write_text(original_content, encoding="utf-8")

    log_track_outcome(
        project=project,
        test_type=test_type,
        technique=technique,
        track="iterative_healing",
        test_path=test_path,
        project_path=project_path,
        success=False,
        stop_reason="iteration_limit_reached",
        error=current_error,
        telemetry_records=telemetry_records,
        iterations=iterations_used,
    )
    return False, current_error, {
        "iterations_used": iterations_used,
        "telemetry": telemetry_records,
    }


def record_regenerative_outcome(
    project,
    test_type,
    technique,
    test_path,
    project_path,
    success,
    error,
    telemetry_records,
):
    return log_track_outcome(
        project=project,
        test_type=test_type,
        technique=technique,
        track="regenerative",
        test_path=test_path,
        project_path=project_path,
        success=bool(success),
        stop_reason="build_success" if success else "build_failed",
        error=error,
        telemetry_records=telemetry_records or [],
        iterations=1,
    )


def save_class(test_path, suffix, save_dir):
    filename = os.path.basename(test_path).replace(".java", f"{suffix}.java")
    save_path = os.path.join(save_dir, filename)
    with open(test_path, "r", encoding="utf-8", errors="replace") as test_file:
        content = test_file.read()
    with open(save_path, "w", encoding="utf-8") as output_file:
        output_file.write(content)
    return save_path


def restore_original_class(test_path, dictionary_for_restore):
    with open(test_path, "w", encoding="utf-8") as test_file_write:
        test_file_write.write(dictionary_for_restore[test_path])


def extract_errors(stdout: str, stderr: str):
    error_pattern = re.compile(r"\[ERROR\] COMPILATION ERROR :(.*?)(?=\[INFO\] \d+ error)", re.DOTALL)
    errors = error_pattern.findall(stdout)

    if errors:
        cleaned_errors = errors[0].strip()
        cleaned_lines = [
            line.replace("[INFO] -------------------------------------------------------------", "")
            .replace("[ERROR]", "")
            .strip()
            for line in cleaned_errors.splitlines()
            if line.strip()
        ]
        formatted_errors = "The following compilation errors were encountered during the Maven build:\n"
        formatted_errors += "\n- " + "\n- ".join(cleaned_lines)
    else:
        cleaned_stderr = [line.strip() for line in stderr.splitlines() if line.strip() and "[ERROR]" in line]

        if cleaned_stderr:
            formatted_errors = "The following errors were encountered during the Maven build (from stderr):\n"
            formatted_errors += "\n- " + "\n- ".join(cleaned_stderr)
        else:
            error_lines = []
            capturing = False
            for line in stdout.splitlines():
                if "[ERROR]" in line:
                    capturing = True
                    error_lines.append(line.replace("[ERROR]", "").strip())
                elif capturing:
                    if "[INFO]" in line:
                        capturing = False
                    else:
                        error_lines.append(line.strip())

            if error_lines:
                formatted_errors = "The following general errors were encountered during the Maven build:\n"
                formatted_errors += "\n- " + "\n- ".join(error_lines)
            else:
                formatted_errors = "No compilation errors or general issues found in the Maven output."

    return formatted_errors


def extract_gradle_errors(stdout: str, stderr: str):
    error_pattern = re.compile(r"> Task :(.*?):.*?FAILED", re.DOTALL)
    errors = error_pattern.findall(stdout)

    if errors:
        formatted_errors = "The following task errors were encountered during the Gradle build:\n"
        formatted_errors += "\n- " + "\n- ".join(errors)
    else:
        cleaned_stderr = [
            line.strip()
            for line in stderr.splitlines()
            if line.strip() and ("[ERROR]" in line or "FAILED" in line)
        ]

        if cleaned_stderr:
            formatted_errors = "The following errors were encountered during the Gradle build (from stderr):\n"
            formatted_errors += "\n- " + "\n- ".join(cleaned_stderr)
        else:
            error_lines = []
            capturing = False
            for line in stdout.splitlines():
                if "[ERROR]" in line or "FAILED" in line:
                    capturing = True
                    error_lines.append(line.replace("[ERROR]", "").strip())
                elif capturing:
                    if "[INFO]" in line:
                        capturing = False
                    else:
                        error_lines.append(line.strip())

            if error_lines:
                formatted_errors = "The following general errors were encountered during the Gradle build:\n"
                formatted_errors += "\n- " + "\n- ".join(error_lines)
            else:
                formatted_errors = "No compilation errors or general issues found in the Gradle output."

    return formatted_errors


def save_conversation_to_json(messages, class_name, save_path="."):
    file_name = f"conversation_{class_name}.json"
    full_path = os.path.join(save_path, file_name)
    conversation_data = []
    for index, message in enumerate(messages):
        role = message.get("role", "unknown").capitalize()
        content = message.get("content", "")
        conversation_data.append(
            {
                "message_number": index + 1,
                "role": role,
                "content": content,
            }
        )
    os.makedirs(save_path, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as file:
        json.dump(conversation_data, file, indent=2)
    return full_path
