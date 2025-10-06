import json
import os
import threading
from typing import Any, Dict

DATA_PATH = os.environ.get("DATA_PATH", "/data")
os.makedirs(DATA_PATH, exist_ok=True)
DB_FILE = os.path.join(DATA_PATH, "kv.json")
_LOCK = threading.Lock()


def read_db() -> Dict[str, Any]:
    with _LOCK:
        if not os.path.exists(DB_FILE):
            return {}
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}

        if not isinstance(data, dict):
            return {}

        return data


def write_db(data: Dict[str, Any]) -> None:
    tmp = DB_FILE + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DB_FILE)
