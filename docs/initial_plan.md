# Kế hoạch ban đầu

Kế hoạch này bắt nguồn từ quan sát rằng ở giai đoạn cuối (`future_self`), workflow phải đọc lại quá nhiều ngữ cảnh bị lặp. Thiết kế cũ truyền gần như toàn bộ output của các bước trước đó vào mọi prompt ở các bước sau. Điều này khiến cho workflow ngày càng trở nên đắt đỏ về lượng token tiêu thụ khi đi về các bước cuối.

Giải pháp tối ưu hóa được đề xuất là yêu cầu mỗi stage sinh ra hai loại output:

- **Artifact**: Toàn bộ nội dung đầy đủ để con người có thể theo dõi, review, debug và phục vụ cho quá trình learning sau này.
- **Handoff**: Một bản tóm tắt có cấu trúc gọn gàng (khoảng 120-250 từ) dành riêng cho các agent ở bước tiếp theo.

Các yêu cầu triển khai chính gồm:

1. **Cập nhật kỹ năng (skill YAML schemas)**: Mỗi stage phải trả về bắt buộc hai phần `## Artifact` và `## Handoff`.
2. **Cập nhật cấu hình luồng (flow/write_blog.yaml)**: Mỗi bước khai báo rõ:
   - `output`
   - `handoff_output`
   - `context_policy`
3. **Nâng cấp Engine**:
   - Phân tích và tách biệt nội dung `## Artifact` và `## Handoff`.
   - Lưu artifact và handoff vào các file riêng biệt.
   - Ghi nhận đầy đủ thông tin vào `step_outputs.json`.
   - Chỉ truyền các handoff/artifact được chọn (theo `context_policy`) sang các bước tiếp theo.
   - Duy trì learning loop hoạt động dựa trên các artifact đầy đủ.
   - Bổ sung ước tính số lượng token artifact/handoff.
4. **Kiểm thử và xác thực**: Thêm unit test cho parser và kiểm tra cơ chế context policy thông qua dry-run và offline learning.
