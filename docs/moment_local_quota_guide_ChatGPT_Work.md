# Chỉ Dẫn Viết Moment Blog Bằng Local Model Quota Trên ChatGPT Work

Ngày: 2026-07-22

## Mục tiêu

Chạy `moment_blog_mode` bằng Local Model Quota thông qua `antigravity` file bridge, với input mặc định:

```text
examples/blog_1.md
```

Lệnh chính:

```powershell
python engine/run_workflow.py --input examples/blog_1.md --mode moment --client antigravity
```

Kết quả mong đợi:

- tạo run mới trong `runs/`;
- chạy đủ 6 stage moment;
- tạo `moment_edited.md` làm output chính;
- giữ bài trong khoảng 300-600 từ, ngắn, hiện tại, trực giác;
- không dùng OpenAI API quota.

## Điều kiện trước khi chạy

Cần có:

- repo đang ở thư mục `D:\Nghiên cứu AI\write_blog`;
- `engine/config.local.yaml` đã cấu hình Local Model, ví dụ `GPT-OSS 120B (Medium)`;
- bridge `engine/antigravity_bridge.py` đọc model theo từng `stage_id`;
- model trong ChatGPT Work có khả năng đọc prompt file và ghi response file;
- workflow moment đã tồn tại tại `flow/write_moment_blog.yaml`;
- 6 skill moment đã tồn tại tại `skills/moment/reflective/`.

Kiểm tra nhanh:

```powershell
python -m unittest tests.test_moment_blog_mode tests.test_antigravity_bridge tests.test_client_router
```

## Cách chạy khuyến nghị

Không chạy lệnh antigravity đồng bộ trong terminal nếu tool sẽ chờ tới khi process kết thúc. Workflow sẽ dừng lại ở mỗi stage để chờ file response.

Hãy start workflow bằng background process:

```powershell
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = 'python'
$psi.Arguments = 'engine/run_workflow.py --input examples/blog_1.md --mode moment --client antigravity'
$psi.WorkingDirectory = 'D:\Nghiên cứu AI\write_blog'
$psi.UseShellExecute = $true
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$p = [System.Diagnostics.Process]::Start($psi)
$p.Id
```

Sau đó theo dõi thư mục:

```text
runs/temp_llm/
```

Mỗi stage sẽ tạo một prompt:

```text
prompt_{stage}_{timestamp}.txt
```

Cần đọc prompt đó và ghi response đúng tên:

```text
response_{stage}_{timestamp}.txt
```

Ví dụ:

```text
prompt_sensory_capture_1784714692561.txt
response_sensory_capture_1784714692561.txt
```

Response bắt buộc có đúng 2 heading cấp cao:

```markdown
## Artifact

<nội dung đầy đủ của stage>

## Handoff

<tóm tắt ngắn cho stage sau>
```

## Thứ tự 6 stage moment

```text
sensory_capture
-> inner_weather
-> cosmic_signal_reader
-> moment_writer
-> breath_editor
-> gentle_witness
```

## Chỉ dẫn viết cho từng stage

### 1. `sensory_capture`

Nhiệm vụ:

- chỉ ghi nhận cảnh, âm thanh, ánh sáng, nhiệt độ, thân thể;
- tách quan sát khỏi diễn giải;
- không rút bài học.

Output nên có:

- `central_moment`
- `visible_scene`
- `sensory_details`
- `bodily_sensations`
- `verbatim_fragments`
- `uncertain_details`

### 2. `inner_weather`

Nhiệm vụ:

- gọi tên thời tiết bên trong;
- gắn cảm xúc với dấu vết cơ thể;
- không phân tích tâm lý sâu.

Nên viết gần:

- ấm lên;
- nhẹ ra;
- mở ra;
- được vỗ về;
- thấy ổn.

Cần tránh:

- tỉnh thức;
- an lạc;
- chuyển hóa;
- bài học cuộc đời.

### 3. `cosmic_signal_reader`

Nhiệm vụ:

- tìm tín hiệu nhỏ, có căn cứ;
- không biến tín hiệu thành lời tiên tri;
- không nói thay vũ trụ bằng giọng quá chắc.

Với input `blog_1.md`, tín hiệu phù hợp:

```text
Mặt trời vẫn đến.
Và trong khoảnh khắc này, mình ổn.
```

### 4. `moment_writer`

Nhiệm vụ:

- viết bản nháp 300-600 từ;
- chỉ giữ một khoảnh khắc trung tâm;
- nhiều khoảng thở;
- kết bằng dư âm, không kết bằng bài học.

Cấu trúc nên dùng:

```text
Cảnh
-> Cảm giác thân thể
-> Tín hiệu nhỏ
-> Câu kết ngắn
```

### 5. `breath_editor`

Nhiệm vụ:

