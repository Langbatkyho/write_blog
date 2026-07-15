# Nhật ký Triển khai: Client Routing (2026-07-15)

## Bối cảnh (Context)
Dự án có nhu cầu sử dụng các mô hình ngôn ngữ lớn (LLM) khác nhau cho từng giai đoạn (stage) của workflow, nhằm tận dụng thế mạnh của từng model. Ví dụ: dùng model thiên về reasoning cho việc lên cấu trúc (`story_architect`), và model thiên về cảm xúc/ngữ cảnh (emotion/nuance) cho việc viết bản nháp (`writing_agent`). 

Trước thay đổi này, tham số `--client` ở mức CLI chỉ cho phép đặt **một client duy nhất** cho toàn bộ workflow.

## Thiết kế (Design)
Thay vì hardcode nhiều loại client trong `workflow.py`, hệ thống được áp dụng mẫu thiết kế (design pattern) **Router**.
- **`engine/client_router.py`**: Quản lý một "registry" các hàm khởi tạo Lazy (Lazy loading) cho từng client (`openai`, `antigravity`).
- **`build_client_map`**: Xử lý logic chuyển đổi chuỗi cấu hình trên CLI (VD: `stage1=client1,stage2=client2`) thành một Python dictionary.
- **`create_routing_client`**: Trả về một `Callable` đóng gói việc tra cứu dictionary theo `stage_id`. Bất cứ stage nào không được liệt kê cụ thể sẽ tự động dùng fallback client từ tham số `--client`.

## Các thay đổi chính (Implementation Details)

### 1. `engine/client_router.py` (Mới)
Tạo mới file chứa lõi định tuyến:
- Hỗ trợ Lazy import để tối ưu hiệu năng (chỉ import module client thực sự được dùng).
- Có cơ chế caching `_cache: dict[str, LlmClient]` để không phải khởi tạo lại cùng một client nhiều lần.

### 2. `engine/run_workflow.py`
Sửa CLI để nhận thêm tham số `--client-map`:
```python
parser.add_argument(
    "--client-map",
    help=(
        "Per-stage LLM client mapping. Format: 'stage1=client,stage2=client'. "
        "Valid clients: openai, antigravity. "
        "Stages not listed use --client as fallback."
    ),
)
```
Gắn kết `client_map` với router trước khi truyền vào hàm `run_workflow`.

### 3. Cập nhật YAML Configurations
- Chỉnh sửa `engine/config.example.yaml` để thêm hướng dẫn chi tiết về cách chia map cho từng client.
- `engine/config.local.yaml` được sửa để cấu hình các model cụ thể theo stage.

### 4. Logging & Verification
- `engine/workflow.py`: Sửa `metadata.json` để ghi nhận thuộc tính `client_routing: True`, báo hiệu cho người phân tích (hoặc learning loop) rằng các stage đã được chia luồng client.
- Bổ sung file test `tests/test_client_router.py` chuyên dụng test parse logic và fallback behavior.

## Kết quả (Result)
- Hỗ trợ gán LLM đa dạng cho từng Stage thành công mà **không cần sửa đổi** bất kỳ dòng code nào xử lý data flow của LLM (thỏa mãn Dependency Injection thuần khiết).
- Đảm bảo tương thích ngược: Lệnh `--client openai` cũ chạy mà không có vấn đề gì xảy ra.
