# Hướng dẫn chạy Moment Workflow với cơ chế Local Model Quota & Multi-Style (Antigravity Bridge)

Cơ chế **Local Model Quota** (`--client antigravity`) cho phép bạn chạy hệ thống Mindful Writing OS hoàn toàn bằng năng lực nội tại của AI Assistant (Gemini/Claude) trong một phiên làm việc (conversation), thay vì tốn phí gọi API từ bên ngoài.

Trong kiến trúc mới (**Voice Lab V1 & Multi-Style**), hệ thống hỗ trợ định tuyến động các phong cách đã được tùy biến (ví dụ: `va-natural`, `minh-hom-hinh`, `reflective`, `provocative`) với cơ chế kiểm duyệt hợp đồng Fail-Fast chặt chẽ.

Dưới đây là các bước chi tiết để bạn khởi tạo và vận hành trơn tru quy trình này trong một **Conversation hoàn toàn mới**.

---

## Bước 1: Chuẩn bị Input File & Chọn Phong Cách (Style)
1. Tạo một file `.md` chứa dữ liệu đầu vào (ví dụ: `examples/moment_1.md`) với cấu trúc bắt buộc:

```markdown
title: [Tiêu đề tùy chọn]

raw_notes:
[Nhập các gạch đầu dòng, cảm xúc thô, sự kiện, suy nghĩ vụn vặt ở thời điểm hiện tại. Khuyến khích giữ nguyên các emoji hoặc biểu cảm tự nhiên.]

target_reader:
- [Tập độc giả mục tiêu]

desired_length:
300-600 từ
```

2. **Xác định Phong cách (Style):** Kiểm tra các phong cách đã được tạo từ Trình quản lý giọng văn **Voice Lab V1** trong thư mục `skills/moment/` (ví dụ: `va-natural`, `minh-hom-hinh`...).

---

## Bước 2: Khởi động Prompt cho AI Assistant trong Conversation Mới
Khi mở một Conversation mới, bạn cần truyền một Prompt khởi động để cấp quyền và hướng dẫn AI cách thức "giao tiếp" với hệ thống bridge.

**Copy và dán Prompt sau cho AI Assistant (thay đổi `--style` nếu muốn dùng giọng văn khác):**

> "Hãy chạy workflow viết blog chế độ moment với phong cách **Van Anh Natural** cho tôi bằng lệnh sau ở background:
> `python engine/run_workflow.py --mode moment --style va-natural --input examples/moment_1.md --client antigravity`
>
> **Nhiệm vụ của bạn (Rất quan trọng):**
> 1. Sử dụng công cụ `/goal` hoặc liên tục gọi công cụ để theo dõi lệnh chạy nền.
> 2. Quá trình chạy sẽ tự động kiểm duyệt hợp đồng Fail-Fast và tuần tự đi qua 6 agents theo phong cách `va-natural`: *sensory_capture, inner_weather, cosmic_signal_reader, moment_writer, breath_editor, gentle_witness*.
> 3. Lệnh chạy nền sẽ thỉnh thoảng dừng lại, tạo ra file `prompt_<tên_agent>_<timestamp>.txt` tại thư mục `runs/temp_llm/` và hiển thị trạng thái `WAITING`.
> 4. Khi thấy trạng thái này, bạn PHẢI:
>    - Dùng lệnh `list_dir` để xem file prompt mới nhất trong `runs/temp_llm/`.
>    - Dùng lệnh `view_file` để đọc kỹ yêu cầu (Skill YAML của style `va-natural`, Input, Handoff context) trong file prompt đó.
>    - Đóng vai agent tương ứng, tự suy nghĩ (thought) và gọi công cụ `write_to_file` để ghi kết quả đầu ra vào file `response_<tên_agent>_<timestamp>.txt` (đúng format gồm 2 phần `## Artifact` và `## Handoff`, chuẩn mã hóa UTF-8 tiếng Việt).
> 5. Lặp lại quá trình này cho đến khi toàn bộ 6 agents hoàn thành và tiến trình báo thành công. Lưu ý: KHÔNG xin phép tôi giữa chừng, hãy chủ động làm đến khi ra thành phẩm cuối cùng."

---

## Bước 3: Hỗ trợ AI xử lý & Cơ chế An toàn (Fail-Fast Bridge)
Do hệ thống Antigravity Bridge giao tiếp thông qua việc "thả" file vào thư mục `runs/temp_llm/`:
- **Đảm bảo mã hóa UTF-8:** Hệ thống bridge V6.0+ đã tích hợp xử lý UTF-8 tự động cho môi trường Windows, ngăn chặn hoàn toàn lỗi phông chữ khi AI đọc/ghi tiếng Việt.
- **Nếu tiến trình bị treo:** Nhắc nhẹ AI: *"Hãy kiểm tra xem có file prompt mới nào trong `runs/temp_llm` không, nếu có hãy tạo file response tương ứng."*
- **Quy trình Kiểm duyệt Hợp đồng (Contract Validation):** Trước khi chạy, engine sẽ tự động xác minh thư mục `skills/moment/<style>/` đầy đủ 6 file skill hợp lệ (theo bảng tra cứu `AGENT_FILENAME_MAP`). Nếu thiếu file bất kỳ, hệ thống sẽ Fail-Fast báo lỗi ngay lập tức mà không chạy ngầm sai lệch.

---

## Bước 4: Chạy Learning Loop (Tùy chọn sau khi viết xong)
Sau khi AI hoàn thành bản nháp (file `final_blog.md` trong thư mục `runs/<tên_thư_mục_run>`), nếu bạn muốn tự tay chỉnh sửa bản nháp đó và để AI "học" phong cách của bạn cho style `va-natural`:
1. Đổi tên `final_blog.md` (bản gốc của AI) thành `moment_edited.md`.
2. Tạo file `production_blog.md` chứa bản văn mà bạn đã tự tay chỉnh sửa cho ưng ý.
3. Yêu cầu AI chạy lệnh học hỏi:
   `python engine/run_workflow.py --learn-from-run runs/<tên_thư_mục_run> --client antigravity`
4. AI sẽ tiếp tục đọc prompt tại `runs/temp_llm/` (đối với `editorial_learning` và `workflow_tuning`) để trích xuất bài học và tự động đề xuất cập nhật YAML vào `skills/moment/va-natural/`.
