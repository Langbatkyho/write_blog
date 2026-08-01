diff --git a/docs/supabase_setup.sql b/docs/supabase_setup.sql
new file mode 100644
index 0000000..6e03c62
--- /dev/null
+++ b/docs/supabase_setup.sql
@@ -0,0 +1,36 @@
+-- Supabase Setup Script cho Write Blog
+-- Copy v├á d├ín to├án bß╗Ö ─æoß║ín m├ú n├áy v├áo mß╗Ñc "SQL Editor" tr├¬n Supabase Dashboard v├á bß║Ñm "Run"
+
+-- 1. Tß║ío bß║úng l╞░u trß╗» style files
+CREATE TABLE IF NOT EXISTS style_files (
+  id BIGSERIAL PRIMARY KEY,
+  mode TEXT NOT NULL,          -- 'deep' hoß║╖c 'moment'
+  slug TEXT NOT NULL,          -- 'reflective', 'va-natural', v.v.
+  filename TEXT NOT NULL,      -- 'sensory_capture.yaml', 'style_meta.yaml', v.v.
+  content TEXT NOT NULL,       -- Nß╗Öi dung YAML
+  updated_at TIMESTAMPTZ DEFAULT NOW(),
+  UNIQUE(mode, slug, filename)
+);
+
+-- 2. Cho ph├⌐p truy cß║¡p ß║⌐n danh (hoß║╖c d├╣ng service_key th├¼ kh├┤ng bß║»t buß╗Öc, nh╞░ng n├¬n bß║¡t RLS nß║┐u public)
+-- Mß║╖c ─æß╗ïnh kh├┤ng c├│ Row Level Security (RLS) ─æß╗â ─æ╞ín giß║ún cho ß╗⌐ng dß╗Ñng nß╗Öi bß╗Ö.
+-- Nß║┐u bß║ín muß╗æn bß║úo mß║¡t h╞ín, c├│ thß╗â bß║¡t RLS v├á cß║Ñu h├¼nh Policy.
+-- ALTER TABLE style_files ENABLE ROW LEVEL SECURITY;
+
+-- 3. Tß║ío function cß║¡p nhß║¡t updated_at tß╗▒ ─æß╗Öng khi sß╗¡a
+CREATE OR REPLACE FUNCTION set_updated_at()
+RETURNS TRIGGER AS $$
+BEGIN
+  NEW.updated_at = NOW();
+  RETURN NEW;
+END;
+$$ LANGUAGE plpgsql;
+
+-- 4. Gß║»n trigger v├áo bß║úng
+DROP TRIGGER IF EXISTS trigger_style_files_updated_at ON style_files;
+CREATE TRIGGER trigger_style_files_updated_at
+BEFORE UPDATE ON style_files
+FOR EACH ROW
+EXECUTE FUNCTION set_updated_at();
+
+-- Ho├án tß║Ñt!
diff --git a/engine/style_manager.py b/engine/style_manager.py
index 04c59db..6adab74 100644
--- a/engine/style_manager.py
+++ b/engine/style_manager.py
@@ -4,7 +4,8 @@ from pathlib import Path
 from typing import Any, Tuple, List, Dict, Optional
 import yaml
 
