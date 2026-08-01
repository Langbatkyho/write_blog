Dưới đây là các gợi ý tinh chỉnh workflow cho chế độ **moment**, được chuyển đổi thành các hành động kỹ thuật ngắn gọn dựa trên bằng chứng biên tập:

---

### 1. sensory_capture
*   **Thay đổi YAML / Prompt-rule:**
    ```yaml
    output_format: "raw_bullet_points"
    prevent_sentence_chaining: true
    ```
*   **Tác động kỳ vọng:** Giữ nguyên các mảnh từ vựng thô và chi tiết giác quan độc lập, ngăn AI tự ý xâu chuỗi chúng thành một câu chuyện tuyến tính quá sớm.
*   **Độ tin cậy:** High

### 2. inner_weather
*   **Thay đổi YAML / Prompt-rule:**
    ```yaml
    focus_areas: ["emotional_shift"]
    exclude_details: ["anatomical_movements", "physical_mechanics"]
    ```
*   **Tác động kỳ vọng:** Loại bỏ mô tả chi tiết về cơ thể học (như gót chân, cổ gáy) để tránh bẫy "tả thực" cơ học ở các bước viết sau, chỉ tập trung vào trạng thái cảm xúc.
*   **Độ tin cậy:** Medium

### 3. cosmic_signal_reader
*   **Thay đổi YAML / Prompt-rule:**
    ```yaml
    signal_extraction: "minimalist_core_theme"
    avoid_behavioral_psychology_interpretation: true
    ```
*   **Tác động kỳ vọng:** Giữ thông điệp cốt lõi ở mức tối giản và gợi mở, không sa đà vào giải thích hoặc phân tích tâm lý học hành vi.
*   **Độ tin cậy:** High

### 4. moment_writer
*   **Thay đổi YAML / Prompt-rule:**
    ```yaml
    style_rules:
      prefer_social_media_formatting_with_frequent_line_breaks: true
      max_sentences_per_paragraph: 2
      frequent_single_phrase_lines: true
      encourage_parallel_structures_for_poetic_rhythm: true
      allow_soft_community_mentions: "HappiLab"
    ```
*   **Tác động kỳ vọng:** Phá vỡ cấu trúc bài luận truyền thống; tạo ra văn bản có nhịp điệu thơ ca, nhiều khoảng trắng, sử dụng phép điệp cấu trúc phủ định và tích hợp nhẹ nhàng tên cộng đồng ở cuối.
*   **Độ tin cậy:** High

### 5. breath_editor
*   **Thay đổi YAML / Prompt-rule:**
    ```yaml
    tasks:
      - "break_down_complex_sentences_into_short_breaths"
      - "ensure_the_text_looks_airy_with_plenty_of_white_space"
      - "remove_didactic_or_analytical_phrases"
    ```
*   **Tác động kỳ vọng:** Biên tập quyết liệt hơn bằng cách bẻ gãy câu phức thành chuỗi câu đơn cực ngắn, tăng khoảng trống thị giác và xóa bỏ mọi giọng điệu mang tính "dạy bảo".
*   **Độ tin cậy:** High

### 6. gentle_witness
*   **Thay đổi YAML / Prompt-rule:**
    ```yaml
    evaluation_criteria:
      - "rhythm_and_line_break_flow"
      - "emotional_transition_smoothness"
    ```
*   **Tác động kỳ vọng:** Đánh giá nghiêm ngặt nhịp điệu ngắt dòng và độ mượt mà của bước đệm cảm xúc (ví dụ: đưa câu dịu dàng lên trước câu tự trào) thay vì chỉ kiểm tra lỗi chính tả hoặc sắc thái từ vựng đơn thuần.
*   **Độ tin cậy:** Medium