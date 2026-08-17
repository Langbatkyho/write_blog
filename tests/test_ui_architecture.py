from pathlib import Path

from streamlit.testing.v1 import AppTest

from engine.voice_lab.models import (
    AnalysisResult,
    CalibrationSession,
    DimensionProfile,
    EvidenceClaim,
    InterviewQuestion,
    StyleProfile,
    VoiceDNA,
)
from engine.voice_lab.prompts import (
    InterviewDimensionPatch,
    InterviewPatchPayload,
)
from ui.state import initialize_session_state, switch_mode
from ui.views import voice_lab as voice_lab_view


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


def _button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


def _runs_signature() -> tuple[tuple[str, int, int], ...]:
    return tuple(
        sorted(
            (
                str(path.relative_to(RUNS_DIR)),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in RUNS_DIR.rglob("*")
            if path.is_file()
        )
    )


def _analysis_result(mode: str = "deep") -> AnalysisResult:
    evidence = EvidenceClaim(
        id="evidence-tone",
        sample_id="sample_1",
        dimension="tone",
        claim="Giọng viết gần gũi.",
        exact_quote="Một đoạn văn đủ dài để kiểm thử Voice Lab.",
    )
    profile = StyleProfile(
        slug="ui-acceptance",
        mode=mode,
        analysis_status="complete",
        dna=VoiceDNA(
            tone=DimensionProfile(
                description="ấm áp và trực diện",
                confidence=0.9,
                evidence_ids=[evidence.id],
            )
        ),
        evidence=[evidence],
    )
    return AnalysisResult(
        profile=profile,
        routing_mode="single_pass",
    )


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


def test_streamlit_has_four_tabs_and_mode_round_trip_resets_voice_lab():
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run(timeout=20)
    main_menu_radio = next(item for item in app.radio if getattr(item, "key", "") == "main_menu_radio")
    main_menu_radio.set_value("Quản lý phong cách viết")
    app.run(timeout=20)
    
    assert [tab.label for tab in app.tabs] == [
        "📚 Quản trị phong cách viết",
        "🎨 Tạo mới phong cách viết",
        "🧪 Thử nghiệm phong cách viết",
    ]

    app.session_state["vl_step"] = 4
    app.session_state["vl_calibration_selection"] = "A"
    mode_radio = next(item for item in app.radio if item.label == "Writing Mode")
    mode_radio.set_value("moment")
    app.run(timeout=20)
    
    main_menu_radio = next(item for item in app.radio if getattr(item, "key", "") == "main_menu_radio")
    main_menu_radio.set_value("Quản lý phong cách viết")
    app.run(timeout=20)

    assert app.session_state["mode"] == "moment"
    assert app.session_state["vl_step"] == 1
    assert app.session_state["vl_calibration_selection"] is None
    
    workbench_style = next(
        item
        for item in app.selectbox
        if item.label == "Chọn Style kiểm chứng:"
    )
    assert workbench_style.value in workbench_style.options
    assert "provocative" not in workbench_style.options
    assert app.session_state["wb_style_select_moment"] in workbench_style.options

    mode_radio = next(item for item in app.radio if item.label == "Writing Mode")
    mode_radio.set_value("deep")
    app.run(timeout=20)
    assert app.session_state["mode"] == "deep"
    assert app.session_state["vl_step"] == 1
    assert not app.exception


def test_workbench_template_and_custom_preview_are_in_memory():
    before = _runs_signature()
    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run(timeout=20)

    main_menu_radio = next(item for item in app.radio if getattr(item, "key", "") == "main_menu_radio")
    main_menu_radio.set_value("Quản lý phong cách viết")
    app.run(timeout=20)

    _button(app, "⚡ Chạy Preview").click()
    app.run(timeout=20)
    assert any("persisted=false" in item.value for item in app.success)
    assert not app.error
    assert not app.exception

    source_radio = next(
        item for item in app.radio if item.label == "Nguồn văn bản:"
    )
    source_radio.set_value("Dán văn bản tùy chỉnh")
    app.run(timeout=20)
    custom_input = next(
        item for item in app.text_area if item.label == "Dán nội dung"
    )
    custom_input.set_value("# Chủ đề\n\nMột ghi chú tùy chỉnh.")
    _button(app, "⚡ Chạy Preview").click()
    app.run(timeout=20)
    assert any("persisted=false" in item.value for item in app.success)
    assert not app.error
    assert not app.exception
    assert _runs_signature() == before


def test_voice_lab_wizard_reaches_compile_review_with_fakes(monkeypatch):
    before = _runs_signature()
    result = _analysis_result()
    question = InterviewQuestion(
        id="question-tone",
        dimension="tone",
        question="Bạn muốn giữ giọng này không?",
        context="Kiểm thử UI.",
    )
    patch = InterviewPatchPayload(
        changes=[
            InterviewDimensionPatch(
                dimension="tone",
                description="ấm áp, tự nhiên",
                strength=0.75,
                do=["viết trực diện"],
                avoid=["lên lớp"],
            )
        ]
    )
    calibration = CalibrationSession(
        dimension="tone",
        content_brief="Kiểm thử",
        variant_a="Bản A dùng để kiểm thử.",
        variant_b="Bản B dùng để kiểm thử.",
        shuffle_mapping={"A": "amplified", "B": "restrained"},
    )
    calls: list[str] = []

    def fake_analyze(samples, mode):
        calls.append("analyze")
        assert samples == ["Một đoạn văn đủ dài để kiểm thử Voice Lab."]
        assert mode == "deep"
        return result

    def fake_confirm(profile, proposed, questions, answers):
        calls.append("confirm")
        assert proposed == patch
        assert questions == [question]
        assert answers[question.id] == "Giữ nét ấm áp."
        return profile

    def fake_compile(profile, session, selected, mode):
        calls.append("compile")
        assert session == calibration
        assert selected == "A"
        assert mode == "deep"
        updated = profile.model_copy(deep=True)
        updated.status = "confirmed"
        updated.is_draft = False
        return updated, {
            "writing_agent.yaml": {
                "effective_skill": {"voice_lab_style": {"tone": ["ấm áp"]}}
            }
        }

    monkeypatch.setattr(voice_lab_view, "analyze_voice_samples", fake_analyze)
    monkeypatch.setattr(
        voice_lab_view, "prepare_interview", lambda profile: [question]
    )
    monkeypatch.setattr(voice_lab_view, "propose_patch", lambda *args: patch)
    monkeypatch.setattr(voice_lab_view, "confirm_patch", fake_confirm)
    monkeypatch.setattr(
        voice_lab_view,
        "prepare_calibration",
        lambda profile, dimension: calibration,
    )
    monkeypatch.setattr(
        voice_lab_view, "apply_calibration_and_compile", fake_compile
    )
    monkeypatch.setattr(
        voice_lab_view,
        "publish_profile",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("AppTest không được publish vào workspace thật.")
        ),
    )

    app = AppTest.from_file(str(ROOT / "ui" / "app.py")).run(timeout=20)
    
    main_menu_radio = next(item for item in app.radio if getattr(item, "key", "") == "main_menu_radio")
    main_menu_radio.set_value("Quản lý phong cách viết")
    app.run(timeout=20)

    sample = next(item for item in app.text_area if item.label == "Mẫu 1")
    sample.set_value("Một đoạn văn đủ dài để kiểm thử Voice Lab.")
    _button(app, "🔍 Phân tích Mẫu").click()
    app.run(timeout=20)
    assert app.session_state["vl_step"] == 2

    _button(app, "➡️ Tiếp tục").click()
    app.run(timeout=20)
    assert app.session_state["vl_step"] == 3

    answer = next(item for item in app.text_input if item.label == "Câu trả lời")
    answer.set_value("Giữ nét ấm áp.")
    _button(app, "Tạo đề xuất cập nhật").click()
    app.run(timeout=20)
    _button(app, "Xác nhận và tạo A/B").click()
    app.run(timeout=20)
    assert app.session_state["vl_step"] == 4

    _button(app, "Chọn Bản A").click()
    # AppTest retains the previous text_input node for one collection cycle
    # after st.rerun, while Streamlit has already removed its widget state.
    app.session_state[f"answer_{question.id}"] = "Giữ nét ấm áp."
    app.run(timeout=20)
    _button(app, "➡️ Compile & Review").click()
    app.run(timeout=20)
    assert app.session_state["vl_step"] == 5
    assert calls == ["analyze", "confirm", "compile"]
    assert any("Review & Publish" in item.value for item in app.markdown)
    assert not app.exception
    assert _runs_signature() == before
