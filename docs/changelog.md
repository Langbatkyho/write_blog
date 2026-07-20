# Lịch sử Thay đổi (Changelog)

## Phiên bản: Đa Phong Cách Multi-Style Architecture (2026-07-20)
- **Tái Cấu Trúc Thư Mục Skill (`skills/`)**:
  - Tạo `skills/reflective/` lưu 7 agent YAML gốc (Style 1 mặc định).
  - Tạo `skills/provocative/` lưu 7 agent YAML với phong cách gai góc, khiêu khích (Style 2) cùng `STYLE_BRIEF.md`.
  - Giữ `skills/editorial_learning.yaml` ở root thư mục `skills/` do logic học tập độc lập với phong cách viết.
- **Dynamic Skill Path Resolution (`engine/workflow.py`)**:
  - Tự động nạp file skill theo phong cách: `Path(step["skill"]).parent / style / Path(step["skill"]).name`.
  - Ghi thông tin `"style"` vào `metadata.json` và tên thư mục chạy dạng `{timestamp}_{style}_{slug}`.
- **CLI & Validation (`engine/run_workflow.py`)**:
  - Thêm cờ `--style` với cơ chế fail-fast kiểm tra sự tồn tại của thư mục style.
  - Hỗ trợ trích xuất tự động `style` từ `metadata.json` khi chạy `--learn-from-run`.
- **Kiểm Thử Multi-Style (`tests/test_workflow_contract.py`)**:
  - Parametrize kiểm thử hợp đồng dữ liệu cho toàn bộ các phong cách (`reflective`, `provocative`).

## Phiên bản: Prompt Caching & Token Optimization (2026-07-15)
- **Tối ưu Hóa Token đầu vào (`flow/write_blog.yaml`)**:
  - Thêm cờ `needs_author_input: false` cho stage `reader_experience`. Điều này cắt bỏ khối lượng lớn bản nháp thô khỏi "độc giả mù", vừa tiết kiệm token, vừa đảm bảo tính chân thực (blind reading).
- **Cấu trúc Prompt Caching (`engine/workflow.py`)**:
  - Chia tách `build_step_prompt` thành Static Prefix (Phần tĩnh) và Dynamic Suffix (Phần động).
  - Tối ưu vị trí của `Instruction` và `Author Input` lên đầu để tận dụng Prefix Hashing trên OpenAI/Anthropic API, có khả năng tiết kiệm lên đến 90% chi phí cho các phần lặp lại.
  - Tối ưu vị trí của `Skill YAML` xuống phần kết thúc prompt, tận dụng triệt để "Recency Bias" nhằm nâng cao độ tuân thủ của LLM.

## Phiên bản: Hỗ trợ Client Routing theo Stage (2026-07-15)
- **Client Router (`engine/client_router.py`)**: Thêm module định tuyến, cho phép gán LLM Client (openai, antigravity) riêng biệt cho từng Stage.
- **Mở rộng CLI (`run_workflow.py`)**: Bổ sung tham số `--client-map` để override client cho các Stage cụ thể (VD: `--client-map "story_architect=antigravity"`), với `--client` đóng vai trò fallback.
- **Metadata Logging**: Cập nhật file `metadata.json` thêm trường `client_routing` để theo dõi việc sử dụng Router.
- **Kiểm thử**: Viết thêm `tests/test_client_router.py` để đảm bảo độ tin cậy của bộ định tuyến mới.

## Phiên bản: Tích hợp Antigravity & Hoàn thiện Refactoring (2026-07-14)
- **Dependency Injection (DI)**: Bổ sung khả năng DI `LlmClient` cho hàm `run_workflow.py` và `engine/workflow.py`, giúp cô lập toàn toàn luồng xử lý LLM.
- **Antigravity Bridge**: Thêm `engine/antigravity_bridge.py` để giao tiếp với model Antigravity cục bộ thông qua cơ chế đọc/ghi file tạm thời (`temp_llm`). Xóa bỏ logic fallback hỗn tạp cũ từ `openai_client.py`.
- **Bảo mật và Tính ổn định**: 
  - Khởi tạo timeout 300 giây cho file-bridge để chống treo hệ thống.
  - Bổ sung `provider` string (`openai` hoặc `antigravity`) vào metadata để tăng tính minh bạch.
  - Chuyển TypeAlias `LlmClient` theo đúng chuẩn PEP 8.
- **Kiểm thử**: Viết thêm `tests/test_antigravity_bridge.py` với Mock Object giả lập đầy đủ luồng file I/O và Timeout.

## Phiên bản: Tái thiết kế Editorial Workflow (2026-07-14)
- **Phân định ranh giới tác vụ**: Tổ chức lại hệ thống Agent theo triết lý "Mỗi agent bảo vệ một chân lý và không trả lời thay câu hỏi của agent khác".
- **Agent mới (`editor_agent`)**: Đóng vai trò là Biên tập viên kết nối, đứng ngay sau `reader_experience`.
- **Cập nhật Skill YAML**: 
  - `writing_agent` trở thành Ghost Writer tạo bản nháp trung thành.
  - `reader_experience` trở thành Sổ tay độc giả (không phán xét hay đề xuất sửa lỗi).
  - `coach_agent` phân tích sâu các điểm mù sau khi bản nháp đã được edit.
  - `future_self` chỉ đưa ra quan sát tương lai, trả quyền quyết định bài viết cuối (`final_blog.md`) lại cho người viết.
- **Hỗ trợ Secondary Artifact**: Bổ sung cơ chế để sinh ra các file nhật ký phụ (như `edit_log.md` song song với `edited_blog.md`).

## Phiên bản: Engine Modularization (2026-07-10)
- **Tách Monolith**: Đập bỏ file script 892 dòng duy nhất thành các module con `utils.py`, `parser.py`, `openai_client.py`, `learning.py`, `workflow.py`.
- **Cơ chế Retry (Exponential Backoff)**: Thêm retry cho OpenAI Client khi gặp mã lỗi 429, 500, 503.
- **Bảo mật API Key**: Hiển thị UserWarning nếu nhúng cứng API Key thay vì dùng biến môi trường.
- **Chuẩn hóa YAML**: Sửa lại các key cấu trúc trong `future_self.yaml` cho đồng bộ với dự án (`sections`).

## Phiên bản: Handoff Layer (2026-07-10)
- **Artifact vs Handoff**: Thiết lập yêu cầu tách biệt hai luồng đầu ra cho mọi agent.
  - `Artifact`: Đầy đủ, lưu để audit và learning.
  - `Handoff`: Dạng nén gọn (120-250 từ), dùng làm input cho các bước tiếp theo.
- **Context Policy**: Chuyển mọi quyết định truyền Context vào file `write_blog.yaml`, thay vì code logic trong Python.
- **Cơ chế Fallback**: Đề phòng trường hợp AI sinh thiếu cấu trúc Handoff, hệ thống sẽ fallback an toàn thay vì crash.
- Tự động sinh `handoff_log.md` và theo dõi metrics qua `step_outputs.json` và `metadata.json`.
