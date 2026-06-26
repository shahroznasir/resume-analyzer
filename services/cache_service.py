import os
import hashlib

CACHE_DIR = "cache"

def calculate_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def get_cached_analysis(file_hash: str) -> str | None:
    cache_path = os.path.join(CACHE_DIR, f"{file_hash}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading cache file {cache_path}: {e}")
            return None
    return None

def save_to_cache(file_hash: str, analysis_json_str: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{file_hash}.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(analysis_json_str)
    except Exception as e:
        print(f"Error writing to cache file {cache_path}: {e}")
