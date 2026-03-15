import os
import json
import hashlib
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

@contextmanager
def file_cache(cache_dir: str, key: str) -> Generator[Any, None, None]:
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, key)
    try:
        if os.path.exists(cache_path):
            # Touch the file to update its modification time
            now = time.time()
            os.utime(cache_path, (now, now))
            with open(cache_path, 'r', encoding='utf-8') as f:
                yield json.load(f)
        else:
            yield None
    finally:
        pass

def make_cache_key(url: str, postal_code: str | None = None) -> str:
    """
    return hashlib.sha256(url.encode('utf-8')).hexdigest() + '.json'
    """
    key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    if postal_code:
        key = f"{postal_code}_{key}"
    return key + '.json'

def clear_old_caches(cache_dir: str, days_unused: int = 30) -> list[str]:
    """
    Remove cache files in cache_dir not accessed in the last 'days_unused' days.
    """
    now = time.time()
    cutoff = now - days_unused * 86400
    removed = []
    for fname in os.listdir(cache_dir):
        fpath = os.path.join(cache_dir, fname)
        if os.path.isfile(fpath):
            last_used = os.path.getmtime(fpath)
            if last_used < cutoff:
                os.remove(fpath)
                removed.append(fname)
    return removed
