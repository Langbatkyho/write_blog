import difflib
import textwrap
from typing import Any
import yaml

from engine.utils import load_yaml, resolve_path
from engine.parser import count_words, count_paragraphs, average_sentence_words

def build_learning_prompt(
    workflow: dict[str, Any],
    skills: dict[str, dict[str, Any]],
    author_input: str,
    step_outputs: dict[str, str],
    final_blog: str,
    production_blog: str,
    comparison_label: str = "final_blog.md",
    mode: str = "deep",
) -> str:
    learning_skill = load_yaml(resolve_path("skills/editorial_learning.yaml"))
    skills_yaml = yaml.safe_dump(skills, allow_unicode=True, sort_keys=False)
    workflow_yaml = yaml.safe_dump(workflow, allow_unicode=True, sort_keys=False)
    step_outputs_block = "\n\n".join(
        f"## {name}\n\n{content}" for name, content in step_outputs.items()
    )

    return textwrap.dedent(
        f"""
        Bạn đang chạy learning loop cho một workflow viết blog phản tư tự động.
        Writing Mode: {mode}

        Learning skill YAML:
        ```yaml
        {yaml.safe_dump(learning_skill, allow_unicode=True, sort_keys=False)}
        ```

        Workflow YAML:
        ```yaml
        {workflow_yaml}
        ```

        Skill YAML files:
        ```yaml
        {skills_yaml}
        ```

        Input gốc của tác giả:
        ```markdown
        {author_input}
        ```

        Output của các bước workflow:
        ```markdown
        {step_outputs_block}
        ```

        Bản nháp so sánh có AI hỗ trợ ({comparison_label}):
        ```markdown
        {final_blog}
        ```

        Bản người viết đã chỉnh sửa production_blog.md:
        ```markdown
        {production_blog}
        ```

        Instructions:
        - Tuân thủ chặt chẽ Learning skill YAML.
        - Mặc định viết toàn bộ báo cáo bằng tiếng Việt.
        - Chỉ giữ tiếng Anh cho tên hàm, thuộc tính, biến số, file name, stage id, YAML key, và thuật ngữ hệ thống đã có sẵn.
        - Tạo báo cáo markdown thực dụng để cải thiện workflow cho writing mode: {mode}.
        - Tập trung vào những gì người viết đã chỉnh và workflow cần học được điều gì.
        - Đưa insight theo từng stage của mode hiện tại.
        - Gợi ý chỉnh YAML bằng bullet ngắn, không viết lại toàn bộ file.
        - Không viết lại bài blog.
        - Không đưa hidden reasoning.
        """
    ).strip()

def build_tuning_prompt(report: str, mode: str = "deep") -> str:
    if mode == "moment":
        stages_list = "sensory_capture, inner_weather, cosmic_signal_reader, moment_writer, breath_editor, gentle_witness"
    else:
        stages_list = "story_architect, reflection_engine, writing_agent, reader_experience, editor_agent, coach_agent, future_self"

    return textwrap.dedent(
        f"""
        Chuyển editorial learning report cho mode '{mode}' thành các gợi ý tinh chỉnh workflow thật ngắn gọn.

        Editorial learning report:
        ```markdown
        {report}
        ```

        Output là một tài liệu markdown bằng tiếng Việt, gồm:
        - một section cho từng workflow stage trong mode '{mode}':
          {stages_list}
        - thay đổi YAML hoặc prompt-rule cụ thể cho stage đó
        - tác động kỳ vọng của từng thay đổi
        - độ tin cậy: high, medium, hoặc low

        Chỉ giữ tiếng Anh cho tên hàm, thuộc tính, biến số, file name, stage id, YAML key, và thuật ngữ hệ thống đã có sẵn.
        Không viết lại bài blog.
        Không đưa hidden reasoning.
        """
    ).strip()

def render_offline_diff(final_blog: str, production_blog: str, comparison_label: str = "final_blog.md") -> str:
    final_lines = final_blog.splitlines()
    production_lines = production_blog.splitlines()
    diff_lines = difflib.unified_diff(
        final_lines,
        production_lines,
        fromfile=comparison_label,
        tofile="production_blog.md",
        lineterm="",
    )
    diff = "\n".join(diff_lines)
    return diff if diff.strip() else "Không phát hiện khác biệt theo từng dòng."

