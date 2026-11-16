# Chạy Moment và Deep Blog từ một Codex Cloud task mới

Hướng dẫn này dành cho Codex web với repository `Langbatkyho/write_blog`. Mỗi bài mới nên chạy trong **một task xuyên suốt**: kiểm tra checkout → chạy các stage → tác giả duyệt → `finalize` → lưu file. Task khác có workspace riêng; hai file Markdown cuối không chứa checkpoint để tiếp tục workflow.

## 1. Trước khi mở task

1. Mở [PR #1](https://github.com/Langbatkyho/write_blog/pull/1) và xác định commit mới nhất của branch `codex/cloud-moment-workflow`. PR còn ở dạng draft và không cần merge vào `main` để thử Cloud.
2. Trong Codex web, tạo **New chat/task** gắn environment `write_blog` đã publish từ repository. Nếu giao diện cho chọn branch, chọn `codex/cloud-moment-workflow`. Nếu không, dùng bước kiểm tra/fetch bên dưới. Đừng suy ra branch chỉ từ tên environment.
3. Chuẩn bị ghi chú **thật** của tác giả để dán vào task. Không dùng `examples/` làm input nghiệp vụ. Chọn style hợp lệ: Moment có `va-natural` (đã thử thực tế) hoặc style Moment hiện có; Deep có `reflective` hoặc `provocative`.
4. Viết `desired_length` bằng khoảng số (`300-600 từ`, `1200-1800 từ`) hoặc một giới hạn rõ (`dưới 300 từ`, `tối đa 500 từ`, `tối thiểu 1200 từ`). Giá trị mơ hồ như “khoảng một trang” bị từ chối khi tạo run. Nếu không khai báo, mặc định của flow là Moment **300–600** và Deep **1200–1800** theo `engine.parser.count_words()`. Nếu muốn bài Moment 295 từ được chấp nhận trong run **mới**, phải khai báo `dưới 300 từ` từ đầu; việc chấp nhận ngoại lệ ở run cũ không thay đổi validator.

## 2. Kiểm tra checkout trong task mới

Dán yêu cầu này vào task mới trước khi gửi nội dung bài:

> Tìm repository `Langbatkyho/write_blog` (trước đây ở `/workspace/write_blog`) và đọc `AGENTS.md`, `.agents/AGENTS.md`. Chạy `pwd`, `git status --porcelain`, `git branch --show-current`, `git rev-parse HEAD` trong repository. Chạy `git fetch origin codex/cloud-moment-workflow` và so sánh HEAD với `FETCH_HEAD`. Nếu checkout sạch nhưng đang ở commit cũ hoặc `main`, chạy `git switch --detach FETCH_HEAD`; không reset hay xóa thay đổi có sẵn. Xác nhận file `.agents/skills/mindful-moment-writing/SKILL.md` và `.agents/skills/deep-blog-writing/SKILL.md` đọc được. Báo SHA cuối cùng và dừng; chưa tạo run.

`pwd` đầu phiên có thể là `/workspace`, còn repository nằm ở `/workspace/write_blog`. `git branch --show-current` trống khi ở **detached HEAD** là bình thường nếu SHA đúng. Nếu `git fetch` không chạy được hoặc checkout có thay đổi chưa rõ nguồn gốc, dừng trước khi tạo run và báo trạng thái. Danh mục Skill tự nạp có thể rỗng dù file tồn tại; liên kết mềm ở `/workspace/.agents/skills` cũng chưa chứng minh Skill được runtime nhận diện. Hãy yêu cầu task **đọc trực tiếp `SKILL.md`** tương ứng.

## 3A. Chạy Moment trong cùng task

Sau khi SHA đã đúng, dán prompt sau và thay phần trong ngoặc vuông bằng dữ liệu thật. Có thể để `desired_length: dưới 300 từ` nếu đó là giới hạn bạn thật sự muốn.

> Đọc trực tiếp `.agents/skills/mindful-moment-writing/SKILL.md` và làm theo `flow/write_moment_blog.yaml`. Đây là input thật của tôi; lưu nó thành file UTF-8 mới ngoài `examples/`, tạo run mới với `--mode moment --style va-natural` và output root riêng dưới `/workspace` (không dùng `runs/` của repo cho thử nghiệm). Dùng `python -m engine.cloud_stage_cli prepare`/`submit` theo đúng thứ tự, **mỗi stage một subagent mới**, chỉ đưa prompt do `prepare` trả về cho subagent đó. Lưu response nguyên văn trước khi `submit`; nếu bị từ chối, sửa response của stage hiện tại rồi gửi lại cùng token. Không sửa stage đã hoàn tất, không gọi API provider ngoài. Chạy đủ 6 stage: `sensory_capture`, `inner_weather`, `cosmic_signal_reader`, `moment_writer`, `breath_editor`, `gentle_witness`.
>
> Input của tôi:
>
> ```markdown
> title: [Tiêu đề]
> raw_notes:
> [Những quan sát và trải nghiệm thật của bạn]
> target_reader: [Nếu có]
> desired_length: 300-600 từ
> ```
>
> Sau stage cuối, kiểm tra `metadata.json` có `status: completed`, `step_outputs.json` có đủ 6 stage, và đếm `moment_edited.md` bằng `engine.parser.count_words()`. Đọc `witness_report.md` nhưng dùng số đếm của code nếu báo cáo nhận xét sai. Trình bày bản bài và nhận xét cho tôi duyệt. **Chưa chạy `finalize`, chưa tạo `final_blog.md` trước khi tôi chọn bài.** Báo đường dẫn run và các file đã có.

`run_log.md` xuất hiện từ lúc tạo run; **sự tồn tại của file này chưa chứng minh workflow đã hoàn tất**. Nếu `breath_editor` gửi bài ngoài giới hạn, `submit` sẽ từ chối trước khi ghi `moment_edited.md`; task cần giữ nguyên run và sửa đúng response của stage đó. Không khởi động run mới chỉ vì một response bị từ chối.

## 3B. Chạy Deep trong cùng task

Để thử Deep, dùng **một task mới khác** cho bài Deep. Sau bước 2, dán prompt sau:

> Đọc trực tiếp `.agents/skills/deep-blog-writing/SKILL.md` và làm theo `flow/write_blog.yaml`. Đây là input thật của tôi; lưu nó thành file UTF-8 mới ngoài `examples/`, tạo run mới với `--mode deep --style reflective` và output root riêng dưới `/workspace` (không dùng `runs/` của repo cho thử nghiệm). Dùng `python -m engine.cloud_stage_cli prepare`/`submit` theo đúng thứ tự, **mỗi stage một subagent mới**, chỉ đưa prompt do `prepare` trả về cho subagent đó. Lưu response nguyên văn trước khi `submit`; nếu bị từ chối, sửa response của stage hiện tại rồi gửi lại cùng token. Không sửa stage đã hoàn tất, không gọi API provider ngoài. Chạy đủ 7 stage: `story_architect`, `reflection_engine`, `writing_agent`, `reader_experience`, `editor_agent`, `coach_agent`, `future_self`.
>
> Riêng `reader_experience`, dùng subagent mới không thừa hưởng hội thoại nếu runtime hỗ trợ; chỉ đưa prompt từ `prepare`, không đưa ghi chú tác giả, story map, reflection hay handoff trước đó. Yêu cầu reader không tự đọc file khác trong workspace. Báo rõ nếu không thể bảo đảm cách ly quyền đọc, vì các subagent chia sẻ workspace.
>
> Input của tôi:
>
> ```markdown
> title: [Tiêu đề]
> raw_notes:
> [Sự kiện, suy nghĩ, chi tiết và giới hạn sự thật do bạn cung cấp]
> target_reader: [Nếu có]
> desired_length: 1200-1800 từ
> ```
>
> Sau stage cuối, kiểm tra `metadata.json` có `status: completed`, `step_outputs.json` có đủ 7 stage, `edited_blog.md` và `edit_log.md` đã được tách. Đếm `edited_blog.md` bằng `engine.parser.count_words()`. Trình bày bài đã sửa cùng `reader_report.md`, `coaching_report.md`, `future_reflection.md` cho tôi duyệt. **Chưa chạy `finalize`, chưa tạo `final_blog.md` trước khi tôi chọn bài.** Báo đường dẫn run và các file đã có.

Deep `reader_experience` được cách ly bằng **nội dung prompt**, không phải quyền truy cập filesystem. Việc agent mới nhận riêng prompt chưa đủ để khẳng định một phép đọc mù được bảo đảm kỹ thuật. `editor_agent` phải trả `## Edited Blog` và `## Edit Log` bên trong `## Artifact`; engine sẽ tách file và chặn bản `edited_blog.md` ngoài giới hạn độ dài.

## 4. Duyệt bài và `finalize` trong chính task đó

Đọc bài AI đã biên tập và các báo cáo. Sau khi quyết định, trả lời một trong hai cách:

- **Duyệt nguyên văn:** “Tôi duyệt nguyên văn `moment_edited.md`” hoặc “Tôi duyệt nguyên văn `edited_blog.md`”.
- **Duyệt bản chỉnh sửa:** Gửi toàn bộ nội dung bạn chọn và nói rõ đây là bản cuối được duyệt.

Với trường hợp duyệt nguyên văn, có thể gửi ngay trong **cùng task**:

> Tôi duyệt nguyên văn `[moment_edited.md hoặc edited_blog.md]` của run vừa hoàn tất. Hãy lưu nội dung đó vào một file approved riêng bên ngoài run, gọi `python -m engine.cloud_stage_cli finalize` với đúng `--run-dir` và `--approved-file`, rồi mở lại `final_blog.md` và `run_log.md` để kiểm tra. Nếu `final_blog.md` đã tồn tại, không ghi đè; hãy báo trạng thái hiện có.

Lệnh đầy đủ là `python -m engine.cloud_stage_cli finalize --run-dir <run_dir> --approved-file <path>`. `finalize` chuẩn hóa khoảng trắng ở hai đầu và thêm một newline cuối file; hãy kiểm tra nội dung thật trước khi nói “khớp nguyên văn”. Không ghi đè `final_blog.md` nếu nó đã tồn tại. Bản tác giả duyệt có thể là ngoại lệ về độ dài; validator kiểm tra bản AI đã biên tập ở stage editor, không thay tác giả quyết định bản cuối.

## 5. Lưu `final_blog.md` và `run_log.md`

Trong task đã tạo run, yêu cầu kiểm tra lại cả hai file, báo **SHA-256** và **số byte** bằng `sha256sum` và `wc -c`. Nếu client cho tải file, tải **riêng từng file Markdown**. Trên Codex web đã gặp trường hợp chỉ thư mục `/codex/.../output` được phép làm liên kết tải nhưng thư mục này chỉ đọc; đường dẫn `/workspace/...` khi đó **không phải link tải** dù file tồn tại. Đừng yêu cầu task tạo một link mà client chặn.

Prompt bàn giao có thể dán vào cùng task:

> Hãy mở lại `final_blog.md` và `run_log.md` của run vừa hoàn tất, báo đường dẫn tuyệt đối, số byte và SHA-256 của từng file. Nếu client cho tải hai file riêng, cung cấp cách tải và xác nhận liên kết hoạt động. Nếu Codex web chặn link tải, nói rõ giới hạn rồi gửi nguyên văn `final_blog.md` trong một câu trả lời và nguyên văn `run_log.md` trong câu trả lời tiếp theo, không tóm tắt hay sửa nội dung; chia log thành các phần có số thứ tự nếu cần. Giữ nguyên run gốc.

Nếu bị chặn, yêu cầu task trả **nguyên văn từng file trong hai câu trả lời riêng**, không tóm tắt; chia `run_log.md` thành các phần đánh số nếu quá dài. Lưu trên máy thành file UTF-8; kiểm tra SHA-256 và số byte. Trên Windows PowerShell dùng `Get-FileHash -Algorithm SHA256 .\final_blog.md` (tương tự cho log); trên Linux dùng `sha256sum final_blog.md run_log.md`. Nếu copy văn bản làm sai newline hoặc bị cắt, yêu cầu task xuất byte gốc thành các đoạn base64 có đánh số, ghép và giải mã cục bộ rồi kiểm tra lại hash. Không đưa nội dung bài riêng tư lên GitHub chỉ để tải file nếu chưa chủ động chọn cách lưu đó.

Với phương án base64, trong task gốc yêu cầu xuất riêng `base64 -w 0 <file>` cho mỗi file; nếu quá dài, chia chuỗi thành các đoạn có số thứ tự, **không thêm ký tự vào chuỗi**. Trên máy của bạn, ghép các đoạn theo thứ tự vào `final_blog.b64` và `run_log.b64`. Trên Windows PowerShell, giải mã bằng:

```powershell
[IO.File]::WriteAllBytes("final_blog.md", [Convert]::FromBase64String((Get-Content -Raw "final_blog.b64")))
[IO.File]::WriteAllBytes("run_log.md", [Convert]::FromBase64String((Get-Content -Raw "run_log.b64")))
Get-FileHash -Algorithm SHA256 final_blog.md, run_log.md
```

Trên Linux dùng `base64 -d final_blog.b64 > final_blog.md` và tương tự cho log. Chỉ chấp nhận bản lưu khi hash khớp hash task đã báo.

## 6. Khi task bị ngắt hoặc mở task khác

- **Cùng task, còn run:** gọi lại `prepare --run-dir <run_dir>` để lấy stage chưa hoàn tất; không chạy lại stage đã checkpoint.
- **Task mới:** workspace có thể khác. Muốn tiếp tục run cũ phải `export` ZIP checkpoint từ task gốc, chuyển ZIP sang task mới và `import` vào output root mới. Hai file `final_blog.md` và `run_log.md` không đủ để khôi phục các stage. Nếu Codex web cũng chặn tải ZIP, ở lại task gốc để hoàn tất; đừng giả định task mới nhìn thấy run cũ.
- **Đổi code giữa chừng:** metadata giữ hash của flow và YAML từng stage; khi import/resume, task mới phải dùng đúng revision tương thích. Đừng tự sửa metadata hoặc artifact để vượt kiểm tra hash.

## 7. Dấu hiệu nghiệm thu

| Kiểm tra | Moment | Deep |
|---|---|---|
| Stage hoàn tất | 6/6 | 7/7 |
| Bản AI đã biên tập | `moment_edited.md` | `edited_blog.md` |
| Báo cáo cần đọc | `witness_report.md` | `reader_report.md`, `coaching_report.md`, `future_reflection.md` |
| Độ dài mặc định | 300–600 từ | 1200–1800 từ |
| Sau khi tác giả duyệt | `final_blog.md` và `run_log.md` | `final_blog.md` và `run_log.md` |

Chỉ coi task nghiệm thu đầy đủ khi trạng thái và số stage đúng, **bản AI đã biên tập** đạt giới hạn do code kiểm tra, tác giả đã duyệt bài cuối, và hai file Markdown đã được lưu/kiểm tra trên máy. Tác giả có thể chấp nhận bản cuối của mình ngoài giới hạn, nhưng cần ghi nhận rõ lựa chọn đó. Skill không xuất hiện trong danh mục tự động hay checkout detached HEAD **không tự nó là lỗi** nếu file Skill đọc được và SHA đúng.
