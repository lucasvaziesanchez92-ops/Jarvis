import os
import json
import time
from loguru import logger

VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", os.path.join("backend", "data", "brain"))
MANIFEST_FILE = os.path.join(VAULT_PATH, ".manifest.json")

def load_manifest() -> dict:
    if not os.path.exists(MANIFEST_FILE):
        return {"ingested": {}}
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading manifest: {e}")
        return {"ingested": {}}

def save_manifest(manifest: dict):
    os.makedirs(VAULT_PATH, exist_ok=True)
    try:
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving manifest: {e}")

def mark_ingested(source_id: str, pages_generated: list[str]):
    manifest = load_manifest()
    manifest["ingested"][source_id] = {
        "timestamp": time.time(),
        "pages": pages_generated
    }
    save_manifest(manifest)

def is_ingested(source_id: str) -> bool:
    manifest = load_manifest()
    return source_id in manifest.get("ingested", {})
