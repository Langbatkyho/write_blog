# Tích hợp Luồng Viết Blog (Blog Workflow) vào Streamlit UI

Mục tiêu: Xây dựng tab "🚀 Viết Blog" mới, hoàn toàn tách biệt với Voice Lab, sử dụng thiết kế đa bước (Wizard) được kiểm soát bởi `st.session_state` cùng với Stepper UI (thanh tiến trình). Quá trình gọi AI sẽ dùng `st.spinner` để chặn thao tác người dùng, tích hợp xử lý lỗi và tính năng bắt đầu lại. Client sử dụng để gọi workflow sẽ là Gemini theo yêu cầu.

## User Review Required

> [!IMPORTANT]
> **Cơ chế "Nâng cấp Style":** Để làm rõ cơ chế của `apply_style_upgrade`, hệ thống sẽ hoạt động theo quy trình 4 bước sau (chạy hoàn toàn ngầm qua API, user chỉ cần ấn 1 nút):
> 
> 1. **Gom Context:** UI Controller tự động quét và đọc toàn bộ nội dung của tất cả các file YAML trong thư mục của style hiện tại (ví dụ: `skills/deep/reflective/` chứa khoảng 7-8 file YAML, dung lượng rất nhẹ).
> 2. **Gọi LLM (Gemini):** Đóng gói toàn bộ các file YAML này cùng với bản `workflow_tuning_suggestions.md` mà AI vừa sinh ra, kèm theo một Prompt hệ thống: *"Hãy đối chiếu các đề xuất với các file YAML, tiến hành chỉnh sửa/thêm/xóa nội dung theo đúng đề xuất và trả về danh sách các file YAML ĐÃ BỊ SỬA dưới định dạng JSON"*.
> 3. **Phân tích kết quả (Parsing):** Controller nhận JSON từ Gemini, bóc tách ra các cặp `{"filename": "editor_agent.yaml", "content": "..."}`.
> 4. **Lưu & Đồng bộ:** Với mỗi file bị sửa, hệ thống gọi hàm `engine.style_manager.save_style_file(...)` để lưu đè an toàn. Lúc này, hàm `auto_git_sync` có sẵn trong `style_manager` sẽ tự động kích hoạt và commit+push những YAML vừa được update lên Github.

## Proposed Changes

---

### Quản lý Trạng thái (State Management)

#### [MODIFY] ui/state.py
- Bổ sung các biến mặc định vào `SESSION_DEFAULTS`:
  - `bw_step`: (int) Bước hiện tại của luồng (1 đến 4).
  - `bw_input_text`: (str) Nội dung bài viết thô.
  - `bw_article_length`: (str) Độ dài mong muốn (Ngắn, Vừa, Dài).
  - `bw_ai_result`: (str) Nội dung AI viết ra.
  - `bw_run_log`: (str) Lịch sử chạy agent.
  - `bw_human_edited`: (str) Nội dung do người dùng tự sửa.
  - `bw_tuning_suggestions`: (str) Đề xuất cải tiến style.
  - `bw_run_dir`: (str) Đường dẫn thư mục `web_runs` (Path string) của lượt chạy này để Learning Loop tham chiếu.
- Hàm `reset_blog_workflow_state()` để xóa dữ liệu rác khi đổi mode, hoặc khi bấm nút "🔄 Bắt đầu lại".

---

### Logic Xử lý Giao diện (Controllers)

#### [MODIFY] ui/controllers/workflow_controller.py
- **Gemini Client:** Import `call_gemini` từ `engine.gemini_client` để sử dụng mặc định.
- Thêm `run_real_workflow(...)`: 
  - Đọc thiết lập độ dài và mix vào `input_text` (ví dụ, ghi chú thêm vào mồi text).
  - Bọc trong khối `try/except`.
  - Gọi `engine.workflow_execution.run_workflow(..., persist=True, llm_client=call_gemini)`.
  - Do `persist=True` trả về `Path` thư mục, controller sẽ tự động đọc file `edited_blog.md` (hoặc `moment_edited.md` nếu mode moment) và `run_log.md` từ thư mục trả về.
  - Trả về dạng Dictionary hoặc Tuple chứa content và run directory path.
- Thêm `run_real_learning(...)`: 
  - **Quan trọng:** Trước khi gọi learning, lưu nội dung user vừa sửa vào file `production_blog.md` tại `run_dir` đã lưu.
  - Gọi `engine.workflow_learning.run_learning_loop(..., persist=True, llm_client=call_gemini)`.
  - Trả về text của file suggestions.
- Thêm `apply_style_upgrade(...)`: Triển khai logic đóng gói đa file YAML, gọi Gemini API sinh JSON và ghi đè như mô tả ở phần User Review.

---

### Giao diện Người dùng (Views)

#### [NEW] ui/views/blog_workflow.py
- Dùng `st.markdown` render **Flow Indicator** (Thanh tiến trình trực quan) dạng: `① Nhập bài → ② Kết quả → ③ Sửa bài → ④ Học hỏi` với trạng thái highlight tương ứng.
- Có nút "🔄 Bắt đầu lại" (reset `bw_step=1`) ở mọi bước (trừ Bước 1).
- Xây dựng hàm `render_blog_workflow(styles, mode)` dùng khối `if/elif` tùy theo `st.session_state.bw_step`:
  - **Bước 1 (Nhập bài):** Hiển thị `st.selectbox` chọn Style, radio button chọn độ dài bài viết. Dưới đó là `st.text_area` mồi sẵn `examples/blog_1.md`. Bấm "🚀 Chạy Workflow" → Hiện `st.spinner`, chạy trong `try/except`, lỗi thì `st.error` + hiện nút Retry. Xong thì chuyển `bw_step = 2`.
  - **Bước 2 (Kết quả):** Dùng `st.tabs` chia màn hình: Tab 1 là AI Result, Tab 2 là Run Log. Nút "Tiếp tục chỉnh sửa" → Chuyển `bw_step = 3`.
  - **Bước 3 (Sửa bài):** `st.text_area` chứa Blog Result để user sửa. Nút "🧠 AI Phân Tích (Learning Loop)" → `st.spinner` → Controller lưu bản sửa thành `production_blog.md` rồi gọi learning loop. Xong chuyển `bw_step = 4`.
  - **Bước 4 (Học hỏi):** `st.text_area` hiển thị Tuning Suggestions. Nút "✨ Nâng cấp Style" → Gọi hàm `apply_style_upgrade`.

#### [MODIFY] ui/app.py
- Import `render_blog_workflow`.
- Bổ sung tab "🚀 Viết Blog" vào danh sách `st.tabs` ở vị trí đầu tiên hoặc cạnh Live Workbench.

## Verification Plan

### Manual Verification
- Khởi động Streamlit.
- Chọn tab "🚀 Viết Blog".
- Bấm tuần tự 4 bước, đảm bảo thanh Stepper hiển thị chính xác tiến độ.
- Đảm bảo Controller đã đọc đúng file `edited_blog.md`/`moment_edited.md` thay vì crash do return type.
- Verify chức năng Nâng cấp style đã bóc tách JSON thành công và làm thay đổi nội dung các file YAML tương ứng.
