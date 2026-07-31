from __future__ import annotations

from html import escape

import streamlit as st

from engine.style_manager import delete_style, rename_style


@st.dialog("🏷️ Đổi tên Style")
def show_rename_dialog(
    mode: str,
    old_slug: str,
    old_name: str,
    is_protected: bool,
) -> None:
    st.markdown(f"Đang đổi tên cho style: **{old_name}** (`{old_slug}`)")
    new_name = st.text_input("Tên hiển thị mới", value=old_name)
    new_slug = st.text_input(
        "Slug hệ thống mới (a-z, 0-9, dấu gạch ngang)",
        value=old_slug,
        disabled=is_protected,
        help=(
            "Không thể đổi slug của System Style bảo vệ."
            if is_protected
            else "2-50 ký tự hợp lệ cho tên folder."
        ),
    )
    if st.button("💾 Lưu Đổi Tên", type="primary"):
        success, message = rename_style(mode, old_slug, new_name, new_slug)
        if success:
            if st.session_state.get("selected_style_slug") == old_slug:
                st.session_state.selected_style_slug = new_slug
            st.rerun()
        st.error(f"❌ {message}")


@st.dialog("🗑️ Xác nhận gỡ Style")
def show_delete_dialog(mode: str, slug: str, name: str) -> None:
    st.warning(
        f"Bạn có chắc chắn muốn gỡ style **{name}** (`{slug}`) không? "
        "Style sẽ được chuyển vào thùng rác có thể khôi phục."
    )
    cancel, confirm = st.columns(2)
    if cancel.button("❌ Hủy bỏ"):
        st.rerun()
    if confirm.button("🗑️ Chuyển vào thùng rác", type="primary"):
        success, message = delete_style(mode, slug)
        if success:
            if st.session_state.get("selected_style_slug") == slug:
                st.session_state.selected_style_slug = "reflective"
            st.rerun()
        st.error(f"❌ {message}")


def render_gallery(styles: list[dict], mode: str) -> None:
    st.subheader(f"📚 Bộ sưu tập Văn phong — Mode {mode.upper()}")
    st.markdown(
        "Khám phá, chỉnh sửa hoặc quản lý các phong cách viết có sẵn."
    )
    if not styles:
        st.info("Chưa có style nào trong chế độ này.")
        return
    columns = st.columns(2)
    for index, style in enumerate(styles):
        with columns[index % 2]:
            protected = style.get("is_protected", False)
            badge_class = "badge-protected" if protected else "badge-custom"
            badge_text = "🔒 SYSTEM STYLE" if protected else "✨ CUSTOM STYLE"
            description = escape(style.get("description", "Không có mô tả."))
            st.markdown(
                f"""
                <div class="style-card">
                    <div class="style-card-title">
                        <span>{escape(style.get('name', style['slug']))}
                        <code>({style['slug']})</code></span>
                        <span class="{badge_class}">{badge_text}</span>
                    </div>
                    <div class="style-card-desc">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            rename, remove = st.columns([1, 1])
            if rename.button("🏷️ Đổi tên", key=f"rename_{style['slug']}"):
                show_rename_dialog(
                    mode,
                    style["slug"],
                    style.get("name", style["slug"]),
                    protected,
                )
            if remove.button(
                "🗑️ Gỡ",
                key=f"del_{style['slug']}",
                disabled=protected,
            ):
                show_delete_dialog(
                    mode, style["slug"], style.get("name", style["slug"])
                )
