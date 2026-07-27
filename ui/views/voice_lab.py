from __future__ import annotations

import yaml
import streamlit as st

from engine.voice_lab.interview import DIMENSION_VI
from engine.voice_lab.models import AnalysisError
from ui.controllers.voice_lab_controller import (
    analyze_voice_samples,
    apply_calibration_and_compile,
    confirm_patch,
    prepare_calibration,
    prepare_interview,
    propose_patch,
    publish_profile,
)


STEP_LABELS = [
    "1. Samples",
    "2. Evidence",
    "3. Interview",
    "4. Calibration",
    "5. Publish",
]


def _dimensions(profile) -> list[str]:
    if not profile or not profile.dna:
        return []
    return list(profile.dna.non_empty_dimensions())


def _start_calibration(profile, dimension: str) -> None:
    st.session_state.vl_calibration = prepare_calibration(profile, dimension)
    st.session_state.vl_calibration_selection = None
    st.session_state.vl_step = 4


def _render_progress(step: int) -> None:
    for index, column in enumerate(st.columns(5), start=1):
        with column:
            label = STEP_LABELS[index - 1]
            if index == step:
                st.markdown(f"**👉 {label}**")
            elif index < step:
                st.markdown(f"✅ ~~{label}~~")
            else:
                st.caption(label)


def _render_samples(mode: str) -> None:
    st.markdown("### Bước 1: Nhập bài viết mẫu")
    for index, sample in enumerate(st.session_state.vl_samples):
        st.session_state.vl_samples[index] = st.text_area(
            f"Mẫu {index + 1}",
            value=sample,
            height=150,
            key=f"sample_{index}",
        )
    if st.button("➕ Thêm Mẫu"):
        st.session_state.vl_samples.append("")
        st.rerun()
    if st.button("🔍 Phân tích Mẫu", type="primary"):
        try:
            with st.spinner("Đang phân tích Voice DNA bằng Gemini..."):
                result = analyze_voice_samples(
                    st.session_state.vl_samples, mode
                )
            st.session_state.vl_profile = result.profile
            st.session_state.vl_dna = result.profile.dna
            st.session_state.vl_claims = result.profile.evidence
            st.session_state.vl_interview_patch = None
            st.session_state.vl_step = 2
            st.rerun()
        except (AnalysisError, ValueError) as exc:
            st.error(
                exc.user_message if isinstance(exc, AnalysisError) else str(exc)
            )


def _render_evidence() -> None:
    st.markdown("### Bước 2: Xem xét Bằng chứng")
    profile = st.session_state.vl_profile
    if st.session_state.vl_dna:
        st.json(st.session_state.vl_dna.model_dump())
    for claim in st.session_state.vl_claims:
        st.info(
            f"**{claim.dimension}** — {claim.claim}\n\n"
            f"`{claim.sample_id}`: “{claim.exact_quote}”"
        )
    if profile and profile.rejected_evidence:
        with st.expander(
            f"Evidence đã loại ({len(profile.rejected_evidence)})"
        ):
            for claim in profile.rejected_evidence:
                st.warning(
                    f"{claim.dimension}: {claim.rejection_reason} — "
                    f"“{claim.exact_quote}”"
                )
    back, onward = st.columns(2)
    if back.button("⬅️ Quay lại", key="evidence_back"):
        st.session_state.vl_step = 1
        st.rerun()
    if onward.button("➡️ Tiếp tục", type="primary"):
        questions = prepare_interview(profile)
        st.session_state.vl_interview = questions
        try:
            if questions:
                st.session_state.vl_step = 3
            else:
                dimensions = _dimensions(profile)
                if not dimensions:
                    raise ValueError("Profile chưa đủ evidence để calibration.")
                _start_calibration(profile, dimensions[0])
            st.rerun()
        except (AnalysisError, ValueError) as exc:
            st.error(
                exc.user_message if isinstance(exc, AnalysisError) else str(exc)
            )


