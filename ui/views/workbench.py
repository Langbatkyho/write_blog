from __future__ import annotations

import streamlit as st

from engine.style_manager import validate_style_contract
from engine.utils import resolve_path
from ui.controllers.workflow_controller import (
    preview_metadata,
    preview_workbench,
)


def render_workbench(styles: list[dict], mode: str) -> None:
    st.subheader("🧪 Bàn Kiểm chứng Hợp đồng Định tuyến")
    st.markdown(
        "Preview in-memory, không gọi API và không tạo artifact trong `runs/`."
    )
    if not styles:
        st.warning("Không có style để kiểm chứng.")
        return
    style = st.selectbox(
        "Chọn Style kiểm chứng:",
        options=[item["slug"] for item in styles],
        key=f"wb_style_select_{mode}",
    )
    source = st.radio(
        "Nguồn văn bản:",
        ["Mẫu chuẩn (template)", "Dán văn bản tùy chỉnh"],
        horizontal=True,
    )
    custom = ""
    if source == "Dán văn bản tùy chỉnh":
        custom = st.text_area("Dán nội dung", height=120)
    if not st.button("⚡ Chạy Preview", type="primary"):
        return
    try:
        validate_style_contract(mode, style)
        config = resolve_path("engine/config.example.yaml")
        if source == "Dán văn bản tùy chỉnh":
            preview = preview_workbench(
                config_path=config,
                input_markdown=custom,
                style=style,
                mode=mode,
            )
        else:
            sample = (
                "examples/moment_blog_input_template.md"
                if mode == "moment"
                else "examples/blog_input_template.md"
            )
            preview = preview_workbench(
                config_path=config,
                input_path=resolve_path(sample),
                style=style,
                mode=mode,
            )
        st.success("✅ Preview hoàn tất; persisted=false, api_called=false.")
        st.json(preview_metadata(preview))
        completed = [
            (stage_id, result)
            for stage_id, result in preview.stages.items()
            if result.status == "completed"
        ]
        tabs = st.tabs([stage_id for stage_id, _ in completed])
        for tab, (_, result) in zip(tabs, completed):
            with tab:
                st.code(result.artifact, language="markdown")
    except Exception as exc:
        st.error(f"❌ Preview thất bại: {exc}")
