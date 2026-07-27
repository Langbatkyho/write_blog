# Architecture Invariants

## Contract và nguồn chân lý

- Pydantic model là contract runtime cho dữ liệu có cấu trúc.
- Schema phải từ chối field ngoài contract khi dữ liệu cần fail-closed.
- Constant, filename map và dimension list chỉ có một nguồn định nghĩa.
- Prompt yêu cầu đúng schema; parser xác minh lại, không tự bịa field thiếu.
- Migration phải tách biệt với contract hiện hành và có test fixture cho phiên bản cũ.

## Ranh giới module

- Entrypoint/UI gọi use case; không chứa domain logic hoặc prompt lớn.
- Orchestrator điều phối thứ tự, không kiêm parser, formatter, persistence và provider client.
- Prompt builder chỉ xây request; parser chỉ chuẩn hóa/xác minh response.
- Compiler là hàm xác định từ canonical profile sang effective artifacts.
- Publisher quản lý transaction; không tái diễn giải profile hoặc prompt.
- Module mới phải có consumer thực tế và test; nếu không, đó là dead architecture.

## Provider và dependency

- Inject client/callable từ biên để test bằng fake hoặc stub.
- Provider mặc định không được ẩn sau silent fallback.
- Voice Lab gọi Gemini; OpenAI workflow blog và Antigravity là ranh giới khác.
- Không để metadata `provider` thay thế bằng chứng `api_called`.

## I/O và tính nguyên tử

- Ghi một file quan trọng qua temp file và atomic replace khi khả thi.
- Publish nhiều file theo `staging → validate → backup → replace`; rollback khi lỗi.
- Checkpoint chỉ tại ranh giới transaction nhất quán, không ghi trạng thái dở dang tùy tiện trong vòng lặp.
- ID phải chống va chạm và không ghi đè output đã tồn tại.

## Tương thích

- Xác định rõ đường migration, deprecation và lỗi cho dữ liệu legacy.
- Không duy trì hai contract “tạm thời” vô thời hạn.
- Thay đổi filename/slug phải dùng mapping rõ ràng, không suy đoán từ tên nội bộ.