-from engine.utils import resolve_path, write_text, load_yaml, read_text, auto_git_sync
+from engine.utils import resolve_path, write_text, load_yaml, read_text
+from engine.supabase_client import upsert_style_file, delete_style_files
 from engine.workflow_contracts import (
     WorkflowDefinition,
     validate_step_skill_contract,
@@ -18,6 +19,12 @@ from engine.style_repository import (
 )
 from engine.style_contracts import is_valid_style_slug, validate_style_metadata
 
+def _sync_style_to_supabase(mode: str, slug: str, style_dir: Path) -> None:
+    """Helper to sync all yaml files in a style directory to Supabase."""
+    for f in style_dir.glob("*.yaml"):
+        content = read_text(f)
+        upsert_style_file(mode, slug, f.name, content)
+
 DEEP_GROUP_A_FILES = {
     "story_architect.yaml",
     "reflection_engine.yaml",
@@ -332,8 +339,17 @@ def save_style_file(mode: str, slug: str, filename: str, content: str) -> Tuple[
             )
         validate_style_directory(mode, slug, staging_dir)
         commit_staged_directory(staging_dir, style_dir)
-        auto_git_sync(str(style_dir), f"feat(style): Cß║¡p nhß║¡t file {filename} cß╗ºa style {slug}")
-        return True, "", warn
+        
+        # Sync file ─æ├ú sß╗¡a l├¬n Supabase
+        if not upsert_style_file(mode, slug, filename, content):
+            warn += " ΓÜá∩╕Å L╞░u local OK nh╞░ng sync Supabase thß║Ñt bß║íi."
+            
+        committed_meta = style_dir / "style_meta.yaml"
+        if committed_meta.exists():
+            if not upsert_style_file(mode, slug, "style_meta.yaml", read_text(committed_meta)):
+                warn += " ΓÜá∩╕Å Sync style_meta.yaml l├¬n Supabase thß║Ñt bß║íi."
+            
+        return True, "", warn.strip()
     except Exception as e:
         if staging_dir and staging_dir.exists():
             shutil.rmtree(staging_dir, ignore_errors=True)
@@ -383,7 +399,7 @@ def create_style(
         )
         validate_style_directory(mode, slug, staging_dir)
         commit_staged_directory(staging_dir, target_dir)
-        auto_git_sync(str(target_dir), f"feat(style): Tß║ío mß╗¢i style {slug}")
+        _sync_style_to_supabase(mode, slug, target_dir)
         return True, ""
     except Exception as e:
         if staging_dir and staging_dir.exists():
@@ -451,10 +467,12 @@ def rename_style(mode: str, old_slug: str, new_name: str, new_slug: str) -> Tupl
         )
         if old_slug == new_slug:
             commit_staged_directory(staging_dir, style_dir)
-            auto_git_sync(str(style_dir), f"feat(style): Cß║¡p nhß║¡t t├¬n cß╗ºa style {new_slug}")
+            _sync_style_to_supabase(mode, new_slug, style_dir)
         else:
             commit_staged_rename(staging_dir, style_dir, target_dir)
-            auto_git_sync(str(style_dir.parent), f"feat(style): ─Éß╗òi t├¬n style {old_slug} th├ánh {new_slug}")
+            # Sync style mß╗¢i v├á x├│a style c┼⌐
+            _sync_style_to_supabase(mode, new_slug, target_dir)
+            delete_style_files(mode, old_slug)
         return True, ""
     except Exception as e:
         if staging_dir and staging_dir.exists():
@@ -487,10 +505,7 @@ def delete_style(mode: str, slug: str) -> Tuple[bool, str]:
     try:
         trash_root = resolve_path(f"profile_history/style_trash/{mode}")
         trash_path = move_to_trash(style_dir, trash_root)
-        auto_git_sync(
-            [str(style_dir.parent), str(trash_path)], 
-            f"feat(style): Xo├í style {slug} v├á chuyß╗ân v├áo th├╣ng r├íc"
-        )
+        delete_style_files(mode, slug)
         return True, f"Style ─æ├ú chuyß╗ân v├áo th├╣ng r├íc: {trash_path}"
     except Exception as e:
         return False, f"Lß╗ùi khi x├│a folder style: {str(e)}"
diff --git a/engine/supabase_client.py b/engine/supabase_client.py
new file mode 100644
index 0000000..ee2ceeb
--- /dev/null
+++ b/engine/supabase_client.py
@@ -0,0 +1,145 @@
+import json
+import os
+import urllib.request
+import urllib.error
+from pathlib import Path
+from typing import Any
+
+from engine.app_logger import log as app_log
+from engine.utils import ROOT
+
+# ----------------- Supabase REST Client -----------------
+# We use urllib to avoid heavy dependencies (like httpx/pydantic) on Render.
+
+def _get_supabase_config() -> tuple[str, str] | None:
+    """Return (URL, KEY) if configured, else None."""
+    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
+    key = os.environ.get("SUPABASE_KEY", "").strip()
+    if not url or not key:
+        return None
+    return url, key
+
+def check_supabase_status() -> dict[str, Any]:
+    """Kiß╗âm tra cß║Ñu h├¼nh Supabase (D├╣ng cho UI debug)."""
+    is_render = bool(os.environ.get("RENDER"))
+    config = _get_supabase_config()
+    
+    status = {
+        "platform": "Render" if is_render else "Local",
+        "supabase_url": "Γ£à ─É├ú cß║Ñu h├¼nh" if config else "Γ¥î Ch╞░a cß║Ñu h├¼nh",
+        "supabase_key": "Γ£à ─É├ú cß║Ñu h├¼nh" if config else "Γ¥î Ch╞░a cß║Ñu h├¼nh",
+        "ready": bool(config),
+    }
+    return status
+
+def upsert_style_file(mode: str, slug: str, filename: str, content: str) -> bool:
+    """L╞░u 1 file YAML cß╗ºa style l├¬n Supabase."""
+    config = _get_supabase_config()
+    if not config:
+        return False
+    
+    url, key = config
+    endpoint = f"{url}/rest/v1/style_files"
+    
+    headers = {
+        "apikey": key,
+        "Authorization": f"Bearer {key}",
+        "Content-Type": "application/json",
+        "Prefer": "resolution=merge-duplicates"
+    }
+    
+    data = {
+        "mode": mode,
+        "slug": slug,
+        "filename": filename,
+        "content": content
+    }
+    
+    try:
+        req = urllib.request.Request(endpoint, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
+        with urllib.request.urlopen(req, timeout=10) as response:
+            if response.status in (200, 201):
+                app_log("SUPABASE", f"Γ£à Upsert OK: {mode}/{slug}/{filename}")
+                return True
+            else:
+                app_log("SUPABASE", f"Γ¥î Upsert fail {response.status}", level="ERROR")
+                return False
+    except Exception as e:
+        app_log("SUPABASE", f"Lß╗ùi mß║íng: {e}", level="ERROR")
+        return False
+
+def delete_style_files(mode: str, slug: str) -> bool:
+    """X├│a tß║Ñt cß║ú files cß╗ºa mß╗Öt style."""
+    config = _get_supabase_config()
+    if not config:
+        return False
+    
+    url, key = config
+    endpoint = f"{url}/rest/v1/style_files?mode=eq.{mode}&slug=eq.{slug}"
+    
+    headers = {
+        "apikey": key,
+        "Authorization": f"Bearer {key}",
+    }
+    
+    try:
+        req = urllib.request.Request(endpoint, headers=headers, method="DELETE")
+        with urllib.request.urlopen(req, timeout=10) as response:
+            if response.status in (200, 204):
+                app_log("SUPABASE", f"Γ£à Delete OK: {mode}/{slug}")
+                return True
+            else:
+                app_log("SUPABASE", f"Γ¥î Delete fail {response.status}", level="ERROR")
+                return False
+    except Exception as e:
+        app_log("SUPABASE", f"Lß╗ùi mß║íng: {e}", level="ERROR")
+        return False
+
+def restore_all_styles() -> bool:
+    """K├⌐o tß║Ñt cß║ú style tß╗½ Supabase v├á ghi ─æ├¿ xuß╗æng filesystem. D├╣ng khi app mß╗¢i khß╗ƒi ─æß╗Öng."""
+    config = _get_supabase_config()
+    if not config:
+        app_log("SUPABASE", "Ch╞░a cß║Ñu h├¼nh SUPABASE, bß╗Å qua restore.")
+        return False
+        
+    url, key = config
+    endpoint = f"{url}/rest/v1/style_files?select=mode,slug,filename,content"
+    
+    headers = {
+        "apikey": key,
+        "Authorization": f"Bearer {key}",
+    }
+    
+    try:
+        req = urllib.request.Request(endpoint, headers=headers, method="GET")
+        with urllib.request.urlopen(req, timeout=15) as response:
+            if response.status == 200:
+                data = json.loads(response.read().decode("utf-8"))
+                if not data:
+                    app_log("SUPABASE", "Database trß╗æng, kh├┤ng c├│ style n├áo ─æß╗â restore.")
+                    return True
+                
+                count = 0
+                for row in data:
+                    mode = row.get("mode")
+                    slug = row.get("slug")
+                    filename = row.get("filename")
+                    content = row.get("content")
+                    if not all([mode, slug, filename, content]):
+                        continue
+                        
+                    target_dir = ROOT / "skills" / mode / slug
+                    target_dir.mkdir(parents=True, exist_ok=True)
+                    target_file = target_dir / filename
+                    
+                    target_file.write_text(content, encoding="utf-8")
+                    count += 1
+                    
+                app_log("SUPABASE", f"Γ£à Restore {count} files xuß╗æng filesystem th├ánh c├┤ng.")
+                return True
+            else:
+                app_log("SUPABASE", f"Γ¥î Restore fail {response.status}", level="ERROR")
+                return False
+    except Exception as e:
+        app_log("SUPABASE", f"Lß╗ùi mß║íng: {e}", level="ERROR")
+        return False
diff --git a/engine/utils.py b/engine/utils.py
index b6a9933..a2d6dee 100644
--- a/engine/utils.py
+++ b/engine/utils.py
@@ -1,5 +1,4 @@
 import os
-import subprocess
 import sys
 from pathlib import Path
 from typing import Any
@@ -37,129 +36,4 @@ def resolve_path(raw_path: str | Path) -> Path:
     path = Path(raw_path)
     return path if path.is_absolute() else ROOT / path
 
-def check_git_sync_status() -> dict[str, Any]:
-    """Kiß╗âm tra trß║íng th├íi cß║Ñu h├¼nh Git Sync (d├╣ng cho UI debug)."""
-    is_render = bool(os.environ.get("RENDER"))
-    has_user = bool(os.environ.get("GITHUB_USERNAME"))
-    has_token = bool(os.environ.get("GITHUB_TOKEN"))
-    git_exists = (Path(str(ROOT)) / ".git").exists()
-    
-    status = {
-        "platform": "Render" if is_render else "Local",
-        "enabled": is_render,
-        "git_repo": "Γ£à C├│ .git" if git_exists else "ΓÜá∩╕Å Ch╞░a c├│ .git (sß║╜ tß╗▒ tß║ío khi sync)",
-        "github_username": "Γ£à ─É├ú cß║Ñu h├¼nh" if has_user else "Γ¥î Ch╞░a cß║Ñu h├¼nh",
-        "github_token": "Γ£à ─É├ú cß║Ñu h├¼nh" if has_token else "Γ¥î Ch╞░a cß║Ñu h├¼nh",
-        "ready": is_render and has_user and has_token,
-    }
-    
-    if is_render and git_exists:
-        try:
-            result = subprocess.run(
-                ["git", "remote", "get-url", "origin"],
-                cwd=str(ROOT), capture_output=True, text=True,
-            )
-            url = result.stdout.strip()
-            # Che giß║Ñu token trong URL
-            if "@github.com" in url:
-                url = url.split("@")[0][:20] + "***@github.com/..."
-            status["remote_url"] = url if url else "Ch╞░a c├│ remote"
-        except Exception:
-            status["remote_url"] = "Ch╞░a c├│ remote"
-    
-    return status
 
-
-def auto_git_sync(target_path: str | list[str], commit_message: str = "Tß╗▒ ─æß╗Öng l╞░u thay ─æß╗òi") -> bool:
-    """
-    Tß╗▒ ─æß╗Öng Git Add, Commit v├á Push dß╗» liß╗çu workflow sang branch 'data'.
-    KH├öNG push v├áo 'main' ─æß╗â tr├ính trigger Render auto-deploy.
-    """
-    if not os.environ.get("RENDER"):
-        app_log("GIT", "Local mode, bß╗Å qua Auto Git Sync.")
-        return False
-        
-    repo_root = str(ROOT)
-    DATA_BRANCH = "data"
-    
-    try:
-        env = os.environ.copy()
-        env["GIT_AUTHOR_NAME"] = "Langbatkyho"
-        env["GIT_AUTHOR_EMAIL"] = "langbatkyho@gmail.com"
-        env["GIT_COMMITTER_NAME"] = "Langbatkyho"
-        env["GIT_COMMITTER_EMAIL"] = "langbatkyho@gmail.com"
-        
-        github_user = os.environ.get("GITHUB_USERNAME")
-        github_token = os.environ.get("GITHUB_TOKEN")
-        
-        if not github_user or not github_token:
-            app_log("GIT", "GITHUB_USERNAME hoß║╖c GITHUB_TOKEN ch╞░a cß║Ñu h├¼nh!", level="ERROR")
-            return False
-        
-        def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
-            result = subprocess.run(
-                cmd, cwd=repo_root, env=env,
-                capture_output=True, text=True,
-            )
-            if check and result.returncode != 0:
-                safe_cmd = ' '.join(cmd).replace(github_token, "***") if github_token else ' '.join(cmd)
-                safe_err = result.stderr.strip().replace(github_token, "***") if github_token else result.stderr.strip()
-                app_log("GIT", f"CMD FAIL: {safe_cmd}", level="ERROR")
-                app_log("GIT", f"STDERR: {safe_err}", level="ERROR")
-                result.check_returncode()
-            return result
-        
-        # ─Éß║úm bß║úo c├│ git repo (Render extract archive, kh├┤ng git clone)
-        git_dir = Path(repo_root) / ".git"
-        if not git_dir.exists():
-            _run(["git", "init"])
-            _run(["git", "checkout", "-b", DATA_BRANCH])
-            _run(["git", "add", "."])
-            _run(["git", "commit", "-m", "Initial commit from Render"])
-            app_log("GIT", f"─É├ú khß╗ƒi tß║ío git repo tr├¬n branch '{DATA_BRANCH}'.")
-        else:
-            # ─Éß║úm bß║úo ─æang ß╗ƒ branch data
-            current = _run(["git", "branch", "--show-current"], check=False)
-            if current.stdout.strip() != DATA_BRANCH:
-                # Tß║ío hoß║╖c chuyß╗ân sang branch data
-                _run(["git", "checkout", "-B", DATA_BRANCH], check=False)
-        
-        # Cß║Ñu h├¼nh remote URL vß╗¢i token
-        auth_url = f"https://{github_user}:{github_token}@github.com/{github_user}/write_blog.git"
-        check_remote = _run(["git", "remote", "get-url", "origin"], check=False)
-        if check_remote.returncode != 0:
-            _run(["git", "remote", "add", "origin", auth_url])
-        else:
-            _run(["git", "remote", "set-url", "origin", auth_url])
-        app_log("GIT", f"Remote OK cho user: {github_user}")
-
-        # Xß╗¡ l├╜ target_path
-        targets = target_path if isinstance(target_path, list) else [target_path]
-        
-        app_log("GIT", f"Branch: {DATA_BRANCH} | Targets: {len(targets)} path(s)")
-        
-        _run(["git", "add", "--"] + targets)
-        
-        status = _run(["git", "status", "--porcelain"])
-        if not status.stdout.strip():
-            app_log("GIT", "Kh├┤ng c├│ thay ─æß╗òi.")
-            return True
-
-        changed = status.stdout.strip().split('\n')
-        app_log("GIT", f"Staged: {len(changed)} file(s)")
-        for c in changed[:5]:
-            app_log("GIT", f"  {c.strip()}")
-        
-        _run(["git", "commit", "-m", commit_message])
-        # Push sang branch 'data' (KH├öNG phß║úi main) vß╗¢i --force
-        # v├¼ local repo mß╗¢i init kh├┤ng c├│ shared history vß╗¢i remote
-        _run(["git", "push", "--force", "origin", f"HEAD:{DATA_BRANCH}"])
-        
-        app_log("GIT", f"Γ£à Push OK ΓåÆ branch '{DATA_BRANCH}': {commit_message}")
-        return True
-    except subprocess.CalledProcessError as e:
-        app_log("GIT", f"Git thß║Ñt bß║íi: {e}", level="ERROR")
-        return False
-    except Exception as e:
-        app_log("GIT", f"Lß╗ùi hß╗ç thß╗æng: {e}", level="ERROR")
-        return False
diff --git a/engine/workflow_execution.py b/engine/workflow_execution.py
index f6c3d7f..2fb8a9b 100644
--- a/engine/workflow_execution.py
+++ b/engine/workflow_execution.py
@@ -10,7 +10,7 @@ from typing import Any, Callable
 from engine.openai_client import call_openai, get_openai_options
 from engine.parser import build_context_package, estimate_tokens, parse_stage_response
 from engine.style_manager import validate_style_contract
-from engine.utils import load_yaml, read_text, resolve_path, auto_git_sync
+from engine.utils import load_yaml, read_text, resolve_path
 from engine.workflow_artifacts import append_run_log, derive_artifact_file_contents
 from engine.workflow_context import build_dry_run_response, build_step_prompt
 from engine.workflow_contracts import (
@@ -390,8 +390,6 @@ def run_workflow(
     )
     if repository and run_dir:
         repository.write_metadata(run_dir, metadata)
-        if final_status == "completed" and should_persist:
-            auto_git_sync(str(run_dir), f"feat(run): Tß╗▒ ─æß╗Öng l╞░u blog workflow {run_dir.name}")
     if terminal_error:
         raise terminal_error
     result = WorkflowRunResult(
diff --git a/ui/app.py b/ui/app.py
index 6c3dcc7..5c09ffe 100644
--- a/ui/app.py
+++ b/ui/app.py
@@ -9,8 +9,9 @@ if str(ROOT) not in sys.path:
     sys.path.insert(0, str(ROOT))
 
 from engine.style_manager import list_styles
-from engine.utils import read_text, check_git_sync_status
+from engine.utils import read_text
 from engine.app_logger import get_logs, clear_logs
+from engine.supabase_client import check_supabase_status, restore_all_styles
 from ui.state import initialize_session_state, switch_mode
 from ui.views.gallery import render_gallery
 from ui.views.voice_lab import render_voice_lab
@@ -27,6 +28,13 @@ st.set_page_config(
     layout="wide",
     initial_sidebar_state="expanded",
 )
+
+# Restore styles from Supabase (only runs once per session/deploy if cached, 
+# but Streamlit runs this every time, so we could optimize, but for now we run it)
+if "supabase_restored" not in st.session_state:
+    restore_all_styles()
+    st.session_state["supabase_restored"] = True
+
 css_path = ROOT / "ui" / "styles.css"
 if css_path.exists():
     st.markdown(
@@ -77,14 +85,14 @@ with st.sidebar:
             clear_logs()
             st.rerun()
     
-    with st.expander("≡ƒöº Trß║íng th├íi Git Sync", expanded=False):
-        sync_status = check_git_sync_status()
+    with st.expander("≡ƒöº Trß║íng th├íi Supabase", expanded=False):
+        sync_status = check_supabase_status()
         for k, v in sync_status.items():
             st.markdown(f"**{k}**: {v}")
         if not sync_status.get("ready"):
             st.warning(
-                "Cß║ºn khai b├ío `GITHUB_USERNAME` v├á `GITHUB_TOKEN` "
-                "tr├¬n Render Dashboard ─æß╗â bß║¡t t├¡nh n─âng l╞░u dß╗» liß╗çu vß╗ü GitHub."
+                "Cß║ºn khai b├ío `SUPABASE_URL` v├á `SUPABASE_KEY` "
+                "tr├¬n Render Dashboard ─æß╗â bß║¡t t├¡nh n─âng l╞░u dß╗» liß╗çu Style."
             )
 
 mode = st.session_state.mode
diff --git a/ui/controllers/workflow_controller.py b/ui/controllers/workflow_controller.py
index 2c5811b..c826d16 100644
--- a/ui/controllers/workflow_controller.py
+++ b/ui/controllers/workflow_controller.py
@@ -13,7 +13,7 @@ from engine.workflow import (
 from engine.workflow_contracts import WorkflowRunResult
 from engine.gemini_client import call_gemini
 from engine.style_manager import get_style_detail, save_style_file
-from engine.utils import read_text, load_yaml, auto_git_sync
+from engine.utils import read_text, load_yaml
 from engine.workflow_persistence import atomic_write_text
 
 
@@ -136,12 +136,6 @@ def run_real_learning(
     if not isinstance(learning_dir, Path):
         raise RuntimeError(f"run_learning_loop trß║ú vß╗ü {type(learning_dir)}, kh├┤ng phß║úi Path. Kiß╗âm tra lß║íi cß╗¥ persist.")
     
-    # Sync production_blog.md + learning results vß╗ü GitHub
-    auto_git_sync(
-        [str(r_dir), str(learning_dir)],
-        f"feat(learning): Sync production_blog + learning results {r_dir.name}",
-    )
-    
     sug_path = learning_dir / "workflow_tuning_suggestions.md"
     if sug_path.exists():
         return read_text(sug_path)