def _render_interview() -> None:
    st.markdown("### Bước 3: Phỏng vấn Bổ sung")
    for question in st.session_state.vl_interview:
        st.write(
            f"**{DIMENSION_VI.get(question.dimension, question.dimension)}**: "
            f"{question.question}"
        )
        st.caption(question.context)
        st.session_state.vl_answers[question.id] = st.text_input(
            "Câu trả lời",
            key=f"answer_{question.id}",
            value=st.session_state.vl_answers.get(question.id, ""),
        )
    if st.button("Tạo đề xuất cập nhật", type="primary"):
        try:
            st.session_state.vl_interview_patch = propose_patch(
                st.session_state.vl_profile,
                st.session_state.vl_interview,
                st.session_state.vl_answers,
            )
        except AnalysisError as exc:
            st.error(exc.user_message)
    patch = st.session_state.vl_interview_patch
    if patch is not None:
        st.json(patch.model_dump())
        confirm, skip = st.columns(2)
        if confirm.button("Xác nhận và tạo A/B", type="primary"):
            try:
                profile = confirm_patch(
                    st.session_state.vl_profile,
                    patch,
                    st.session_state.vl_interview,
                    st.session_state.vl_answers,
                )
                dimensions = _dimensions(profile)
                target = st.session_state.vl_interview[0].dimension
                if target not in dimensions:
                    target = dimensions[0]
                st.session_state.vl_profile = profile
                st.session_state.vl_dna = profile.dna
                _start_calibration(profile, target)
                st.rerun()
            except (AnalysisError, ValueError) as exc:
                st.error(
                    exc.user_message
                    if isinstance(exc, AnalysisError)
                    else str(exc)
                )
        if skip.button("Bỏ qua phỏng vấn"):
            try:
                dimensions = _dimensions(st.session_state.vl_profile)
                _start_calibration(
                    st.session_state.vl_profile, dimensions[0]
                )
                st.rerun()
            except (AnalysisError, ValueError, IndexError) as exc:
                st.error(
                    exc.user_message
                    if isinstance(exc, AnalysisError)
                    else str(exc)
                )


def _render_calibration(mode: str) -> None:
    st.markdown("### Bước 4: Blind A/B Calibration")
    session = st.session_state.vl_calibration
    if session is None:
        st.error("Calibration session chưa được tạo.")
        return
    st.write(
        f"Chọn biến thể phù hợp nhất cho "
        f"**{DIMENSION_VI.get(session.dimension, session.dimension)}**."
    )
    left, right = st.columns(2)
    with left:
        st.info(session.variant_a)
        if st.button("Chọn Bản A"):
            st.session_state.vl_calibration_selection = "A"
    with right:
        st.info(session.variant_b)
        if st.button("Chọn Bản B"):
            st.session_state.vl_calibration_selection = "B"
    selected = st.session_state.vl_calibration_selection
    if selected and st.button("➡️ Compile & Review", type="primary"):
        try:
            profile, compiled = apply_calibration_and_compile(
                st.session_state.vl_profile, session, selected, mode
            )
            st.session_state.vl_profile = profile
            st.session_state.vl_dna = profile.dna
            st.session_state.vl_compiled_ir = compiled
            st.session_state.vl_calibration_selection = None
            st.session_state.vl_step = 5
            st.rerun()
        except (AnalysisError, ValueError) as exc:
            st.error(
                exc.user_message if isinstance(exc, AnalysisError) else str(exc)
            )


def _render_publish(mode: str) -> None:
    st.markdown("### Bước 5: Review & Publish")
    profile = st.session_state.vl_profile
    compiled = st.session_state.vl_compiled_ir
    if profile:
        st.json(profile.model_dump())
    if compiled:
        total_chars = sum(
            len(str(value))
            for artifact in compiled.values()
            for value in artifact.values()
        )
        st.info(f"Ước tính prompt: ~{total_chars // 5}–{total_chars // 3} token")
        with st.expander("🔍 Layer Inspector"):
            filename = st.selectbox("Chọn Agent", list(compiled.keys()))
            artifact = compiled[filename]
            left, right = st.columns(2)
            left.json(artifact)
            right.code(
                yaml.safe_dump(
                    artifact.get("effective_skill", {}),
                    allow_unicode=True,
                    sort_keys=False,
                ),
                language="yaml",
            )
    st.session_state.vl_style_name = st.text_input(
        "Tên Style", value=st.session_state.vl_style_name
    )
    st.session_state.vl_style_slug = st.text_input(
        "Slug Style", value=st.session_state.vl_style_slug
    )
    if st.button("🚀 Publish (Safety Pipeline)", type="primary"):
        try:
            updated, result = publish_profile(
                profile,
                compiled,
                name=st.session_state.vl_style_name,
                slug=st.session_state.vl_style_slug,
                mode=mode,
            )
            st.session_state.vl_profile = updated
            for warning in result.warnings:
                st.warning(warning)
            st.session_state.selected_style_slug = updated.slug
            st.session_state.vl_step = 1
            st.rerun()
        except Exception as exc:
            st.error(f"❌ Publish thất bại, đã rollback: {exc}")


def render_voice_lab(mode: str) -> None:
    st.subheader("🎨 Voice Lab Studio (5-Step Wizard)")
    step = st.session_state.vl_step
    _render_progress(step)
    st.markdown("---")
    if step == 1:
        _render_samples(mode)
    elif step == 2:
        _render_evidence()
    elif step == 3:
        _render_interview()
    elif step == 4:
        _render_calibration(mode)
    elif step == 5:
        _render_publish(mode)
