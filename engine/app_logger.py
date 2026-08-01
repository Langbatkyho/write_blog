"""
In-app Logger — Thu thập log vào bộ nhớ để hiển thị trên giao diện Streamlit.
Dùng cho Render free tier (không có disk log / server log chi tiết).
"""
from __future__ import annotations

import datetime as dt
import threading
from collections import deque
from typing import Any


_MAX_ENTRIES = 200
_lock = threading.Lock()
_log_buffer: deque[dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)


def log(tag: str, message: str, level: str = "INFO") -> None:
    """Ghi một dòng log vào buffer."""
    entry = {
        "time": dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"),
        "tag": tag,
        "msg": message,
        "level": level,
    }
    with _lock:
        _log_buffer.append(entry)
    # Vẫn giữ print để debug local
    print(f"[{tag}] {message}")


def get_logs(limit: int = 50) -> list[dict[str, Any]]:
    """Lấy log gần nhất (mới nhất trước)."""
    with _lock:
        entries = list(_log_buffer)
    return list(reversed(entries))[:limit]


def clear_logs() -> None:
    """Xóa toàn bộ log buffer."""
    with _lock:
        _log_buffer.clear()
