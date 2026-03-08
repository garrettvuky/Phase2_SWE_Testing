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
    parser = argparse.ArgumentParser(description="Checkout cloned repos to dataset base commits.")
    parser.add_argument(
        "--manifest",
        default="phase2/data/processed/manifest.jsonl",
        help="Path to manifest.jsonl",
    )
    parser.add_argument(
        "--repos-dir",
        default="repos",
        help="Directory containing cloned repositories.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    repos_dir = Path(args.repos_dir).resolve()

    print("=== Starting Git Checkout ===")
    print(f"Manifest: {manifest_path}")
    print(f"Repos dir: {repos_dir}")

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not repos_dir.exists():
        raise FileNotFoundError(f"Repos directory not found: {repos_dir}")

    with manifest_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            repo_id = _repo_id(record)
            base_commit = str(record.get("base_commit") or "").strip()
            if not repo_id or not base_commit:
                continue

            target_dir = repos_dir / repo_id
            if not target_dir.exists():
                continue

            print(f"[REWIND] {repo_id} -> {base_commit}")
            subprocess.run(
                ["git", "checkout", "--force", "--detach", base_commit],
                cwd=target_dir,
                capture_output=True,
                text=True,
            )

    print("=== Checkout Complete ===")


if __name__ == "__main__":
    main()
