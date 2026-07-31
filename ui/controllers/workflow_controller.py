from __future__ import annotations

import json
import re
from pathlib import Path

from engine.workflow import (
    preview_workflow,
    preview_workflow_text,
    run_workflow,
    run_learning_loop,
)
from engine.workflow_contracts import WorkflowRunResult
from engine.gemini_client import call_gemini
from engine.style_manager import get_style_detail, save_style_file
from engine.utils import read_text, load_yaml, auto_git_sync
from engine.workflow_persistence import atomic_write_text


def preview_workbench(
    *,
    config_path: Path,
    style: str,
    mode: str,
    input_path: Path | None = None,
    input_markdown: str | None = None,
) -> WorkflowRunResult:
    if (input_path is None) == (input_markdown is None):
        raise ValueError("Phải truyền đúng một nguồn input cho workbench.")
    if input_markdown is not None:
        return preview_workflow_text(
            config_path,
            input_markdown,
            style=style,
            mode=mode,
            run_source="ui",
        )
    assert input_path is not None
    return preview_workflow(
        config_path,
        input_path,
        style=style,
        mode=mode,
        run_source="ui",
    )


def preview_metadata(preview: WorkflowRunResult) -> dict:
    return {
        "mode": preview.mode,
        "style": preview.style,
        "status": preview.status,
        "run_source": preview.run_source,
        "persisted": preview.persisted,
        "api_attempted": preview.api_attempted,
        "api_called": preview.api_called,
        "stages": {
            stage_id: {
                "status": result.status,
                "provider": result.provider,
                "model": result.model,
                "api_attempted": result.api_attempted,
                "api_called": result.api_called,
                "duration_ms": result.duration_ms,
            }
            for stage_id, result in preview.stages.items()
        },
    }


def run_real_workflow(
    *,
    config_path: Path,
    style: str,
    mode: str,
    input_text: str,
    length: str,
) -> tuple[str, str, str]:
    modified_input = f"{input_text}\n\n---\n**Ghi chú hệ thống**: Độ dài bài viết mong muốn: {length}."
    
    result = run_workflow(
        config_path=config_path,
        input_path=None,
        input_markdown=modified_input,
        dry_run=False,
        llm_client=call_gemini,
        style=style,
        mode=mode,
        persist=True,
        run_source="ui",
    )
    run_dir = result
    if not isinstance(run_dir, Path):
        raise RuntimeError(f"run_workflow trả về {type(run_dir)}, không phải Path. Kiểm tra lại cờ persist.")
    
    edited_file = "moment_edited.md" if mode == "moment" else "edited_blog.md"
    edited_content = ""
    edited_path = run_dir / edited_file
    if edited_path.exists():
        edited_content = read_text(edited_path)
    else:
        final_path = run_dir / "final_blog.md"
        if final_path.exists():
            edited_content = read_text(final_path)

    run_log = ""
    log_path = run_dir / "run_log.md"
    if log_path.exists():
        run_log = read_text(log_path)
        
    # Bỏ phần Edit Log theo yêu cầu người dùng
    # Match: "## Edit Log", "edit_log.md", "### edit_log.md", v.v.
    parts = re.split(r"(?im)^#{0,6}\s*edit[_\s]*log(?:\.md)?\s*$", edited_content)
    edited_content_stripped = parts[0].strip()
        
    return edited_content_stripped, run_log, str(run_dir)


def run_real_learning(
    *,
    config_path: Path,
    run_dir: str,
    human_edited: str,
) -> str:
    r_dir = Path(run_dir)
    atomic_write_text(r_dir / "production_blog.md", human_edited)
    
    learning_dir = run_learning_loop(
        config_path=config_path,
        run_dir=r_dir,
        dry_run=False,
        llm_client=call_gemini,
        persist=True,
        run_source="ui",
    )
    if not isinstance(learning_dir, Path):
        raise RuntimeError(f"run_learning_loop trả về {type(learning_dir)}, không phải Path. Kiểm tra lại cờ persist.")
    
    # Sync production_blog.md + learning results về GitHub
    auto_git_sync(
        [str(r_dir), str(learning_dir)],
        f"feat(learning): Sync production_blog + learning results {r_dir.name}",
    )
    
    sug_path = learning_dir / "workflow_tuning_suggestions.md"
    if sug_path.exists():
        return read_text(sug_path)
    return "Không tìm thấy file gợi ý."


def apply_style_upgrade(mode: str, slug: str, suggestions: str, config: dict) -> list[str]:
    detail = get_style_detail(mode, slug)
    style_dir = Path(detail["directory"])
    files = detail["files"]
    
    # Bước 1: Hỏi LLM xem file nào cần sửa (output nhỏ, không bị truncate)
    file_list_str = "\n".join(f"- {f}" for f in files)
    filter_prompt = f"""Dưới đây là danh sách các file YAML của style '{slug}':
{file_list_str}

Và đây là các đề xuất tinh chỉnh:
{suggestions}

Hãy liệt kê CHÍNH XÁC tên các file cần sửa (chỉ file thực sự bị ảnh hưởng bởi đề xuất).
Trả về JSON duy nhất: {{"files_to_update": ["file1.yaml", "file2.yaml"]}}
Không trả về text ngoài JSON."""
    
    filter_resp = call_gemini(filter_prompt, config, max_output_tokens=1024)
    # Clean markdown fences
    for prefix in ("```json", "```"):
        if filter_resp.startswith(prefix):
            filter_resp = filter_resp[len(prefix):]
    if filter_resp.endswith("```"):
        filter_resp = filter_resp[:-3]
    
    try:
        filter_data = json.loads(filter_resp.strip())
        files_to_update = [f for f in filter_data.get("files_to_update", []) if f in files]
    except Exception:
        # Fallback: cập nhật tất cả file
        files_to_update = list(files)
    
    if not files_to_update:
        return []
    
    # Bước 2: Gọi LLM riêng cho từng file cần sửa
    saved_files = []
    for filename in files_to_update:
        original_content = read_text(style_dir / filename)
        
        per_file_prompt = f"""Bạn là một AI cấu hình hệ thống.
Dưới đây là nội dung YAML hiện tại của file '{filename}' thuộc style '{slug}':

{original_content}

Và đây là các đề xuất tinh chỉnh:
{suggestions}

Nhiệm vụ: Áp dụng CHÍNH XÁC các đề xuất liên quan vào file này.
Giữ nguyên cấu trúc YAML hợp đồng (name, output, v.v).
Trả về TOÀN BỘ nội dung YAML đã sửa (không phải JSON, không có markdown fences).
Nếu file không cần sửa, trả về nguyên nội dung gốc."""

        updated_content = call_gemini(
            per_file_prompt, config, max_output_tokens=8192
        )
        
        # Bỏ markdown fences nếu LLM tự thêm
        updated_content = updated_content.strip()
        for prefix in ("```yaml", "```yml", "```"):
            if updated_content.startswith(prefix):
                updated_content = updated_content[len(prefix):]
                break
        if updated_content.endswith("```"):
            updated_content = updated_content[:-3]
        updated_content = updated_content.strip()
        
        # Chỉ lưu nếu nội dung thực sự thay đổi
        if updated_content and updated_content != original_content.strip():
            success, err, _ = save_style_file(mode, slug, filename, updated_content)
            if not success:
                raise ValueError(f"Lỗi khi lưu {filename}: {err}")
            saved_files.append(filename)
    
    return saved_files
