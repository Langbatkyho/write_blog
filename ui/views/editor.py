from __future__ import annotations

from pathlib import Path

import streamlit as st

from engine.style_manager import get_style_detail, save_style_file
from engine.utils import read_text


def render_editor(styles: list[dict], mode: str, code_editor=None) -> None:
    st.subheader("💻 Trình soạn thảo cấu hình Agent YAML")
    if not styles:
        st.warning("Không có style nào để chỉnh sửa.")
        return
    slugs = [style["slug"] for style in styles]
    current = st.session_state.get("selected_style_slug", "reflective")
    if current not in slugs:
        current = slugs[0]
    selected_slug = st.selectbox(
        "Chọn Style để chỉnh sửa:",
        options=slugs,
        index=slugs.index(current),
        key="editor_style_select",
    )
    st.session_state.selected_style_slug = selected_slug
    try:
        detail = get_style_detail(mode, selected_slug)
        files = detail.get("files", [])
        all_files = (
            ["style_meta.yaml"] + files
            if "style_meta.yaml" not in files
            else files
        )
        selected_file = st.selectbox(
            "Chọn file YAML:", options=all_files, key="editor_file_select"
        )
        file_path = Path(detail["directory"]) / selected_file
        content = read_text(file_path) if file_path.exists() else "# File not found"
        if code_editor:
            response = code_editor(
                content,
                lang="yaml",
                theme="cobalt",
                height=[15, 30],
                buttons=[],
                key=f"ce_{selected_slug}_{selected_file}",
            )
            edited = response.get("text", content)
        else:
            edited = st.text_area(
                "Nội dung file YAML", value=content, height=450
            )
        if st.button("💾 Lưu thay đổi", type="primary"):
            success, error, warning = save_style_file(
                mode, selected_slug, selected_file, edited
            )
            if not success:
                st.error(f"❌ {error}")
            else:
                if warning:
                    st.warning(warning)
                st.success("✅ Đã lưu bằng transaction staging/rollback.")
    except Exception as exc:
        st.error(f"Không thể tải style: {exc}")
