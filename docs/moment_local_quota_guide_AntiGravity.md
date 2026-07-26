# Hướng dẫn chạy Moment Workflow với cơ chế Local Model Quota (Antigravity Bridge)

Cơ chế **Local Model Quota** (`--client antigravity`) cho phép bạn chạy hệ thống Mindful Writing OS hoàn toàn bằng năng lực nội tại của AI Assistant (Gemini/Claude) trong một phiên làm việc (conversation), thay vì phải tốn phí gọi API từ bên ngoài.

Dưới đây là các bước chi tiết để bạn khởi tạo và vận hành trơn tru quy trình này trong một **Conversation hoàn toàn mới**.

---

## Bước 1: Chuẩn bị Input File
Tạo một file `.md` chứa dữ liệu đầu vào (ví dụ: `examples/moment_2.md`) với cấu trúc bắt buộc:

```markdown
title: [Tiêu đề tùy chọn]

raw_notes:
[Nhập các gạch đầu dòng, cảm xúc thô, sự kiện, suy nghĩ vụn vặt ở thời điểm hiện tại. Khuyến khích giữ nguyên các emoji hoặc biểu cảm tự nhiên.]

target_reader:
- [Tập độc giả mục tiêu]

desired_length:
300-600 từ
```

---

## Bước 2: Khởi động Prompt cho AI Assistant trong Conversation Mới
Khi mở một Conversation mới, bạn cần truyền một Prompt khởi động để cấp quyền và hướng dẫn AI cách thức "giao tiếp" với hệ thống bridge.

**Copy và dán Prompt sau cho AI Assistant:**

> "Hãy chạy workflow viết blog chế độ moment cho tôi bằng lệnh sau ở background:
> `python engine/run_workflow.py --mode moment --input examples/moment_2.md --client antigravity`
>
> **Nhiệm vụ của bạn (Rất quan trọng):**
> 1. Sử dụng công cụ `/goal` hoặc liên tục gọi công cụ để theo dõi lệnh chạy nền.
> 2. Quá trình chạy sẽ tuần tự đi qua 6 agents: *sensory_capture, inner_weather, cosmic_signal_reader, moment_writer, breath_editor, gentle_witness*.
> 3. Lệnh chạy nền sẽ thỉnh thoảng dừng lại, tạo ra file `prompt_<tên_agent>_<timestamp>.txt` tại thư mục `runs/temp_llm/` và hiển thị trạng thái `WAITING`.
> 4. Khi thấy trạng thái này, bạn PHẢI:
>    - Dùng lệnh `list_dir` để xem file prompt mới nhất.
>    - Dùng lệnh `view_file` để đọc kỹ yêu cầu (Skill YAML, Input, Handoff context) trong file prompt đó.
>    - Đóng vai agent tương ứng, tự suy nghĩ (thought) và gọi công cụ `write_to_file` để ghi kết quả đầu ra vào file `response_<tên_agent>_<timestamp>.txt` (đúng format gồm 2 phần `## Artifact` và `## Handoff`).
> 5. Lặp lại quá trình này cho đến khi toàn bộ 6 agents hoàn thành và tiến trình báo thành công. Lưu ý: KHÔNG xin phép tôi giữa chừng, hãy chủ động làm đến khi ra thành phẩm cuối cùng."

---

## Bước 3: Hỗ trợ AI xử lý (Nếu cần)
Do hệ thống Antigravity Bridge giao tiếp thông qua việc "thả" file vào thư mục `runs/temp_llm`, đôi khi AI có thể dừng lại hoặc quên mất việc kiểm tra thư mục. Nếu tiến trình bị treo:
- Nhắc nhẹ AI: *"Hãy kiểm tra xem có file prompt mới nào trong `runs/temp_llm` không, nếu có hãy tạo file response tương ứng."*

---

## Bước 4: Chạy Learning Loop (Tùy chọn sau khi viết xong)
Sau khi AI hoàn thành bản nháp (file `final_blog.md` trong thư mục `runs/<tên_thư_mục_run>`), nếu bạn muốn tự tay chỉnh sửa bản nháp đó và để AI "học" phong cách của bạn:
1. Đổi tên `final_blog.md` (bản gốc của AI) thành `moment_edited.md`.
2. Tạo file `production_blog.md` chứa bản văn mà bạn đã tự tay chỉnh sửa cho ưng ý.
3. Yêu cầu AI chạy lệnh học hỏi:
   `python engine/run_workflow.py --learn-from-run runs/<tên_thư_mục_run> --client antigravity`
4. AI sẽ lại tiếp tục đọc prompt tại `runs/temp_llm/` (đối với `editorial_learning` và `workflow_tuning`) để trích xuất bài học và đề xuất YAML.
