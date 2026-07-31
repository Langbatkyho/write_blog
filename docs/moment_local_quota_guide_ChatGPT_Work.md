# Chỉ Dẫn Chạy Moment Blog Bằng Local Model Quota Trên ChatGPT Work

Ngày cập nhật: 2026-07-28

## Mục tiêu

Chạy workflow viết blog ngắn bằng `moment` mode, style `va-natural`, qua Local Model Quota bằng `antigravity` file bridge.

Input chuẩn:

```text
examples/moment_1.md
```

Lệnh workflow:

```powershell
python engine/run_workflow.py --input examples/moment_1.md --mode moment --style va-natural --client antigravity
```

Kết quả cần đạt:

- tạo một run mới trong `runs/`;
- chạy đủ 6 stage của moment workflow;
- dùng style `skills/moment/va-natural/`;
- dùng Antigravity bridge qua `runs/temp_llm/`;
- tạo output chính `moment_edited.md` và bản copy xuất bản `final_blog.md`;
- nội dung bài cuối không vượt quá 300 từ.

## Điều kiện trước khi chạy

Workspace:

```text
D:\Nghiên cứu AI\write_blog
```

Cần có các thành phần sau:

- workflow moment tại `flow/write_moment_blog.yaml`;
- style `va-natural` tại `skills/moment/va-natural/`;
- input tại `examples/moment_1.md`;
- bridge tại `engine/antigravity_bridge.py`;
- client router hỗ trợ `--client antigravity`;
- `engine/config.local.yaml` hoặc fallback `engine/config.example.yaml` có model local phù hợp.

Kiểm tra nhanh các file style:

```powershell
Get-ChildItem skills/moment/va-natural -File
```

Style hợp lệ cần có 6 file:

```text
sensory_capture.yaml
inner_weather.yaml
cosmic_signal_reader.yaml
moment_writer.yaml
breath_editor.yaml
gentle_witness.yaml
```

## Cách chạy

Workflow Antigravity là file bridge. Khi chạy, engine tạo một run folder mới ngay khi bắt đầu, rồi tạo prompt ở:

```text
runs/temp_llm/
```

Điều này có nghĩa là:

- mỗi lần khởi động lệnh workflow sẽ tạo một run folder mới trong `runs/`;
- nhiều lần khởi động cùng input/title có thể tạo nhiều folder cùng slug, ví dụ cùng chứa `_moment_va-natural_...`;
- chỉ coi run là kết quả cuối khi `metadata.json` có `"status": "completed"`;
- run có `"status": "failed"` là lần đã lỗi hoặc timeout;
- run còn `"status": "running"` nhưng không còn process/prompt đang chờ thường là lần khởi động dở hoặc stale, không phải output cuối.

Trước khi chạy lại, nên kiểm tra nhanh có prompt Antigravity nào đang chờ không:

```powershell
Get-ChildItem runs/temp_llm -Filter 'prompt_*.txt' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 10 Name,LastWriteTime
```

Nếu có prompt cũ, phải xác định nó thuộc lần chạy nào trước khi ghi response. Không ghi response cho prompt cũ nếu bạn đang muốn bắt đầu một workflow mới.

Mỗi stage tạo một file:

```text
prompt_{stage}_{timestamp}.txt
```

Người vận hành cần đọc prompt đó và ghi response cùng timestamp:

```text
response_{stage}_{timestamp}.txt
```

Ví dụ:

```text
prompt_sensory_capture_1785072981188.txt
response_sensory_capture_1785072981188.txt
```

Response phải có đúng 2 heading cấp cao:

```markdown
## Artifact

<nội dung đầy đủ của stage>

## Handoff

<tóm tắt ngắn cho stage sau>
```

Lưu ý quan trọng: file response nên là UTF-8 không BOM. Nếu response có BOM trước `## Artifact`, parser có thể không nhận heading đầu tiên và ghi cả `Artifact/Handoff` vào output cuối.

## Thứ tự 6 stage

```text
sensory_capture
-> inner_weather
-> cosmic_signal_reader
-> moment_writer
-> breath_editor
-> gentle_witness
```

## Chỉ dẫn theo stage cho input `moment_1.md`

### 1. `sensory_capture`

Nhiệm vụ:

- bắt khoảnh khắc trung tâm: hoa nở không vì ai;
- ghi hình ảnh hoa sáng, xanh non, cánh mở tự nhiên;
- đối chiếu nhẹ với con người hay cần công bằng, động viên, ghi nhận;
- không rút bài học.

Tinh thần nên giữ:

