"""
NEXUS Storage Engine.
Thread-safe, atomic JSON read/write operations using temporary file replacement.
Prevents file corruption and partial writes during process interruptions.
"""

import json
import os
import tempfile
from typing import Any, Optional

def load_json_safe(filepath: str, default: Optional[Any] = None) -> Any:
    """Reads JSON safely, returning default if file does not exist or is corrupt."""
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def atomic_save_json(filepath: str, data: Any, indent: int = 2) -> None:
    """Writes JSON atomically by writing to a temporary file in the same directory then renaming."""
    parent_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(parent_dir, exist_ok=True)

    # Use NamedTemporaryFile in the same filesystem directory to ensure atomic os.replace
    with tempfile.NamedTemporaryFile("w", dir=parent_dir, delete=False, encoding="utf-8") as tf:
        temp_path = tf.name
        json.dump(data, tf, indent=indent)
        tf.flush()
        os.fsync(tf.fileno())

    os.replace(temp_path, filepath)
