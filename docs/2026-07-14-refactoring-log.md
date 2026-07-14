# Refactoring Log — 2026-07-14 Workflow Redesign Adjustments

**Date:** 2026-07-14  
**Author:** Gemini 3.5 Flash (Principal Solutions Architect)  
**Parent Review:** Claude Opus 4.6 Báo cáo Code Review  

## Changes Made

### 1. Vector 1: Dọn dẹp key `sections` trùng lặp trong skill YAML
- **Files modified:**
  - [skills/reflection_engine.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/reflection_engine.yaml)
  - [skills/story_architect.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/story_architect.yaml)
- **Detail:** Loại bỏ khối `output.sections` trùng lặp ở cuối tệp. Dữ liệu cấu trúc đầu ra của Artifact hiện tại chỉ được định nghĩa một lần duy nhất trong `output.artifact.sections`.

### 2. Vector 2: Thống nhất Heading Level của `editor_agent` data contract
- **Files modified:**
  - [skills/editor_agent.yaml](file:///D:/Nghiên cứu AI/write_blog/skills/editor_agent.yaml)
  - [tests/test_workflow_contract.py](file:///D:/Nghiên cứu AI/write_blog/tests/test_workflow_contract.py)
  - [engine/workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/workflow.py)
- **Detail:** Thay đổi các trường yêu cầu phân tách bài viết từ `### Edited Blog` / `### Edit Log` (H3) thành `## Edited Blog` / `## Edit Log` (H2). Cập nhật cả test contract kiểm thử và cấu trúc phản hồi dry-run trong `workflow.py` để đảm bảo thống nhất chuẩn dữ liệu.

### 3. Vector 3: Hoist API Key Extraction khỏi vòng lặp Retry
- **File modified:**
  - [engine/openai_client.py](file:///D:/Nghiên cứu AI/write_blog/engine/openai_client.py)
- **Detail:** Đưa hàm `get_api_key(config)` ra khỏi vòng lặp `for attempt in range(max_retries)` trong `call_openai()`. API key hiện tại chỉ được truy xuất và kiểm tra một lần trước khi bắt đầu gửi request, tránh lặp lại cảnh báo bảo mật (`UserWarning`) thừa thãi khi có lỗi mạng/retry.

### 4. Vector 4: Cảnh báo khi chia tách Artifact phụ thất bại
- **File modified:**
  - [engine/workflow.py](file:///D:/Nghiên cứu AI/write_blog/engine/workflow.py)
- **Detail:** Thêm cảnh báo bằng `warnings.warn` khi hàm `derive_artifact_file_contents` không tìm thấy tiêu đề tương thích và phải sử dụng cơ chế fallback (lưu toàn bộ artifact vào file chính).

### 5. Vector 5: Bổ sung Unit Test kiểm tra cơ chế Fallback
- **File modified:**
  - [tests/test_handoff_parser.py](file:///D:/Nghiên cứu AI/write_blog/tests/test_handoff_parser.py)
- **Detail:** Thêm hàm test `test_secondary_fallback_when_heading_missing` để kiểm thử hành vi an toàn khi LLM trả dữ liệu không đúng cấu trúc Markdown phân chia, xác nhận việc phát ra cảnh báo đúng như thiết kế.

## Verification Results

- **Unit Tests:** `Ran 10 tests in 0.035s. Status: OK`. Tất cả các bài kiểm tra bao gồm cả test case mới về fallback và test check contract đều thành công 100%.
- **Dry-run Workflow:** Chạy thành công lệnh `python engine/run_workflow.py --input examples/blog_input_template.md --dry-run` mà không gặp bất kỳ lỗi hay cảnh báo nào. Bản ghi chạy được lưu đầy đủ tại thư mục `runs/`.
