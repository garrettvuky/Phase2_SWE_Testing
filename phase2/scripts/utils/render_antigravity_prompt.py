from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _bootstrap_import_path(workdir: Path) -> None:
    src_dir = (workdir / "src").resolve()
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _resolve_path(base: Path, value: Path) -> Path:
    candidate = value.expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _run_git_show(repo_path: Path, commit: str, rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/").strip("/")
    target = f"{commit}:{normalized}"
    completed = subprocess.run(
        ["git", "show", target],
        cwd=str(repo_path),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Unable to read '{target}' from {repo_path}: {detail}")
    return completed.stdout


def _resolve_case(case_input: str, workdir: Path) -> tuple[Any, str]:
    from phase2.cases import load_case, load_case_by_id

    candidate = Path(case_input).expanduser()
    if candidate.exists() or candidate.suffix.lower() == ".json" or "/" in case_input or "\\" in case_input:
        path = candidate if candidate.is_absolute() else (workdir / candidate)
        return load_case(path.resolve()), str(path.resolve())
    try:
        return load_case_by_id(case_input, workdir=workdir), f"<index:{case_input}>"
    except FileNotFoundError:
        fallback = (workdir / "cases" / case_input / "case.json").resolve()
        if fallback.exists():
            return load_case(fallback), str(fallback)
        raise


def _load_manifest_record(
    manifest_path: Path,
    dataset_id: str | None,
    repo_id: str,
    focal_file_path: str,
    test_file_path: str,
) -> dict[str, Any] | None:
    if not manifest_path.exists():
        return None

    best: dict[str, Any] | None = None
    for raw_line in manifest_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            continue
        if dataset_id and str(payload.get("dataset_id") or "").strip() == dataset_id:
            return payload
        same_repo = str(payload.get("repository_repo_id") or "").strip() == repo_id
        same_focal = str(payload.get("focal_file_path") or "").strip() == focal_file_path
        same_test = str(payload.get("test_file_path") or "").strip() == test_file_path
        if same_repo and same_focal and same_test:
            best = payload
    return best


def _read_failing_tests(path: Path | None) -> str:
    if path is None:
        return "[]"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(payload, indent=2, sort_keys=True)


def _replace_placeholders(template_text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    leftovers = sorted(set(re.findall(r"\{\{[A-Za-z0-9_]+\}\}", rendered)))
    return rendered, leftovers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render Antigravity system prompt from a case and repository sources."
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path.cwd(),
        help="Workspace root (default: current directory).",
    )
    parser.add_argument(
        "--case",
        required=True,
        help="Case ID from cases/index/cases.jsonl or path to case.json.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("phase2/sync/regenerative_evosuite/prompts/antigravity_system_prompt.txt"),
        help="Prompt template path (default: phase2/sync/regenerative_evosuite/prompts/antigravity_system_prompt.txt).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Rendered prompt output path. Defaults to phase2/sync/regenerative_evosuite/prompts/rendered/<case_id>.txt.",
    )
    parser.add_argument(
        "--repos-root",
        type=Path,
        default=Path("repos"),
        help="Repos root path (default: repos).",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=None,
        help="Optional explicit repository path for this case (overrides repo-index/repos-root lookup).",
    )
    parser.add_argument(
        "--repo-index",
        type=Path,
        default=Path("phase2/data/processed/repo_index.json"),
        help="Repo index path (default: phase2/data/processed/repo_index.json).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("phase2/data/processed/manifest.jsonl"),
        help="Manifest path used to resolve class identifiers (default: phase2/data/processed/manifest.jsonl).",
    )
    parser.add_argument(
        "--failing-tests-json",
        type=Path,
        default=None,
        help="Optional JSON file containing failing tests to embed.",
    )
    parser.add_argument(
        "--allow-unresolved-placeholders",
        action="store_true",
        help="Allow output even if template placeholders remain unresolved.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workdir = args.workdir.expanduser().resolve()
    _bootstrap_import_path(workdir)

    from phase2.repo import resolve_repo_path

    case, case_source = _resolve_case(args.case, workdir=workdir)
    if args.repo_path is not None:
        repo_path = _resolve_path(workdir, args.repo_path)
    else:
        repo_path = resolve_repo_path(
            workdir=workdir,
            repo_id=case.repo_id,
            repos_root=args.repos_root,
            index_path=args.repo_index,
        )
        if not (repo_path / ".git").exists():
            fallback_repo = _resolve_path(workdir, args.repos_root) / str(case.repo_id)
            if (fallback_repo / ".git").exists():
                repo_path = fallback_repo
    if not (repo_path / ".git").exists():
        raise FileNotFoundError(f"Repository clone for repo_id={case.repo_id} not found: {repo_path}")

    template_path = _resolve_path(workdir, args.template)
    template_text = template_path.read_text(encoding="utf-8")

    manifest_path = _resolve_path(workdir, args.manifest)
    metadata = case.metadata if isinstance(case.metadata, dict) else {}
    dataset_id = str(metadata.get("record_id") or "").strip() or None
    manifest_record = _load_manifest_record(
        manifest_path=manifest_path,
        dataset_id=dataset_id,
        repo_id=case.repo_id,
        focal_file_path=case.focal_file_path,
        test_file_path=case.test_file_path,
    )

    focal_class_identifier = (
        str((manifest_record or {}).get("focal_class_identifier") or "").strip()
        or Path(case.focal_file_path).stem
    )
    test_class_identifier = (
        str((manifest_record or {}).get("test_class_identifier") or "").strip()
        or Path(case.test_file_path).stem
    )

    focal_source = _run_git_show(repo_path=repo_path, commit=case.modified_commit, rel_path=case.focal_file_path)
    test_source = _run_git_show(repo_path=repo_path, commit=case.modified_commit, rel_path=case.test_file_path)
    failing_tests_json = _read_failing_tests(
        _resolve_path(workdir, args.failing_tests_json) if args.failing_tests_json else None
    )
    build_commands = "\n".join(case.build_commands)

    values = {
        "repo_id": str(case.repo_id),
        "case_id": str(case.case_id),
        "base_commit": str(case.base_commit),
        "modified_commit": str(case.modified_commit),
        "focal_class_identifier": focal_class_identifier,
        "focal_file_path": str(case.focal_file_path),
        "mapped_focal_method": str(case.mapped_focal_method),
        "test_class_identifier": test_class_identifier,
        "test_file_path": str(case.test_file_path),
        "mapped_test_method": str(case.mapped_test_method),
        "failing_tests_json": failing_tests_json,
        "build_commands": build_commands,
        "focal_class_source": focal_source,
        "test_class_source": test_source,
    }
    rendered, leftovers = _replace_placeholders(template_text, values)
    if leftovers and not args.allow_unresolved_placeholders:
        raise ValueError(
            "Unresolved placeholders in rendered template: "
            + ", ".join(leftovers)
            + ". Use --allow-unresolved-placeholders to bypass."
        )

    if args.output is None:
        output_path = workdir / "phase2" / "sync" / "regenerative_evosuite" / "prompts" / "rendered" / f"{case.case_id}.txt"
    else:
        output_path = _resolve_path(workdir, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    receipt = {
        "status": "ok",
        "case_source": case_source,
        "repo_path": str(repo_path),
        "template_path": str(template_path),
        "output_path": str(output_path),
        "manifest_record_found": manifest_record is not None,
        "focal_class_identifier": focal_class_identifier,
        "test_class_identifier": test_class_identifier,
        "embedded_failing_tests_path": str(_resolve_path(workdir, args.failing_tests_json))
        if args.failing_tests_json
        else None,
        "unresolved_placeholders": leftovers,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