```text
Hoa vô tư, người thì lỉnh kỉnh.
Biết sống như hoa là đẹp, nhưng khó lắm người ơi.
```

### 2. `inner_weather`

Nhiệm vụ:

- gọi tên thời tiết bên trong;
- gắn cảm xúc với thân thể;
- giữ giọng tự chấp nhận, không bi lụy.

Hướng phù hợp:

```text
mong được đủ
mỏi nhẹ ở ngực và vai
thôi trách mình vì chưa vô sự được ngay
```

### 3. `cosmic_signal_reader`

Nhiệm vụ:

- nghe tín hiệu nhỏ, có căn cứ;
- không biến “người vô sự” thành tiêu chuẩn mới để ép mình;
- giữ ẩn dụ hoa như một lời nhắc mềm.

Tín hiệu phù hợp:

```text
Bớt xin phép một chút.
Bớt chờ công nhận một chút.
Quay về chăm cái gốc của mình.
```

### 4. `moment_writer`

Nhiệm vụ:

- viết bản nháp bài moment bằng tiếng Việt;
- dùng giọng `va-natural`: thân mật, dịu, có “mình/tui”, hơi tự trêu;
- giữ bài dưới 300 từ ngay từ bản nháp nếu input yêu cầu `desired_length: dưới 300 từ`.

Cấu trúc khuyến nghị:

```text
Nhìn hoa
-> Hoa không cần công nhận
-> Mình vẫn cần được thấy và được thương
-> Người vô sự là không bỏ rơi mình trong lúc chờ hoa nở
```

### 5. `breath_editor`

Nhiệm vụ:

- cắt nhẹ;
- làm câu thở hơn;
- không thêm insight mới;
- bảo đảm bài cuối dưới 300 từ.

Với style `va-natural`, artifact của stage này nên là chính bài cuối, không kèm edit log trong Artifact:

```markdown
## Artifact

# Người vô sự

<bài cuối dưới 300 từ>

## Handoff

<xác nhận ngắn về các chỉnh sửa và số từ>
```

Sau stage này engine ghi output chính:

```text
moment_edited.md
```

Nếu muốn có bản xuất bản rõ ràng, copy nội dung bài cuối sang:

```text
final_blog.md
```

### 6. `gentle_witness`

Nhiệm vụ:

- xác nhận bài còn là một khoảnh khắc sống;
- không rewrite;
- không thêm lời khuyên;
- kiểm tra bài không bị thành bài giảng.

Kết luận mong muốn:

```text
Đạt: dưới 300 từ, đúng tinh thần va-natural, ấm áp, thân mật, tự chấp nhận.
```

## Ghi response bằng UTF-8 không BOM trong PowerShell

Nếu ghi response bằng PowerShell, ưu tiên cách này:

```powershell
$responsePath = 'runs/temp_llm/response_sensory_capture_1785072981188.txt'
$text = @'
## Artifact

<artifact>

## Handoff

<handoff>
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Resolve-Path $responsePath), $text, $utf8NoBom)
```

Tránh để ký tự BOM hoặc dòng trống lạ đứng trước `## Artifact`.

## Kiểm tra sau khi chạy

Tìm các run mới nhất:

```powershell
Get-ChildItem runs -Directory |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 Name,LastWriteTime
```

Không chọn run chỉ dựa vào tên slug. Hãy kiểm tra trạng thái:

```powershell
Select-String -Path 'runs/<run_folder>/metadata.json' `
  -Pattern '"status"|"completed_at"|"api_called"|"provider"|"model"|"mode"|"style"'
