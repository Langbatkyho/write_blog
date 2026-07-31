import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.style_manager import list_styles
from engine.utils import read_text
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
