import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.style_manager import list_styles
from engine.utils import read_text
from ui.state import initialize_session_state, switch_mode
from ui.views.editor import render_editor
from ui.views.gallery import render_gallery
from ui.views.voice_lab import render_voice_lab
from ui.views.workbench import render_workbench


try:
    from code_editor import code_editor
except ImportError:
    code_editor = None


st.set_page_config(
    page_title="Antigravity Mindful Writing OS",
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
    st.markdown("### 🧭 Chế độ viết")
    selected_mode = st.radio(
        "Writing Mode",
        options=["deep", "moment"],
        format_func=lambda value: (
            "🌊 Deep Blog Mode (7 Agents)"
            if value == "deep"
            else "⚡ Moment Blog Mode (6 Agents)"
        ),
        index=0 if st.session_state.mode == "deep" else 1,
        key="mode_radio",
    )
    if switch_mode(st.session_state, selected_mode):
        st.rerun()
    st.caption("Voice Lab dùng Gemini API; Workbench preview không gọi API.")

mode = st.session_state.mode
styles = list_styles(mode)
st.title("✍️ Antigravity Mindful Writing OS")
st.markdown(f"Chế độ hiện tại: `{mode.upper()}`")

gallery, studio, editor, workbench = st.tabs(
    [
        "📚 Style Gallery",
        "🎨 Style Studio",
        "💻 YAML Code Editor",
        "🧪 Live Workbench",
    ]
)
with gallery:
    render_gallery(styles, mode)
with studio:
    render_voice_lab(mode)
with editor:
    render_editor(styles, mode, code_editor=code_editor)
with workbench:
    render_workbench(styles, mode)
