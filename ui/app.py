import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.style_manager import list_styles
from engine.utils import read_text, check_git_sync_status
from engine.app_logger import get_logs, clear_logs
from ui.state import initialize_session_state, switch_mode
from ui.views.gallery import render_gallery
from ui.views.voice_lab import render_voice_lab
from ui.views.workbench import render_workbench
from ui.views.blog_workflow import render_blog_workflow





st.set_page_config(
    page_title="Nhà xuất bản happiLab",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)
css_path = ROOT / "ui" / "styles.css"
if css_path.exists():
    st.markdown(
        f"<style>{read_text(css_path)}</style>", unsafe_allow_html=True
    )

initialize_session_state(st.session_state)

with st.sidebar:
    st.markdown("### 🧭 Chọn loại blog")
    selected_mode = st.radio(
        "Writing Mode",
        options=["deep", "moment"],
        format_func=lambda value: (
            "🌊 Deep Blog Mode (7 Trợ lý AI)"
            if value == "deep"
            else "⚡ Moment Blog Mode (6 Trợ lý AI)"
        ),
        index=0 if st.session_state.mode == "deep" else 1,
        key="mode_radio",
    )
    if switch_mode(st.session_state, selected_mode):
        st.rerun()
        
    st.divider()
    st.markdown("### 🗂️ Menu chính")
    main_menu = st.radio(
        "Menu chức năng",
        options=["Viết bài blog", "Quản lý phong cách viết"],
        key="main_menu_radio",
        label_visibility="collapsed",
    )
    
    # ── Log Panel ──
    st.divider()
    with st.expander("📊 Nhật ký hệ thống", expanded=False):
        logs = get_logs(30)
        if logs:
            for entry in logs:
                icon = "🟢" if entry["level"] == "INFO" else "🔴"
                st.markdown(
                    f"`{entry['time']}` {icon} **[{entry['tag']}]** {entry['msg']}",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Chưa có log nào. Log sẽ xuất hiện khi bạn chạy workflow.")
        if st.button("🗑️ Xóa log", key="clear_logs_btn"):
            clear_logs()
            st.rerun()
    
    with st.expander("🔧 Trạng thái Git Sync", expanded=False):
        sync_status = check_git_sync_status()
        for k, v in sync_status.items():
            st.markdown(f"**{k}**: {v}")
        if not sync_status.get("ready"):
            st.warning(
                "Cần khai báo `GITHUB_USERNAME` và `GITHUB_TOKEN` "
                "trên Render Dashboard để bật tính năng lưu dữ liệu về GitHub."
            )

mode = st.session_state.mode
styles = list_styles(mode)
st.title("✍️ Nhà xuất bản happiLab")
st.markdown(f"Chế độ hiện tại: `{mode.upper()}`")

if main_menu == "Viết bài blog":
    render_blog_workflow(styles, mode)
else:
    quang_tri, tao_moi, thu_nghiem = st.tabs(
        [
            "📚 Quản trị phong cách viết",
            "🎨 Tạo mới phong cách viết",
            "🧪 Thử nghiệm phong cách viết",
        ]
    )
    with quang_tri:
        render_gallery(styles, mode)
    with tao_moi:
        render_voice_lab(mode)
    with thu_nghiem:
        render_workbench(styles, mode)
