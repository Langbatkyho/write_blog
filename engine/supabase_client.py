import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from engine.app_logger import log as app_log
from engine.utils import ROOT

# ----------------- Supabase REST Client -----------------
# We use urllib to avoid heavy dependencies (like httpx/pydantic) on Render.

def _get_supabase_config() -> tuple[str, str] | None:
    """Return (URL, KEY) if configured, else None."""
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None
    return url, key

def check_supabase_status() -> dict[str, Any]:
    """Kiểm tra cấu hình Supabase (Dùng cho UI debug)."""
    is_render = bool(os.environ.get("RENDER"))
    config = _get_supabase_config()
    
    status = {
        "platform": "Render" if is_render else "Local",
        "supabase_url": "✅ Đã cấu hình" if config else "❌ Chưa cấu hình",
        "supabase_key": "✅ Đã cấu hình" if config else "❌ Chưa cấu hình",
        "ready": bool(config),
    }
    return status

def upsert_style_file(mode: str, slug: str, filename: str, content: str) -> bool:
    """Lưu 1 file YAML của style lên Supabase."""
    config = _get_supabase_config()
    if not config:
        return False
    
    url, key = config
    endpoint = f"{url}/rest/v1/style_files"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    data = {
        "mode": mode,
        "slug": slug,
        "filename": filename,
        "content": content
    }
    
    try:
        req = urllib.request.Request(endpoint, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 201):
                app_log("SUPABASE", f"✅ Upsert OK: {mode}/{slug}/{filename}")
                return True
            else:
                app_log("SUPABASE", f"❌ Upsert fail {response.status}", level="ERROR")
                return False
    except Exception as e:
        app_log("SUPABASE", f"Lỗi mạng: {e}", level="ERROR")
        return False

def delete_style_files(mode: str, slug: str) -> bool:
    """Xóa tất cả files của một style."""
    config = _get_supabase_config()
    if not config:
        return False
    
    url, key = config
    endpoint = f"{url}/rest/v1/style_files?mode=eq.{mode}&slug=eq.{slug}"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    
    try:
        req = urllib.request.Request(endpoint, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 204):
                app_log("SUPABASE", f"✅ Delete OK: {mode}/{slug}")
                return True
            else:
                app_log("SUPABASE", f"❌ Delete fail {response.status}", level="ERROR")
                return False
    except Exception as e:
        app_log("SUPABASE", f"Lỗi mạng: {e}", level="ERROR")
        return False

def restore_all_styles() -> bool:
    """Kéo tất cả style từ Supabase và ghi đè xuống filesystem. Dùng khi app mới khởi động."""
    config = _get_supabase_config()
    if not config:
        app_log("SUPABASE", "Chưa cấu hình SUPABASE, bỏ qua restore.")
        return False
        
    url, key = config
    endpoint = f"{url}/rest/v1/style_files?select=mode,slug,filename,content"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    
    try:
        req = urllib.request.Request(endpoint, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if not data:
                    app_log("SUPABASE", "Database trống, không có style nào để restore.")
                    return True
                
                count = 0
                for row in data:
                    mode = row.get("mode")
                    slug = row.get("slug")
                    filename = row.get("filename")
                    content = row.get("content")
                    if not all([mode, slug, filename, content]):
                        continue
                        
                    target_dir = ROOT / "skills" / mode / slug
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_file = target_dir / filename
                    
                    target_file.write_text(content, encoding="utf-8")
                    count += 1
                    
                app_log("SUPABASE", f"✅ Restore {count} files xuống filesystem thành công.")
                return True
            else:
                app_log("SUPABASE", f"❌ Restore fail {response.status}", level="ERROR")
                return False
    except Exception as e:
        app_log("SUPABASE", f"Lỗi mạng: {e}", level="ERROR")
        return False
