# Contract chuẩn bị cho workflow trên Codex Cloud

Nguồn chuẩn theo thứ tự trách nhiệm:

- `flow/*.yaml`: thứ tự, dependency, context policy, tên artifact/handoff và final output.
- `skills/<mode>/<style>/*.yaml`: nhiệm vụ, ranh giới vai trò, giọng văn và độ dài handoff theo stage.
- Input tác giả: độ dài và nội dung cụ thể của bài. Khi hẹp hơn gợi ý độ dài của style, yêu cầu tác giả được ưu tiên; output contract của flow vẫn áp dụng.
- Engine: xác thực và lưu kết quả. Không suy ra trạng thái hoàn tất chỉ từ tên thư mục.

Một response stage gồm đúng hai heading cấp hai `## Artifact` và `## Handoff`. Với editor có secondary artifact, bên trong Artifact phải có `## Edited Blog` và `## Edit Log`; engine tách thành file bài đã sửa và edit log. Handoff chỉ dành cho stage sau và dùng độ dài khai báo ở YAML; nếu không khai báo, mặc định 120–250 từ.

`moment_edited.md` và `edited_blog.md` là bản AI đã biên tập. `final_blog.md` là bản tác giả đã chọn để hoàn thiện; `production_blog.md` là bản đã chỉnh sửa để xuất bản hoặc đưa vào learning loop. Không tự coi việc sao chép bản AI sang `final_blog.md` là bằng chứng tác giả đã duyệt.

Khi kiểm tra độ dài, `engine.parser.count_words()` chuẩn hóa Unicode NFC rồi đếm các cụm `\w+`. Đây là quy ước đếm có thể lặp lại bằng code, không phải phép tách từ ngữ nghĩa tiếng Việt. Với giới hạn “dưới 300 từ”, kết quả phải nhỏ hơn 300 theo quy ước này.

Trên Codex Cloud, `submit` kiểm tra độ dài bài sau khi tách `Edited Blog` ở stage `breath_editor`, trước khi lưu artifact hoặc checkpoint. Mức giới hạn lấy từ `desired_length` của input, hoặc giá trị mặc định trong flow khi input không khai báo. Response ngoài giới hạn bị từ chối và có thể gửi lại cùng token với nội dung đã sửa. Kiểm tra này không sửa các run đã hoàn tất bằng phiên bản cũ; với run đó, phải báo số từ thực tế nếu `witness_report.md` nhận xét sai.

Bàn giao ưu tiên hai file Markdown có thể tải riêng. Khi client chỉ cho phép tải từ thư mục output chỉ đọc, không được giả định một liên kết tới file trong workspace sẽ hoạt động. Bàn giao nguyên văn từng file kèm SHA-256 và số byte để tác giả tự lưu và kiểm tra; run gốc vẫn chỉ đọc sau khi hoàn tất.

Metadata của run mới ghi SHA-256 cho flow và từng file stage YAML đã dùng. Hash phục vụ truy vết phiên bản thực thi; nó không tự lưu bản sao YAML hoặc bảo đảm file còn tồn tại về sau.
