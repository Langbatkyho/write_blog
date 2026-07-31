import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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
        print("[Git Sync] Chạy ở Local, bỏ qua Auto Git Sync.")
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
                print(f"[Git Sync] CMD: {' '.join(cmd)}")
                print(f"[Git Sync] STDERR: {result.stderr.strip()}")
                result.check_returncode()
            return result

        github_user = os.environ.get("GITHUB_USERNAME")
        github_token = os.environ.get("GITHUB_TOKEN")
        
        if not github_user or not github_token:
            print("[Git Sync] GITHUB_USERNAME hoặc GITHUB_TOKEN chưa được cấu hình.")
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
        
        print(f"[Git Sync] Repo root: {repo_root}")
        print(f"[Git Sync] Targets: {targets}")
        
        _run(["git", "add", "--"] + targets)
        
        status = _run(["git", "status", "--porcelain"])
        if not status.stdout.strip():
            print("[Git Sync] Không có file nào thay đổi.")
            return True

        print(f"[Git Sync] Staged changes:\n{status.stdout.strip()}")
        _run(["git", "commit", "-m", commit_message])
        _run(["git", "push", "origin", "HEAD:main"])
        
        print(f"[Git Sync] ✅ Đã push thành công: {commit_message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Git Sync Lỗi] Quá trình git thất bại: {e}")
        return False
    except Exception as e:
        print(f"[Git Sync Lỗi] Lỗi hệ thống: {e}")
        return False

