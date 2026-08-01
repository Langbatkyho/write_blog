import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from engine.app_logger import log as app_log

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: PyYAML. Install it with `pip install pyyaml`."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")

def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(read_text(path))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML object in {path}")
    return data

def resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path

def auto_git_sync(target_path: str | list[str], commit_message: str = "Tự động lưu thay đổi") -> bool:
    """
    Tự động Git Add, Commit và Push cho một thư mục hoặc file cụ thể.
    Chạy tất cả git command từ thư mục ROOT của repo.
    """
    if not os.environ.get("RENDER"):
        app_log("GIT", "Local mode, bỏ qua Auto Git Sync.")
        return False
        
    repo_root = str(ROOT)
    
    try:
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "Langbatkyho"
        env["GIT_AUTHOR_EMAIL"] = "langbatkyho@gmail.com"
        env["GIT_COMMITTER_NAME"] = "Langbatkyho"
        env["GIT_COMMITTER_EMAIL"] = "langbatkyho@gmail.com"
        
        def _run(cmd: list[str]) -> subprocess.CompletedProcess:
            result = subprocess.run(
                cmd, cwd=repo_root, env=env,
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                app_log("GIT", f"CMD FAIL: {' '.join(cmd)}", level="ERROR")
                app_log("GIT", f"STDERR: {result.stderr.strip()}", level="ERROR")
                result.check_returncode()
            return result

        github_user = os.environ.get("GITHUB_USERNAME")
        github_token = os.environ.get("GITHUB_TOKEN")
        
        if not github_user or not github_token:
            app_log("GIT", "GITHUB_USERNAME hoặc GITHUB_TOKEN chưa cấu hình!", level="ERROR")
            return False
        
        # Cấu hình authentication
        netrc_path = Path.home() / ".netrc"
        netrc_path.write_text(
            f"machine github.com\nlogin {github_user}\npassword {github_token}\n",
            encoding="utf-8",
        )

        # Xử lý target_path: hỗ trợ list hoặc string đơn (KHÔNG split)
        if isinstance(target_path, list):
            targets = target_path
        else:
            targets = [target_path]
        
        app_log("GIT", f"Repo: {repo_root} | Targets: {targets}")
        
        _run(["git", "add", "--"] + targets)
        
        status = _run(["git", "status", "--porcelain"])
        if not status.stdout.strip():
            app_log("GIT", "Không có thay đổi.")
            return True

        changed = status.stdout.strip().split('\n')
        app_log("GIT", f"Staged: {len(changed)} file(s)")
        _run(["git", "commit", "-m", commit_message])
        _run(["git", "push", "origin", "HEAD:main"])
        
        app_log("GIT", f"✅ Push OK: {commit_message}")
        return True
    except subprocess.CalledProcessError as e:
        app_log("GIT", f"Git thất bại: {e}", level="ERROR")
        return False
    except Exception as e:
        app_log("GIT", f"Lỗi hệ thống: {e}", level="ERROR")
        return False

