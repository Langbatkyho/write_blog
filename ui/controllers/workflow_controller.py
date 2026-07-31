from __future__ import annotations

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
from engine.utils import read_text, load_yaml
from engine.workflow_persistence import atomic_write_text
import json


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
        
    return edited_content, run_log, str(run_dir)


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
    sug_path = learning_dir / "workflow_tuning_suggestions.md"
    if sug_path.exists():
        return read_text(sug_path)
    return "Không tìm thấy file gợi ý."


def apply_style_upgrade(mode: str, slug: str, suggestions: str, config: dict) -> list[str]:
    detail = get_style_detail(mode, slug)
    style_dir = Path(detail["directory"])
    files = detail["files"]
    
    yaml_contents = []
    for f in files:
        content = read_text(style_dir / f)
        yaml_contents.append(f"--- FILE: {f} ---\n{content}\n")
    
    combined_yaml = "\n".join(yaml_contents)
    
    prompt = f"""
Bạn là một AI cấu hình hệ thống.
Dưới đây là các file YAML hiện tại của style '{slug}':
{combined_yaml}

Và đây là các đề xuất tinh chỉnh:
{suggestions}

Nhiệm vụ của bạn là áp dụng CHÍNH XÁC các đề xuất trên vào các file YAML tương ứng.
Bạn CHỈ thay đổi nội dung các file cần sửa.
Trả về định dạng JSON duy nhất như sau:
{{
  "updated_files": [
    {{ "filename": "tên_file.yaml", "content": "Nội dung YAML đầy đủ sau khi sửa" }}
  ]
}}
Tuyệt đối không trả về text ngoài JSON. Đảm bảo cấu trúc YAML hoàn chỉnh và đúng format hợp đồng (có name, output, v.v).
"""
    response = call_gemini(prompt, config)
    
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    
    try:
        data = json.loads(response.strip())
    except Exception as e:
        raise ValueError(f"LLM trả về JSON không hợp lệ: {e}\n{response}")
    
    updated_files = data.get("updated_files", [])
    if not updated_files:
        return []
    
    saved_files = []
    for item in updated_files:
        filename = item["filename"]
        content = item["content"]
        if filename not in files:
            continue
        success, err, _ = save_style_file(mode, slug, filename, content)
        if not success:
            raise ValueError(f"Lỗi khi lưu {filename}: {err}")
        saved_files.append(filename)
    
    return saved_files
