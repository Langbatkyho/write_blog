# Refactor Checklist

## Discovery

- Đọc kiến trúc hiện tại, workflow analysis và kế hoạch liên quan.
- Tìm mọi caller, consumer, test, config và artifact format bị ảnh hưởng.
- Ghi lại backward-compatibility và dữ liệu người dùng cần bảo vệ.

## Module review

- Module có bao nhiêu trách nhiệm/lý do thay đổi?
- Entrypoint có chứa prompt, parser, formatter hoặc persistence không?
- Logic có lặp lại giữa mode/style/provider không?
- Abstraction mới có consumer thật không?
- Có hai nguồn chân lý cho cùng schema, filename hoặc dimension không?

Số dòng lớn là tín hiệu kiểm tra, không tự động chứng minh God Object.

## Change design

- Xác định contract trước implementation.
- Ưu tiên hàm thuần cho compile/transform/validation.
- Inject I/O và provider tại biên.
- Giữ compatibility trong migration adapter có thời hạn.
- Dùng fail-closed thay silent fallback.

## Verification

- Chạy test nhỏ nhất liên quan trước, regression sau.
- Dùng temp output và fake API.
- Tìm import/reference để phát hiện code chết.
- Xác minh `runs/` không đổi ngoài ý muốn.
- Với UI: chạy AppTest và kiểm tra trực quan khi cần.
- Với publish: kiểm tra staging, validation, rollback và không ghi đè.

## Completion

- Xóa import, biến, nhánh và file tạm do thay đổi hiện tại làm dư thừa.
- Không xóa dữ liệu hoặc thay đổi ngoài phạm vi.
- Cập nhật tài liệu kiến trúc/changelog nếu contract hoặc hành vi thay đổi.
