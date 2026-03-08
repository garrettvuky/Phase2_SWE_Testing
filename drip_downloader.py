import os
import time
import random
import requests
from pathlib import Path

# --- Configuration ---
REPO_ID = "classes2test"
BASE_API_URL = f"https://anonymous.4open.science/api/repo/{REPO_ID}"
OUTPUT_DIR = Path("AgoneTest")
DELAY_SECONDS = 4.0  # 350 requests / 15 mins = 1 request every ~2.57 seconds

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_directory(path=""):
    """Fetches the contents of a directory."""
    urls = [
        f"{BASE_API_URL}/files/{path}" if path else f"{BASE_API_URL}/files",
        f"{BASE_API_URL}/files?path={path}" if path else f"{BASE_API_URL}/files",
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            time.sleep(DELAY_SECONDS)  # Respect rate limit
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # Fallback in case the root API returns a dict structure
                    # where keys are names and values are metadata
                    formatted_data = []
                    for k, v in data.items():
                        v["name"] = k
                        formatted_data.append(v)
                    return formatted_data
        except Exception:
            continue
            
    return None

def download_file(filepath):
    """Downloads a single file and preserves its directory path."""
    local_path = OUTPUT_DIR / filepath
    
    # Ensure the parent subdirectories exist locally before writing
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    if local_path.exists():
        print(f"[SKIP] {filepath} already exists.")
        return True
        
    url = f"{BASE_API_URL}/file/{filepath}"
    try:
        response = requests.get(url, timeout=10)
        time.sleep(DELAY_SECONDS)
        
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(response.content)
            print(f"[SUCCESS] Downloaded: {filepath}")
            return True
        elif response.status_code == 429:
            print(f"[RATE LIMITED] Server asked us to slow down. Waiting 10 seconds...")
            time.sleep(10)
            # Retry once after cooling down
            return download_file(filepath)
        else:
            print(f"[ERROR] Status {response.status_code} for {filepath}")
            return False
    except Exception as e:
        print(f"[NETWORK ERROR] {filepath}: {e}")
        time.sleep(DELAY_SECONDS)
        return False

def traverse_and_download(current_path=""):
    """Recursively walks through the repository tree to download all files."""
    contents = fetch_directory(current_path)
    
    if not contents:
        return

    for item in contents:
        # Ignore hidden files/folders if needed, or parse the name
        name = item.get("name", "")
        if not name:
            continue
            
        item_path = f"{current_path}/{name}" if current_path else name
        
        # If it has a "size" attribute, treat it as a file. Otherwise, a directory.
        if "size" in item or item.get("type") == "file":
            download_file(item_path)
        else:
            print(f"\n--- Entering directory: {item_path} ---")
            traverse_and_download(item_path)

def main():
    print("=== Starting AgoneTest Full Repository Downloader ===")
    
    if REPO_ID == "YOUR_AGONETEST_REPO_ID":
        print("WAIT! Please update the REPO_ID variable in the script with the hash from your AgoneTest URL.")
        return
        
    print("Mapping repository structure...")
    traverse_and_download("")

    print("\n=== Download Complete ===")
    print(f"Framework files are successfully saved in: {OUTPUT_DIR.absolute()}")

if __name__ == "__main__":
    main()