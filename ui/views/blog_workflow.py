from __future__ import annotations

import streamlit as st

from engine.utils import resolve_path, read_text, load_yaml
from engine.email_sender import send_blog_email
from ui.controllers.workflow_controller import (
    run_real_workflow,
    run_real_learning,
    apply_style_upgrade,
)
from ui.state import reset_blog_workflow_state


def render_stepper(current_step: int) -> None:
    steps = [
        "Nhập bài",
        "Kết quả",
        "Sửa bài",
        "Học hỏi",
    ]
    for index, column in enumerate(st.columns(4), start=1):
        with column:
            label = f"{index}. {steps[index-1]}"
            if index == current_step:
                st.markdown(f"**👉 {label}**")
            elif index < current_step:
                st.markdown(f"✅ ~~{label}~~")
            else:
                st.caption(label)


def load_sample_input() -> str:
    path = resolve_path("examples/blog_1.md")
    if path.exists():
        return read_text(path)
    return ""


def render_blog_workflow(styles: list[dict], mode: str) -> None:
    st.subheader("🚀 Trợ lý AI giúp bạn viết blog trong 1 nốt nhạc :D")
    
    step = st.session_state.bw_step
    render_stepper(step)
    
    if step > 1:
        if st.button("🔄 Bắt đầu lại"):
            reset_blog_workflow_state(st.session_state)
            st.rerun()
    
    st.divider()
    
    if step == 1:
        _render_step_1(styles, mode)
    elif step == 2:
        _render_step_2()
    elif step == 3:
        _render_step_3(mode)
    elif step == 4:
        _render_step_4(mode)


def _render_step_1(styles: list[dict], mode: str) -> None:
    if not styles:
        st.warning("Không có style nào để chọn.")
        return

    col1, col2, col3 = st.columns([1.5, 1.5, 3])
    
    with col1:
        selected_style = st.selectbox(
            "Chọn Style:",
            options=[item["slug"] for item in styles],
            index=0,
        )
        st.session_state.selected_style_slug = selected_style
    
    with col2:
        default_val = st.session_state.bw_article_length
        length_val = st.number_input(
            "Độ dài mong muốn (số từ):",
            min_value=100,
            max_value=10000,
            value=default_val,
            step=50,
        )
        st.caption("Gợi ý: Ngắn: 300 - Vừa: 600 - Dài: 1200")
        st.session_state.bw_article_length = length_val
        length_str = f"{length_val} từ"
    
    if not st.session_state.bw_input_text:
        st.session_state.bw_input_text = load_sample_input()
        
    input_text = st.text_area(
        "Nội dung thô / Ý tưởng ban đầu:",
        value=st.session_state.bw_input_text,
        height=300,
    )
    
    if st.button("🚀 Chạy Workflow", type="primary"):
        st.session_state.bw_input_text = input_text
        with st.spinner("Hệ thống đang gọi Trợ lý AI để viết bài... Vui lòng đợi trong vài phút."):
            try:
                config_path = resolve_path("engine/config.example.yaml")
                edited, log, rdir = run_real_workflow(
                    config_path=config_path,
                    style=selected_style,
                    mode=mode,
                    input_text=input_text,
                    length=length_str,
                )
                st.session_state.bw_ai_result = edited
                st.session_state.bw_run_log = log
                st.session_state.bw_run_dir = rdir
                st.session_state.bw_step = 2
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi chạy workflow: {e}")


def _render_step_2() -> None:
    st.success("🎉 Trợ lý AI đã hoàn thành bài viết!")
    
    tab1, tab2 = st.tabs(["📄 Bài viết (AI Draft)", "🔍 Log Quá trình (Run Log)"])
    with tab1:
        st.markdown(st.session_state.bw_ai_result)
    with tab2:
        st.markdown(st.session_state.bw_run_log)
        
    st.divider()
    if st.button("✏️ Tiếp tục chỉnh sửa", type="primary"):
        st.session_state.bw_human_edited = st.session_state.bw_ai_result
        st.session_state.bw_step = 3
        st.rerun()


def _render_step_3(mode: str) -> None:
    st.info("Hãy chỉnh sửa lại bài viết theo ý bạn. Sau đó ấn Phân Tích để AI học hỏi văn phong của bạn.")
    edited = st.text_area(
        "Chỉnh sửa bài viết:",
        value=st.session_state.bw_human_edited,
        height=500,
    )
    
    if st.button("🧠 AI Phân Tích (Learning Loop)", type="primary"):
        st.session_state.bw_human_edited = edited
        with st.spinner("AI đang phân tích các chỉnh sửa của bạn và rút ra bài học..."):
            try:
                config_path = resolve_path("engine/config.example.yaml")
                suggestions = run_real_learning(
                    config_path=config_path,
                    run_dir=st.session_state.bw_run_dir,
                    human_edited=edited,
                )
                st.session_state.bw_tuning_suggestions = suggestions
                st.session_state.bw_step = 4
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi chạy Learning Loop: {e}")


def _render_step_4(mode: str) -> None:
    st.success("💡 Phân tích hoàn tất! Dưới đây là các đề xuất nâng cấp Phong cách viết của bạn.")
    suggestions = st.text_area(
        "Đề xuất tinh chỉnh (Tuning Suggestions):",
        value=st.session_state.bw_tuning_suggestions,
        height=400,
    )
    
    st.warning(
        "Khi bạn ấn Nâng cấp, hệ thống sẽ gọi AI để tự động sửa Phong cách viết hiện hành "
        "dựa trên các đề xuất ở trên."
    )
    
    if st.button("✨ Nâng cấp Phong cách viết", type="primary"):
        with st.spinner("Đang hòa trộn YAML và đồng bộ..."):
            try:
                config_path = resolve_path("engine/config.example.yaml")
                config = load_yaml(config_path)
                updated_files = apply_style_upgrade(
                    mode=mode,
                    slug=st.session_state.selected_style_slug,
                    suggestions=suggestions,
                    config=config,
                )
                if updated_files:
                    st.success(f"Đã cập nhật thành công các file: {', '.join(updated_files)}")
                else:
                    st.info("Không có file YAML nào cần cập nhật.")
            except Exception as e:
                st.error(f"Lỗi khi nâng cấp Phong cách viết: {e}")

    st.divider()
    st.subheader("📧 Gửi kết quả về Email")
    st.caption(
        "Gửi bài viết hoàn thiện của bạn cùng các báo cáo phản hồi chi tiết đính kèm dạng text (.txt) vào hộp thư."
    )

    col_mail, col_btn = st.columns([3, 1])
    with col_mail:
        default_recipient = st.session_state.get("user_info", {}).get("email", "")
        recipient_email = st.text_input(
            "Nhập địa chỉ email người nhận:",
            value=default_recipient,
            placeholder="vidu@gmail.com",
            key="bw_email_recipient",
        )
    with col_btn:
        st.write("")
        st.write("")
        send_btn = st.button("📤 Gửi Email", key="bw_send_email_btn", use_container_width=True)

    if send_btn:
        if not recipient_email:
            st.warning("Vui lòng nhập địa chỉ email người nhận.")
        else:
            with st.spinner("Đang kết nối máy chủ và gửi email..."):
                try:
                    send_blog_email(
                        recipient=recipient_email,
                        mode=mode,
                        human_edited=st.session_state.bw_human_edited,
                        run_dir=st.session_state.bw_run_dir,
                    )
                    st.success(f"🎉 Đã gửi email thành công tới **{recipient_email}**!")
                except Exception as e:
                    st.error(f"Lỗi khi gửi email: {e}")

