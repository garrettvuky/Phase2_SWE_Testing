import csv
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd


def strict_checks_enabled() -> bool:
    raw = str(os.environ.get("AGONE_STRICT_POST_BUILD", "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _module_value(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text.replace("\\", "/")


def _normalize_repo_path(raw_path: str | None) -> str | None:
    if raw_path is None:
        return None
    text = str(raw_path).strip().replace("\\", "/")
    if not text:
        return None
    marker = "compiledrepos/"
    idx = text.find(marker)
    if idx >= 0:
        return text[idx:]
    if text.startswith("repos/"):
        return "compiledrepos/" + text[len("repos/") :]
    return text


def _resolve_path(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    p = Path(path_text)
    if p.exists():
        return p
    p2 = (Path.cwd() / path_text).resolve()
    if p2.exists():
        return p2
    return p2


def _records(project_dataframe) -> list[dict]:
    df = project_dataframe.copy()
    normalized: list[dict] = []
    seen: set[tuple] = set()
    for _, row in df.iterrows():
        record = {
            "focal_class": str(row.get("Focal_Class", "")).strip(),
            "test_class": str(row.get("Test_Class", "")).strip(),
            "focal_path": _normalize_repo_path(row.get("Focal_Path")),
            "test_path": _normalize_repo_path(row.get("Test_Path")),
            "module": _module_value(row.get("Module")),
        }
        key = (
            record["focal_class"],
            record["test_class"],
            record["focal_path"],
            record["test_path"],
            record["module"],
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(record)
    return normalized


def _to_test_fqcn(test_path: str | None, fallback_test_class: str | None) -> str | None:
    if not test_path:
        return fallback_test_class
    normalized = test_path.replace("\\", "/")
    marker = "test/java/"
    if marker in normalized:
        rel = normalized.split(marker, 1)[1]
        return rel.replace("/", ".").replace(".java", "")
    return fallback_test_class


def _is_valid_java_test_source(content: str, expected_class_name: str) -> tuple[bool, str | None]:
    text = (content or "").strip()
    if not text:
        return False, "empty_test_source"
    if "```" in text:
        return False, "contains_markdown_fence"

    class_pattern = re.compile(
        rf"^\s*(?:public|protected|private|abstract|final|static|\s)*(class|interface|enum)\s+{re.escape(expected_class_name)}\b",
        re.MULTILINE,
    )
    class_match = class_pattern.search(text)
    if class_match is None:
        return False, f"missing_type_declaration:{expected_class_name}"

    preamble = text[: class_match.start()]
    for line in preamble.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if stripped.startswith("package ") or stripped.startswith("import ") or stripped.startswith("@"):
            continue
        return False, f"non_java_preamble:{stripped[:80]}"

    return True, None


def validate_generated_tests(project_dataframe) -> list[str]:
    errors: list[str] = []
    for rec in _records(project_dataframe):
        test_class = rec["test_class"]
        test_path = _resolve_path(rec["test_path"])
        if test_path is None or not test_path.exists():
            errors.append(f"Missing generated test file: {rec['test_path']}")
            continue
        try:
            source = test_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"Cannot read generated test file {test_path}: {exc}")
            continue
        ok, reason = _is_valid_java_test_source(source, test_class or test_path.stem)
        if not ok:
            errors.append(f"Invalid Java test source for {test_path}: {reason}")
    return errors


def _module_root(path: Path, module: str) -> Path:
    return path / module if module else path


def _maven_surefire_reports(module_root: Path, fqcn: str) -> list[Path]:
    expected = module_root / "target" / "surefire-reports" / f"TEST-{fqcn}.xml"
    if expected.exists():
        return [expected]
    return list(module_root.rglob(f"TEST-{fqcn}.xml"))


def _gradle_test_reports(module_root: Path, fqcn: str) -> list[Path]:
    expected = module_root / "build" / "test-results" / "test" / f"TEST-{fqcn}.xml"
    if expected.exists():
        return [expected]
    return list(module_root.rglob(f"TEST-{fqcn}.xml"))


def _jacoco_candidates(module_root: Path, build_tool: str) -> list[Path]:
    if build_tool == "maven":
        base = [
            module_root / "target" / "site" / "jacoco" / "jacoco.csv",
            module_root / "target" / "site" / "jacoco-ut" / "jacoco.csv",
        ]
    else:
        base = [
            module_root / "build" / "reports" / "jacoco" / "jacoco.csv",
            module_root / "build" / "reports" / "jacoco-ut" / "jacoco.csv",
        ]
    return [p for p in base if p.exists()]


def _pit_candidates(module_root: Path, build_tool: str) -> list[Path]:
    if build_tool == "maven":
        return list((module_root / "target" / "pit-reports").glob("**/mutations.csv"))
    return list((module_root / "build" / "reports" / "pitest").glob("**/mutations.csv"))


def _sum_tests(report_paths: list[Path]) -> int:
    total_tests = 0
    for report in report_paths:
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError:
            continue
        tests_attr = root.attrib.get("tests")
        try:
            total_tests += int(tests_attr) if tests_attr is not None else 0
        except ValueError:
            continue
    return total_tests


def validate_post_build(path: str, project_dataframe, build_tool: str) -> tuple[bool, list[str]]:
    root = Path(path)
    records = _records(project_dataframe)
    errors: list[str] = []

    for rec in records:
        module_root = _module_root(root, rec["module"])
        fqcn = _to_test_fqcn(rec["test_path"], rec["test_class"])
        if not fqcn:
            errors.append(f"Cannot infer test FQCN for {rec['test_path']}")
            continue

        if build_tool == "maven":
            reports = _maven_surefire_reports(module_root, fqcn)
        else:
            reports = _gradle_test_reports(module_root, fqcn)

        if not reports:
            errors.append(f"No test report found for {fqcn}")
            continue
        tests_run = _sum_tests(reports)
        if tests_run <= 0:
            errors.append(f"No tests executed for {fqcn} (tests=0)")

    for rec in records:
        module_root = _module_root(root, rec["module"])
        focal_class = rec["focal_class"]
        jacoco_files = _jacoco_candidates(module_root, build_tool)
        if not jacoco_files:
            errors.append(f"No JaCoCo CSV report for focal class {focal_class}")
            continue

        found_row = False
        covered_lines = 0
        for csv_path in jacoco_files:
            try:
                jacoco_df = pd.read_csv(csv_path)
            except Exception:
                continue
            if "CLASS" not in jacoco_df.columns:
                continue
            focal_rows = jacoco_df[jacoco_df["CLASS"] == focal_class]
            if focal_rows.empty:
                continue
            found_row = True
            line_covered = pd.to_numeric(focal_rows.get("LINE_COVERED"), errors="coerce").fillna(0).sum()
            covered_lines += int(line_covered)

        if not found_row:
            errors.append(f"JaCoCo missing focal class row: {focal_class}")
        elif covered_lines <= 0:
            errors.append(f"JaCoCo LINE_COVERED is 0 for focal class {focal_class}")

    for rec in records:
        module_root = _module_root(root, rec["module"])
        focal_file = f"{rec['focal_class']}.java"
        pit_files = _pit_candidates(module_root, build_tool)
        if not pit_files:
            errors.append(f"MUTATION_NOT_AVAILABLE: no PIT report for focal class {rec['focal_class']}")
            continue

        found_focal = False
        for pit_csv in pit_files:
            try:
                with pit_csv.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                    reader = csv.reader(handle)
                    for row in reader:
                        if row and row[0].strip() == focal_file:
                            found_focal = True
                            break
                if found_focal:
                    break
            except OSError:
                continue

        if not found_focal:
            errors.append(
                f"MUTATION_NOT_AVAILABLE: PIT report has no focal rows for {rec['focal_class']} ({focal_file})"
            )

    return len(errors) == 0, errors
