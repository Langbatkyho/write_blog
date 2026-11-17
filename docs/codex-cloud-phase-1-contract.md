# Contract chuẩn bị cho workflow trên Codex Cloud

Nguồn chuẩn theo thứ tự trách nhiệm:

- `flow/*.yaml`: thứ tự, dependency, context policy, tên artifact/handoff và final output.
- `skills/<mode>/<style>/*.yaml`: nhiệm vụ, ranh giới vai trò, giọng văn và độ dài handoff theo stage.
- Input tác giả: độ dài và nội dung cụ thể của bài. Khi hẹp hơn gợi ý độ dài của style, yêu cầu tác giả được ưu tiên; output contract của flow vẫn áp dụng.
- Engine: xác thực và lưu kết quả. Không suy ra trạng thái hoàn tất chỉ từ tên thư mục.

Một response stage gồm đúng hai heading cấp hai `## Artifact` và `## Handoff`. Với editor có secondary artifact, bên trong Artifact phải có `## Edited Blog` và `## Edit Log`; engine tách thành file bài đã sửa và edit log. Handoff chỉ dành cho stage sau và dùng độ dài khai báo ở YAML; nếu không khai báo, mặc định 120–250 từ.

`moment_edited.md` và `edited_blog.md` là bản AI đã biên tập. `final_blog.md` là bản tác giả đã chọn để hoàn thiện; `production_blog.md` là bản đã chỉnh sửa để xuất bản hoặc đưa vào learning loop. Không tự coi việc sao chép bản AI sang `final_blog.md` là bằng chứng tác giả đã duyệt.

Khi kiểm tra độ dài, `engine.parser.count_words()` chuẩn hóa Unicode NFC rồi đếm các cụm `\w+`. Đây là quy ước đếm có thể lặp lại bằng code, không phải phép tách từ ngữ nghĩa tiếng Việt. Với giới hạn “dưới 300 từ”, kết quả phải nhỏ hơn 300 theo quy ước này.

Trên Codex Cloud, `submit` kiểm tra độ dài bài sau khi tách `Edited Blog` ở stage tạo `final_output.primary_ai_draft`: `breath_editor` cho Moment, `editor_agent` cho Deep. Mức giới hạn lấy từ `desired_length` của input, hoặc giá trị mặc định trong flow khi input không khai báo (Moment 300–600 từ, Deep 1200–1800 từ). Response ngoài giới hạn bị từ chối trước khi lưu artifact/checkpoint và có thể gửi lại cùng token với nội dung đã sửa. Kiểm tra này không sửa các run đã hoàn tất bằng phiên bản cũ; với run đó, phải báo số từ thực tế nếu báo cáo nhận xét sai.

`desired_length` chấp nhận khoảng số (`1200-1800 từ`), `dưới N`, `tối đa N` hoặc `tối thiểu N` (cùng các cách viết tiếng Anh tương ứng). Giá trị không xác định được sẽ bị từ chối ngay khi tạo run, trước khi ghi file.

Deep `reader_experience` nhận prompt chỉ có bản nháp từ `writing_agent` và YAML của reader, không có input tác giả hay handoff từ các stage trước. Skill yêu cầu một subagent mới, không thừa hưởng hội thoại và không tự đọc các file khác. Các subagent vẫn có thể đọc cùng workspace; vì vậy ranh giới này chỉ kiểm soát context được gửi, không bảo đảm cách ly bằng quyền truy cập.

Bàn giao ưu tiên hai file Markdown có thể tải riêng. Khi client chỉ cho phép tải từ thư mục output chỉ đọc, không được giả định một liên kết tới file trong workspace sẽ hoạt động. Bàn giao nguyên văn từng file kèm SHA-256 và số byte để tác giả tự lưu và kiểm tra; run gốc vẫn chỉ đọc sau khi hoàn tất.

Metadata của run mới ghi SHA-256 cho flow và từng file stage YAML đã dùng. Hash phục vụ truy vết phiên bản thực thi; nó không tự lưu bản sao YAML hoặc bảo đảm file còn tồn tại về sau.

## Phục hồi checkpoint Cloud (P0)

`step_outputs.json` là nguồn chuẩn cho các stage đã commit; các khóa phải là một đoạn đầu đúng thứ tự của flow. `verify --run-dir` chỉ đọc và đối chiếu artifact, handoff, log, metadata với checkpoint. Stage cuối đã commit nhưng metadata còn `running` hoặc log còn đúng bản của checkpoint trước được báo `needs_recovery`. `prepare`, `submit`, `finalize` dừng với thông báo cần phục hồi trong trạng thái này.

`recover --run-dir` tái tạo file thiếu, cập nhật log cũ đã xác minh và sửa metadata dẫn xuất từ checkpoint. Nội dung hiện có khác bản có thể tái dựng là xung đột và không bị ghi đè. File của stage chưa commit trong checkpoint không được coi là stage hoàn tất; có thể gửi lại response của stage đó. Chỉ gọi `recover` trên run được phép sửa; run nghiệp vụ đã hoàn tất mặc định chỉ đọc theo `.agents/AGENTS.md`.

## Toàn vẹn và dấu vết finalize (P1)

Run mới ghi `protocol_version: 2`, SHA-256 của input, từng artifact/handoff trong checkpoint, SHA của các module runtime Cloud và commit nguồn nếu Git cung cấp. Commit và hash runtime phục vụ truy vết; `resume` không khóa cứng theo commit vì thay đổi tài liệu không làm hỏng contract. Run cũ không có version được đọc như phiên bản 1 và không tự nhận là đã có hash lịch sử. `verify` chặn input/checkpoint có hash sai. Export xác minh run trước khi tạo ZIP; import xác minh sau khi staging và trước khi công bố run.

`finalize` lưu receipt trong metadata: thời điểm UTC, SHA của approved file, SHA file cuối, nguồn approved file và quy tắc chuẩn hóa. Run log ghi sự kiện phê duyệt từ receipt. Gọi lại cùng approved file trả file cũ; nội dung khác bị từ chối. Nếu gián đoạn sau khi tạo file cuối hoặc sau receipt, dùng cùng approved file hoặc `verify`/`recover` để hoàn tất. Receipt ghi lại việc CLI nhận file do tác giả chọn, không tự chứng minh danh tính người phê duyệt.