```

Kỳ vọng với run hoàn tất:

```text
status      -> completed
provider    -> antigravity
api_called  -> false
mode        -> moment
style       -> va-natural
```

Nếu có nhiều folder cùng slug, phân loại như sau:

```powershell
$runs = Get-ChildItem runs -Directory | Where-Object { $_.Name -like '*_moment_va-natural_*' }
foreach ($run in $runs) {
  "--- $($run.Name)"
  Select-String -Path (Join-Path $run.FullName 'metadata.json') `
    -Pattern '"status"|"created_at"|"completed_at"|"api_called"' |
    ForEach-Object { $_.Line.Trim() }
}
```

Quy ước đọc kết quả:

- `completed`: run thành công, dùng folder này để lấy `final_blog.md`;
- `failed`: run lỗi hoặc timeout, chỉ dùng để audit;
- `running`: chỉ tin là đang chạy nếu còn process workflow hoặc prompt mới đang chờ response;
- `running` nhưng không có prompt/process liên quan: coi là stale/abandoned, không dùng làm output cuối.

Run thành công cần có:

```text
input.md
metadata.json
run_log.md
handoff_log.md
step_outputs.json
sensory_notes.md
inner_weather.md
signal_note.md
moment_draft.md
moment_edited.md
witness_report.md
final_blog.md
```

Quét lỗi:

```powershell
Select-String -Path 'runs/<run_folder>/run_log.md' -Pattern 'ERROR|Timeout|Traceback|Fallback'
```

Kiểm tra metadata:

```powershell
Select-String -Path 'runs/<run_folder>/metadata.json' `
  -Pattern '"workflow_file"|"input_file"|"style"|"mode"|"dry_run"|"status"|"api_called"'
```

Kỳ vọng:

```text
workflow_file -> flow/write_moment_blog.yaml
input_file    -> examples/moment_1.md
style         -> va-natural
mode          -> moment
dry_run       -> false
status        -> completed
api_called    -> false
```

Đếm từ bài cuối:

```powershell
$p = 'runs/<run_folder>/final_blog.md'
$text = Get-Content -Raw -Encoding UTF8 -LiteralPath $p
([regex]::Matches(($text -replace '#[^\s]+',''),'[\p{L}\p{N}]+')).Count
```

Kết quả phải nhỏ hơn hoặc bằng `300`.

## Run đã xác minh

Run ngày 2026-07-26:

```text
runs/20260726_203621_moment_va-natural_người-vô-sự
```

Kết quả:

- input: `examples/moment_1.md`;
- mode: `moment`;
- style: `va-natural`;
- client: `antigravity` qua `runs/temp_llm/`;
- chạy đủ 6 stage;
- output chính: `moment_edited.md`;
- bản xuất bản: `final_blog.md`;
- số từ bài cuối: 237;
- không còn prompt đang chờ trong `runs/temp_llm/`;
- không còn Python workflow process treo sau khi hoàn tất.

## Khi có nhiều run cùng slug

Nếu thấy nhiều folder cùng chứa một phần tên như `_moment_va-natural_người-vô-sự`, đó không nhất thiết là lỗi ghi đè. Engine chủ động tạo run ID collision-safe bằng timestamp + UUID, nên mỗi lần khởi động lệnh là một folder sibling mới.

Nguyên nhân thường gặp:

- lệnh workflow được chạy nhiều lần;
- lần trước timeout khi chờ Antigravity response;
- process bị dừng giữa chừng sau khi đã tạo run folder;
- người vận hành tạo response cho prompt cũ, rồi chạy lại workflow mới.

Không tự xóa các run này. Theo quy tắc dữ liệu của repo, run cũ là dữ liệu nghiệp vụ. Nếu cần dọn, trước hết phải lập danh sách đường dẫn tuyệt đối, phân loại trạng thái bằng `metadata.json`, rồi xin phê duyệt phạm vi xóa cụ thể.

Khi báo cáo kết quả, luôn ghi rõ:

```text
Run thành công: runs/<completed_run_folder>
Status: completed
Output chính: runs/<completed_run_folder>/final_blog.md
Các run cùng slug khác: failed/running/stale, chỉ dùng để audit
```

## Prompt điều phối nhanh cho ChatGPT Work

Dùng prompt này khi cần chạy lại:

````markdown
Bạn là Agentic Engineer trong workspace:

`D:\Nghiên cứu AI\write_blog`

Hãy chạy workflow:

```powershell
python engine/run_workflow.py --input examples/moment_1.md --mode moment --style va-natural --client antigravity
```

Theo dõi `runs/temp_llm/`. Với mỗi file:

`prompt_{stage}_{timestamp}.txt`

hãy đọc prompt và ghi file response tương ứng:

`response_{stage}_{timestamp}.txt`

Response phải là UTF-8 không BOM và có đúng:

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

Yêu cầu riêng:

- dùng đúng style `va-natural`;
- không khởi động lại workflow nếu đã có prompt mới đang chờ response cho chính lần chạy hiện tại;
- nếu có nhiều folder cùng slug, chỉ lấy kết quả từ run có `metadata.json` ghi `"status": "completed"`;
- với `moment_writer` và `breath_editor`, giữ bài dưới 300 từ;
- artifact của `breath_editor` chỉ nên chứa bài cuối, không kèm edit log;
- sau khi hoàn tất, tạo hoặc xác nhận `final_blog.md`;
- đếm từ `final_blog.md`;
- báo lại run folder completed, output chính, số từ, mode/style, api_called, và các run cùng slug đang failed/running/stale nếu có.
````