- cắt lặp;
- làm câu nhẹ hơn;
- không thêm ý mới;
- giữ bài dưới 600 từ.

Lưu ý parser:

Artifact nên có 2 mục:

```markdown
## Edited Blog

<bản đã edit>

## Edit Log

<các điểm đã cắt/chỉnh>
```

Engine sẽ tách thành:

- `moment_edited.md`
- `edit_log.md`

### 6. `gentle_witness`

Nhiệm vụ:

- xác nhận bài còn thật, còn trong, còn là một khoảnh khắc sống;
- không rewrite;
- không loop về editor;
- không coaching.

Output nên gồm:

- `what_still_feels_alive`
- `what_felt_forced`
- `what_should_remain_untouched`
- `verdict`

## Kiểm tra sau khi chạy

Tìm run mới nhất:

```powershell
Get-ChildItem runs -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime
```

Run thành công cần có:

```text
sensory_notes.md
inner_weather.md
signal_note.md
moment_draft.md
moment_edited.md
edit_log.md
witness_report.md
handoff_log.md
run_log.md
step_outputs.json
metadata.json
```

Quét lỗi:

```powershell
Select-String -Path 'runs\<run_folder>\run_log.md' -Pattern 'ERROR|Timeout|Traceback|Fallback'
```

Nếu không có output, chưa thấy lỗi rõ ràng.

Đếm từ output chính:

```powershell
$text = Get-Content -Raw 'runs\<run_folder>\moment_edited.md'
($text -split '\s+' | Where-Object { $_.Trim().Length -gt 0 }).Count
```

Kiểm tra metadata:

- `mode` phải là `moment`;
- `dry_run` phải là `false`;
- `stage_models` của 6 stage nên là Local Model;
- `workflow_file` phải trỏ tới `flow/write_moment_blog.yaml`;
- `total_artifact_estimated_tokens` và `total_handoff_estimated_tokens` nên có giá trị.

## Kết quả mẫu đã xác minh

Run ngày 2026-07-22:

```text
runs/20260722_170452_moment_reflective_kết-nối
```

Kết quả:

- chạy đủ 6 stage;
- output chính: `moment_edited.md`;
- khoảng 271 từ;
- không thấy `ERROR`, `Timeout`, `Traceback`, `Fallback`;
- `stage_models`: `GPT-OSS 120B (Medium)`;
- test suite: `34/34 OK`.

## Lỗi thường gặp

### 1. Workflow treo ở một stage

Nguyên nhân thường gặp:

- chưa ghi `response_{stage}_{timestamp}.txt`;
- response sai timestamp;
- response sai tên stage;
- response không có đúng 2 heading `## Artifact` và `## Handoff`.

### 2. Mojibake trong terminal

Terminal PowerShell có thể hiển thị sai tiếng Việt, nhưng file vẫn có thể là UTF-8. Ưu tiên mở file trong editor hỗ trợ UTF-8 để kiểm tra.

### 3. Moment bị thành deep mini

Cần cắt:

- giải thích dài;
- khái niệm lớn;
- lời khuyên;
- câu tổng kết quá chắc;
- các đoạn “tôi đã nhận ra...”.

### 4. `breath_editor` không tách được file

Kiểm tra artifact của `breath_editor` có đúng:

```markdown
## Edited Blog
## Edit Log
```

Không nên dùng heading `##` bên trong thân bài edited blog.

## Prompt điều phối nhanh cho ChatGPT Work

Dùng prompt này trong một task mới khi cần chạy lại:

````markdown
Bạn là Agentic Engineer trong workspace:

`D:\Nghiên cứu AI\write_blog`

Hãy chạy workflow:

```powershell
python engine/run_workflow.py --input examples/blog_1.md --mode moment --client antigravity
```

Chạy bằng background process nếu terminal sẽ bị block.

Theo dõi `runs/temp_llm/`. Với mỗi file:

`prompt_{stage}_{timestamp}.txt`

hãy đọc prompt và ghi file response tương ứng:

`response_{stage}_{timestamp}.txt`

Response phải có đúng:

```markdown
## Artifact

<artifact>

## Handoff

<handoff>
```

Stage order:

1. `sensory_capture`
2. `inner_weather`
3. `cosmic_signal_reader`
4. `moment_writer`
5. `breath_editor`
6. `gentle_witness`

Với `breath_editor`, artifact phải có:

```markdown
## Edited Blog

<bản blog đã edit>

## Edit Log

<log chỉnh sửa>
```

Sau khi hoàn tất, kiểm tra run mới nhất có đủ file, quét `run_log.md` với pattern `ERROR|Timeout|Traceback|Fallback`, đếm số từ `moment_edited.md`, đọc `metadata.json`, rồi báo lại:

- run folder;
- output chính;
- số từ;
- model/stage_models;
- lỗi nếu có;
- kết luận chất lượng moment.
````