def build_offline_learning_report(
    final_blog: str,
    production_blog: str,
    step_outputs: dict[str, str],
    comparison_label: str = "final_blog.md",
    mode: str = "deep",
) -> str:
    final_words = count_words(final_blog)
    production_words = count_words(production_blog)
    word_delta = production_words - final_words
    final_paragraphs = count_paragraphs(final_blog)
    production_paragraphs = count_paragraphs(production_blog)
    paragraph_delta = production_paragraphs - final_paragraphs
    final_sentence_avg = average_sentence_words(final_blog)
    production_sentence_avg = average_sentence_words(production_blog)
    similarity = difflib.SequenceMatcher(None, final_blog, production_blog).ratio()
    diff = render_offline_diff(final_blog, production_blog, comparison_label=comparison_label)

    if word_delta < 0:
        length_note = "Bản production ngắn hơn, cho thấy người viết có thể đã cắt phần giải thích thừa hoặc siết lại nhịp."
    elif word_delta > 0:
        length_note = "Bản production dài hơn, cho thấy người viết có thể đã thêm ngữ cảnh, chi tiết cảm xúc hoặc phần nối ý."
    else:
        length_note = "Bản production có cùng số từ, nên bài học chính có thể nằm ở cách diễn đạt, cấu trúc hoặc trọng tâm nhấn."

    if production_sentence_avg < final_sentence_avg:
        rhythm_note = "Độ dài câu trung bình giảm, cho thấy người viết có xu hướng thích nhịp ngắn hơn và khoảng dừng rõ hơn."
    elif production_sentence_avg > final_sentence_avg:
        rhythm_note = "Độ dài câu trung bình tăng, cho thấy người viết có thể muốn phần suy tưởng phát triển hơn hoặc dòng văn mượt hơn."
    else:
        rhythm_note = "Độ dài câu trung bình gần như không đổi."

    available_steps = ", ".join(step_outputs.keys()) or "Không tìm thấy step output"

    if mode == "moment":
        stage_insights = textwrap.dedent("""
            ### sensory_capture
            Kiểm tra liệu bản production có giữ quan sát cụ thể chân thật hay thêm chi tiết chưa có căn cứ.

            ### inner_weather
            Kiểm tra liệu bản production có đổi cách gọi tên cảm xúc hoặc thêm lý thuyết tâm lý/tâm linh quá mức.

            ### cosmic_signal_reader
            Kiểm tra tín hiệu trực giác nhỏ được giữ, được cắt gọn, hay bị mở rộng thành bài giảng.

            ### moment_writer
            Kiểm tra liệu bản production có rút ngắn câu hoặc bỏ phần hồi tưởng để giữ năng lượng hiện tại.

            ### breath_editor
            Kiểm tra liệu bản production có làm nhẹ câu nặng hơn nữa hay cho thấy bản edit đã bị quá trau chuốt.

            ### gentle_witness
            Kiểm tra liệu witness report có nhận ra đúng các đoạn gượng, quá sạch hoặc lên giọng dạy đời.
        """).strip()
    else:
        stage_insights = textwrap.dedent("""
            ### story_architect
            Kiểm tra liệu bản production có đổi mở bài, sắp xếp lại các phần hoặc di chuyển điểm chuyển cảm xúc.

            ### reflection_engine
            Kiểm tra liệu bản production có thêm sự chưa chắc, bỏ kết luận quá sớm hoặc đào sâu một căng thẳng ẩn.

            ### writing_agent
            Kiểm tra liệu bản production có rút ngắn đoạn, đổi đại từ, bỏ câu chung chung hoặc thêm chi tiết sống.

            ### reader_experience
            Kiểm tra liệu reader diary có bắt được nơi sự chú ý, niềm tin hoặc kết nối thay đổi.

            ### editor_agent
            Kiểm tra liệu bản production lặp lại, đi ngược hoặc cải thiện các chỉnh sửa của editor_agent.

            ### coach_agent
            Kiểm tra liệu bản production có trả lời một câu hỏi sâu hơn mà coaching report chưa hỏi.

            ### future_self
            Kiểm tra liệu bản production có đi theo hay bỏ qua future_reflection.md.
        """).strip()

    return textwrap.dedent(
        f"""
        # Báo Cáo Offline Editorial Learning ({mode.upper()} MODE)

        Báo cáo này được tạo mà không gọi OpenAI API. Nó dùng so sánh văn bản cục bộ để phân tích khác biệt.

        ## Tóm Tắt

        - Mode: {mode}
        - Similarity score: {similarity:.3f}
        - Số từ {comparison_label}: {final_words}
        - Số từ production_blog.md: {production_words}
        - Chênh lệch số từ: {word_delta:+d}
        - Chênh lệch số đoạn: {paragraph_delta:+d}
        - Số từ trung bình/câu, {comparison_label}: {final_sentence_avg:.2f}
        - Số từ trung bình/câu, production: {production_sentence_avg:.2f}

        {length_note}

        {rhythm_note}

        ## Ngữ Cảnh Workflow Có Sẵn

        Step outputs tìm thấy: {available_steps}

        ## Insight Offline Theo Từng Stage

        {stage_insights}

        ## Local Diff

        ```diff
        {diff}
        ```
        """
    ).strip()

