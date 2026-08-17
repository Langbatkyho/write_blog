# Implementation Plan - DeepSeek API Integration (`deepseek-v4-pro`)

Tích hợp chính thức provider `deepseek` (model `deepseek-v4-pro`) vào hệ thống `mindful_writing_os` để phục vụ chạy workflow viết blog đa chế độ (Deep Mode & Moment Mode).

## 1. Điểm hợp lý, hiệu quả (Context Caching & Thinking Mode)
- **Context Caching:** Bật mặc định trên đĩa. Giữ nguyên cấu trúc Prompt/Context tĩnh ở đầu để tối ưu hoá Cache Hit Rate.
- **Thinking Mode:** Rất phù hợp với **Deep Mode** và **Reflective Style**. Trả về tiến trình suy luận ở trường `reasoning_content`.

## 2. Các điểm cần điều chỉnh (Theo phân tích của Claude Opus)
- **Endpoint:** Dùng `https://api.deepseek.com` (qua OpenAI SDK).
- **Token Budget:** Tăng `max_output_tokens` lên `8192` vì reasoning tokens chia sẻ chung budget với output tokens, tránh bài blog bị cắt cụt.
- **Lưu trữ Reasoning:** Log riêng trường `reasoning_content` ra file `_reasoning.md` trong thư mục run để theo dõi.
- **Graceful Fallback:** Xử lý mềm dẻo nếu API trả về thiếu `reasoning_content` hoặc bị lỗi.
- **Timeout:** Thiết lập timeout cao (`120s` - `300s`) trong `config.yaml` để chờ Thinking Mode xử lý.

## 3. Các thay đổi dự kiến (Proposed Changes)

### Core Engine

#### [NEW] `engine/deepseek_client.py`
- Tạo module client sử dụng OpenAI SDK với `base_url="https://api.deepseek.com"`.
- Nạp `DEEPSEEK_API_KEY` từ `.env`.
- Tích hợp **Thinking Mode**:
  - Truyền `reasoning_effort`.
  - Tách `reasoning_content` ra và lưu vào thư mục đầu ra của lượt chạy (ví dụ `_reasoning.md`).
  - Gắn lại `reasoning_content` vào tin nhắn `assistant` nếu có kịch bản đa lượt.
  - Fallback an toàn nếu không nhận được suy luận.

#### [MODIFY] `engine/client_router.py`
- Đăng ký `"deepseek"` vào registry và capability map.
- Cập nhật `describe_stage`.

#### [MODIFY] `engine/run_workflow.py`
- Thêm `"deepseek"` vào `--client` choices.

#### [MODIFY] `engine/config.example.yaml` & `engine/config.local.yaml`
- Thêm block cấu hình mặc định:
  ```yaml
  deepseek:
    endpoint: "https://api.deepseek.com"
    model: "deepseek-v4-pro"
    max_output_tokens: 8192
    timeout: 300
    api_key_env: "DEEPSEEK_API_KEY"
    thinking:
      enabled: true
      reasoning_effort: "high"
  ```

### Test Suite

#### [MODIFY] `tests/test_workflow_runtime_contract.py`
- Cập nhật test case router và contract.
