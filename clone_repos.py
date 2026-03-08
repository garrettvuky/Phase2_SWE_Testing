import argparse
import json
import subprocess
from pathlib import Path


def _repo_id(record: dict) -> str | None:
    value = record.get("repository_repo_id") or (record.get("repository") or {}).get("repo_id")
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clone all repositories listed in manifest.jsonl.")
    parser.add_argument(
        "--manifest",
        default="phase2/data/processed/manifest.jsonl",
        help="Path to manifest.jsonl",
    )
    parser.add_argument(
        "--repos-dir",
        default="repos",
        help="Destination directory for cloned repositories.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    repos_dir = Path(args.repos_dir).resolve()
    repos_dir.mkdir(parents=True, exist_ok=True)

    print("=== Starting Mass Repository Clone ===")
    print(f"Manifest: {manifest_path}")
    print(f"Repos dir: {repos_dir}")

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            repo_url = str(record.get("repository_url") or "").strip()
            repo_id = _repo_id(record)
            if not repo_url or not repo_id:
                continue

            target_dir = repos_dir / repo_id
            if target_dir.exists():
                print(f"[SKIP] {repo_id} already exists.")
                continue

            print(f"[CLONE] {repo_id} <- {repo_url}")
            subprocess.run(["git", "clone", repo_url, str(target_dir)], check=False)

    print("=== Cloning Complete ===")


if __name__ == "__main__":
    main()