def build_offline_tuning_suggestions(report: str, mode: str = "deep") -> str:
    if mode == "moment":
        suggestions_body = textwrap.dedent("""
            ## sensory_capture
            - Check: "Bản người viết sửa có giữ quan sát cụ thể mà không suy diễn ý nghĩa ẩn không?"
            - Tác động kỳ vọng: baseline giác quan sạch và đáng tin hơn.
            - Confidence: high

            ## inner_weather
            - Check: "Bản người viết sửa có làm cách gọi tên thời tiết bên trong giản dị hơn không?"
            - Tác động kỳ vọng: tránh giọng lâm sàng hoặc phân tích quá mức.
            - Confidence: medium

            ## cosmic_signal_reader
            - Check: "Tín hiệu trực giác có còn nhỏ và có căn cứ không?"
            - Tác động kỳ vọng: tránh biến cosmic signal thành lời khuyên dạy đời.
            - Confidence: high

            ## moment_writer
            - Check: "Bản người viết sửa có chỉnh nhịp câu để giữ hơi thở hiện tại không?"
            - Tác động kỳ vọng: nhịp bài ngắn tự nhiên hơn.
            - Confidence: high

            ## breath_editor
            - Check: "Editor có cắt gọn mà không thêm ý mới không?"
            - Tác động kỳ vọng: giữ moment trong giới hạn 300-600 từ.
            - Confidence: high

            ## gentle_witness
            - Check: "Witness report có nhận ra đúng giọng dạy đời, quá sạch hoặc quá gượng không?"
            - Tác động kỳ vọng: củng cố bước xác nhận nhẹ nhàng mà không tạo loop.
            - Confidence: medium
        """).strip()
    else:
        suggestions_body = textwrap.dedent("""
            ## story_architect
            - Thêm câu hỏi review: "Bản production có di chuyển điểm bắt đầu thật sự của câu chuyện không?"
            - Tác động kỳ vọng: chọn mở bài tốt hơn.
            - Confidence: medium

            ## reflection_engine
            - Thêm câu hỏi review: "Bản production có trì hoãn hoặc làm mềm một insight không?"
            - Tác động kỳ vọng: giảm việc tạo ý nghĩa quá sớm.
            - Confidence: medium

            ## writing_agent
            - So sánh độ dài đoạn và câu với bản production trước khi chấp nhận draft sau này.
            - Tác động kỳ vọng: nhịp gần hơn với giọng người viết đã chỉnh.
            - Confidence: high

            ## reader_experience
            - Giữ stage này là nhật ký đọc mù, không chẩn đoán hoặc khuyến nghị.
            - Tác động kỳ vọng: tín hiệu sạch hơn cho editor_agent.
            - Confidence: high

            ## editor_agent
            - So sánh edit_log.md với bản production và thêm các lựa chọn chỉnh lặp lại của người viết thành minimum-edit rules.
            - Tác động kỳ vọng: ít rewrite không cần thiết hơn và kết nối người đọc tốt hơn.
            - Confidence: medium

            ## coach_agent
            - Đọc edited_blog.md thay vì draft_blog.md để coaching tập trung vào điểm mù của người viết, không phải dọn câu chữ.
            - Tác động kỳ vọng: câu hỏi coaching sâu hơn.
            - Confidence: medium

            ## future_self
            - Giữ stage này chỉ phản tư; nó nên nêu quyết định cho người viết, không rewrite final_blog.md.
            - Tác động kỳ vọng: quyền sở hữu bản cuối của người viết rõ hơn.
            - Confidence: medium
        """).strip()

    return textwrap.dedent(
        f"""
        # Gợi Ý Tinh Chỉnh Workflow Offline ({mode.upper()} MODE)

        Các gợi ý này được tạo mà không cần OpenAI API cho mode '{mode}'.

        {suggestions_body}

        ## Báo Cáo Nguồn

        Xem `editorial_learning_report.md` để biết metrics và chi tiết diff.
        """
    ).strip()
