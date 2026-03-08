import argparse
import csv
import json
import os
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare AgoneTest native inputs (compiledrepos + output/classes.csv) from AST mapping outputs."
    )
    parser.add_argument("--repos-dir", default="repos", help="Source repositories directory.")
    parser.add_argument("--compiledrepos-dir", default="compiledrepos", help="Target compiledrepos path.")
    parser.add_argument("--mapping-dir", default="artifacts/mapping", help="Directory of mapping JSON files.")
    parser.add_argument("--output-csv", default="output/classes.csv", help="Output CSV path for AgoneTest.")
    parser.add_argument(
        "--overwrite-csv",
        action="store_true",
        help="Overwrite existing classes.csv instead of appending/deduplicating.",
    )
    return parser.parse_args()


def _relative_repo_path(raw_path: str, repo_id: str, repos_dir: Path) -> str | None:
    normalized = str(raw_path or "").replace("\\", "/")
    marker = f"/repos/{repo_id}/"
    if marker in normalized:
        rel = normalized.split(marker, 1)[1].strip("/")
        return f"repos/{repo_id}/{rel}" if rel else None

    candidate = Path(raw_path)
    repo_root = (repos_dir / repo_id).resolve()
    try:
        rel = candidate.resolve().relative_to(repo_root)
    except Exception:
        return None
    rel_str = rel.as_posix().strip("/")
    return f"repos/{repo_id}/{rel_str}" if rel_str else None


def _infer_module(relative_path: str) -> str | None:
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("repos/"):
        parts = normalized.split("/")[2:]
    else:
        parts = normalized.split("/")
    if "src" not in parts:
        return None
    src_index = parts.index("src")
    if src_index <= 0:
        return None
    module = "/".join(parts[:src_index]).strip("/")
    return module or None


def _ensure_compiledrepos_link(repos_dir: Path, compiledrepos_dir: Path) -> None:
    if compiledrepos_dir.exists():
        return

    try:
        os.symlink(repos_dir.resolve(), compiledrepos_dir, target_is_directory=True)
        print(f"[LINK] Created symlink: {compiledrepos_dir} -> {repos_dir}")
        return
    except OSError:
        pass

    if os.name == "nt":
        command = ["cmd", "/c", "mklink", "/J", str(compiledrepos_dir), str(repos_dir.resolve())]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[LINK] Created directory junction: {compiledrepos_dir} -> {repos_dir}")
            return

    raise RuntimeError(
        f"Unable to create compiledrepos link at {compiledrepos_dir}. "
        f"Create it manually as a symlink/junction to {repos_dir}."
    )


def _load_existing_rows(output_csv: Path) -> list[dict]:
    if not output_csv.exists():
        return []
    with output_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def main() -> None:
    args = parse_args()
    workdir = Path.cwd()
    repos_dir = (workdir / args.repos_dir).resolve()
    compiledrepos_dir = (workdir / args.compiledrepos_dir).resolve()
    mapping_dir = (workdir / args.mapping_dir).resolve()
    output_csv = (workdir / args.output_csv).resolve()

    if not repos_dir.exists():
        raise FileNotFoundError(f"Repos directory not found: {repos_dir}")
    if not mapping_dir.exists():
        raise FileNotFoundError(f"Mapping directory not found: {mapping_dir}")

    _ensure_compiledrepos_link(repos_dir, compiledrepos_dir)

    rows: list[dict] = []
    for json_path in sorted(mapping_dir.glob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if str(payload.get("status", "")).lower() != "ok":
            continue

        repo_id = str(payload.get("repo_id") or "").strip()
        focal_path = payload.get("focal_file_path")
        test_path = payload.get("test_file_path")
        if not repo_id or not focal_path or not test_path:
            continue

        focal_rel = _relative_repo_path(focal_path, repo_id, repos_dir)
        test_rel = _relative_repo_path(test_path, repo_id, repos_dir)
        if not focal_rel or not test_rel:
            continue

        focal_class = str(payload.get("focal_class_name") or Path(focal_path).stem).strip()
        test_class = Path(test_rel).stem
        module = _infer_module(focal_rel)

        rows.append(
            {
                "Project": repo_id,
                "Focal_Class": focal_class,
                "Test_Class": test_class,
                "Focal_Path": focal_rel,
                "Test_Path": test_rel,
                "Module": module,
            }
        )

    if not args.overwrite_csv:
        rows = _load_existing_rows(output_csv) + rows

    unique_rows: list[dict] = []
    seen: set[tuple] = set()
    for row in rows:
        key = (
            row.get("Project"),
            row.get("Focal_Class"),
            row.get("Test_Class"),
            row.get("Focal_Path"),
            row.get("Test_Path"),
            row.get("Module"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Project", "Focal_Class", "Test_Class", "Focal_Path", "Test_Path", "Module"],
        )
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"[DONE] Wrote {len(unique_rows)} rows to {output_csv}")


if __name__ == "__main__":
    main()
