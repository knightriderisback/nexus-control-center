"""
NEXUS Storage Engine.
Thread-safe, atomic JSON read/write operations using temporary file replacement,
cross-process flock synchronization, in-memory re-entrant locks, and corruption quarantine.
Prevents file corruption, race conditions, and partial writes during process interruptions.
"""

import json
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional, Dict

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

# Per-filepath thread synchronization & re-entrancy
_LOCK_REGISTRY: Dict[str, threading.RLock] = {}
_REGISTRY_LOCK = threading.Lock()
_THREAD_LOCAL = threading.local()

def _get_thread_lock(filepath: str) -> threading.RLock:
    norm_path = os.path.normpath(os.path.abspath(filepath))
    with _REGISTRY_LOCK:
        if norm_path not in _LOCK_REGISTRY:
            _LOCK_REGISTRY[norm_path] = threading.RLock()
        return _LOCK_REGISTRY[norm_path]

@contextmanager
def file_lock_context(filepath: str):
    """Acquires thread-level RLock and file-level flock with full re-entrancy tracking."""
    norm_path = os.path.normpath(os.path.abspath(filepath))
    t_lock = _get_thread_lock(norm_path)

    if not hasattr(_THREAD_LOCAL, "held_flocks"):
        _THREAD_LOCAL.held_flocks = {}
    if not hasattr(_THREAD_LOCAL, "flock_fds"):
        _THREAD_LOCAL.flock_fds = {}

    with t_lock:
        lock_file_path = f"{norm_path}.lock"
        parent_dir = os.path.dirname(norm_path)
        os.makedirs(parent_dir, exist_ok=True)

        depth = _THREAD_LOCAL.held_flocks.get(norm_path, 0)
        if depth == 0 and HAS_FCNTL:
            try:
                fd = os.open(lock_file_path, os.O_CREAT | os.O_RDWR, 0o666)
                fcntl.flock(fd, fcntl.LOCK_EX)
                _THREAD_LOCAL.held_flocks[norm_path] = 1
                _THREAD_LOCAL.flock_fds[norm_path] = fd
            except Exception:
                _THREAD_LOCAL.held_flocks[norm_path] = 1
                _THREAD_LOCAL.flock_fds[norm_path] = None
        else:
            _THREAD_LOCAL.held_flocks[norm_path] = depth + 1

        try:
            yield
        finally:
            cur_depth = _THREAD_LOCAL.held_flocks.get(norm_path, 1) - 1
            if cur_depth <= 0:
                _THREAD_LOCAL.held_flocks.pop(norm_path, None)
                fd = _THREAD_LOCAL.flock_fds.pop(norm_path, None)
                if fd is not None and HAS_FCNTL:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                        os.close(fd)
                    except Exception:
                        pass
            else:
                _THREAD_LOCAL.held_flocks[norm_path] = cur_depth

def load_json_safe(filepath: str, default: Optional[Any] = None) -> Any:
    """
    Reads JSON safely under lock.
    If file is corrupted, quarantines the damaged file to <filepath>.corrupt.<ts>
    and returns default safely without raising uncaught runtime exceptions.
    """
    if not os.path.exists(filepath):
        return default if default is not None else {}
    
    t_lock = _get_thread_lock(filepath)
    with t_lock:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Quarantine corrupted file to preserve forensic trace and avoid silent loss
            try:
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                quarantine_path = f"{filepath}.corrupt.{ts}"
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    shutil.copy2(filepath, quarantine_path)
            except Exception:
                pass
            return default if default is not None else {}

def atomic_save_json(filepath: str, data: Any, indent: int = 2) -> None:
    """Writes JSON atomically by writing to a temporary file in the same directory then renaming under lock."""
    parent_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(parent_dir, exist_ok=True)

    with file_lock_context(filepath):
        with tempfile.NamedTemporaryFile("w", dir=parent_dir, delete=False, encoding="utf-8") as tf:
            temp_path = tf.name
            json.dump(data, tf, indent=indent)
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(temp_path, filepath)

@contextmanager
def atomic_json_updater(filepath: str, default: Optional[Any] = None):
    """
    Context manager providing transactional read-modify-write semantics for persistent JSON files.
    Holds lock throughout the mutation window to prevent race conditions.
    """
    with file_lock_context(filepath):
        data = load_json_safe(filepath, default=default)
        yield data
        atomic_save_json(filepath, data)
