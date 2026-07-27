from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.state import initialize_session_state, switch_mode


ROOT = Path(__file__).resolve().parents[1]


def test_session_state_initialization_and_mode_reset():
    state = {}
    initialize_session_state(state)
    state["vl_step"] = 4
    state["vl_calibration_selection"] = "A"
    assert switch_mode(state, "moment") is True
    assert state["mode"] == "moment"
    assert state["vl_step"] == 1
    assert state["vl_calibration_selection"] is None
    assert switch_mode(state, "moment") is False


def test_streamlit_app_smoke_has_no_exception():
    app = AppTest.from_file(str(ROOT / "ui" / "app.py"))
    app.run(timeout=20)
    assert not app.exception
