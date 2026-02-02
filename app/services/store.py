import json
import os
from typing import List, Dict
from datetime import datetime
from app.core.logging import get_logger

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
STORE_FILE = os.path.join(DATA_DIR, "uploaded_files.json")

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def _load_store() -> List[Dict]:
    if not os.path.exists(STORE_FILE):
        return []
    try:
        with open(STORE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load store: {e}")
        return []

def _save_store(data: List[Dict]):
    try:
        with open(STORE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save store: {e}")

def add_file_metadata(metadata: Dict):
    _ensure_data_dir()
    data = _load_store()
    # Add timestamp if not present
    if "upload_timestamp" not in metadata:
        metadata["upload_timestamp"] = datetime.utcnow().isoformat()
    
    data.append(metadata)
    _save_store(data)

def list_files() -> List[Dict]:
    _ensure_data_dir()
    return _load_store()
