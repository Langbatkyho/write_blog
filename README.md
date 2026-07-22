# Mindful Blog Workflow

Dự án này dùng các file YAML trong thư mục `skills/` để vận hành hệ hai chế độ viết blog phản tư và khoảnh khắc có hỗ trợ AI:

- **`deep_blog_mode`** (`--mode deep`): Viết dài (1000-1500 từ), phản tư sâu, chuyển hóa trải nghiệm.
- **`moment_blog_mode`** (`--mode moment`): Viết ngắn (300-600 từ), hiện tại, cảm giác giác quan, lắng nghe tín hiệu khoảnh khắc.

Triết lý hiện tại: mỗi agent chỉ trung thành với một câu hỏi duy nhất. AI không thay người viết ra quyết định cuối cùng; AI tạo bản nháp, phản hồi, chỉnh sửa tối thiểu, coaching, và phản tư để người viết tự hoàn thiện `final_blog.md` / `production_blog.md`.

## Hai Writing Modes

### 1. Deep Blog Mode (`--mode deep`)

```text
story_architect
  -> reflection_engine
  -> writing_agent
  -> reader_experience
  -> editor_agent
  -> coach_agent
  -> future_self
  -> human writer
```

### 2. Moment Blog Mode (`--mode moment`)

```text
sensory_capture
  -> inner_weather
  -> cosmic_signal_reader
  -> moment_writer
  -> breath_editor
  -> gentle_witness
  -> human writer
```

Outputs chính của `moment_blog_mode`:

- `sensory_notes.md`: ghi nhận cảnh vật, giác quan, cảm giác thân thể.
- `inner_weather.md`: gọi tên thời tiết bên trong hiện tại.
- `signal_note.md`: tín hiệu trực giác nhỏ, có căn cứ.
- `moment_draft.md`: bản nháp ngắn (300-600 từ) giữ năng lượng hiện tại.
- `moment_edited.md`: bản cắt gọt làm nhẹ bởi `breath_editor`.
- `witness_report.md`: xác nhận bài viết còn là khoảnh khắc sống từ `gentle_witness`.

## Vai Trò Các Agent Theo Mode

### Moment Mode Agents

| Agent | Trung thành với | Câu hỏi chính |
| --- | --- | --- |
| `sensory_capture` | Giác quan | Khoảnh khắc này đang hiện ra qua giác quan như thế nào? |
| `inner_weather` | Trạng thái | Thời tiết bên trong người viết ngay lúc này là gì? |
| `cosmic_signal_reader` | Trực giác | Khoảnh khắc này đang thì thầm điều gì với người viết? |
| `moment_writer` | Năng lượng hiện tại | Nếu chỉ giữ lại khoảnh khắc này, bài viết cần nói điều gì? |
| `breath_editor` | Độ trong | Cần bỏ hoặc làm nhẹ điều gì để khoảnh khắc được tự cất tiếng? |
| `gentle_witness` | Sự thật | Bài viết còn là một khoảnh khắc sống hay đã bị kéo thành bài học? |

### Deep Mode Agents

| Agent | Trung thành với | Câu hỏi chính |
| --- | --- | --- |
| `story_architect` | Câu chuyện | Điều gì thật sự đã xảy ra? |
| `reflection_engine` | Nhận thức | Điều gì thay đổi bên trong người viết? |
| `writing_agent` | Giọng người viết | Nếu có đủ thời gian, tác giả sẽ kể chuyện này thế nào? |
| `reader_experience` | Trải nghiệm đọc | Độc giả lần đầu đã cảm thấy gì? |
| `editor_agent` | Kết nối | Cần thay đổi tối thiểu điều gì để giảm ma sát? |
| `coach_agent` | Sự phát triển | Người viết còn chưa nhìn thấy điều gì? |
| `future_self` | Con người đang trở thành | 5 năm nữa, tác giả còn muốn đứng tên bài này không? |

## Artifact Và Handoff

Mỗi stage phải trả về:

```markdown
## Artifact

Nội dung đầy đủ để lưu log, debug, review, hoặc làm output thật.

## Handoff

Bản tóm tắt có cấu trúc khoảng 120-250 từ tiếng Việt cho stage sau.
```

Engine chỉ truyền những handoff hoặc artifact được khai báo trong `context_policy` của `flow/write_blog.yaml`.

Ví dụ:

- `reader_experience` chỉ nhận `draft_blog.md`, để giữ blind review.
- `editor_agent` nhận `draft_blog.md` và `reader_report.md`, rồi tạo `edited_blog.md` và `edit_log.md`.
- `future_self` nhận `edited_blog.md`, `editor_handoff`, `coaching_handoff`, và `reflection_handoff`, nhưng không rewrite bài.

## Chạy Tự Động Bằng OpenAI API

Đặt API key vào biến môi trường:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Nếu cần cấu hình riêng:

```powershell
Copy-Item engine/config.example.yaml engine/config.local.yaml
```

Chạy deep blog mode (mặc định):

```powershell
python engine/run_workflow.py --input examples/blog_input_template.md --mode deep
```

Chạy moment blog mode (viết ngắn, hiện tại):

```powershell
python engine/run_workflow.py --input examples/moment_blog_input_template.md --mode moment
```

Chạy workflow với phong cách khác (ví dụ `provocative` cho deep mode):

```powershell
python engine/run_workflow.py --input examples/blog_input_template.md --mode deep --style provocative
```

Kiểm tra không gọi API (dry-run):

```powershell
python engine/run_workflow.py --input examples/moment_blog_input_template.md --mode moment --dry-run
```

Mỗi run tạo thư mục riêng trong `runs/`, gồm:

- `run_log.md`: log artifact đầy đủ.
- `handoff_log.md`: chuỗi handoff rút gọn.
- `step_outputs.json`: artifact, handoff, file names, fallback flag, token estimates.
- `metadata.json`: model, endpoint, context strategy, token metrics.

## Chạy Bằng Native Model (Không Cần API Key)

Dùng Antigravity bridge để tận dụng model quota nội bộ (chỉ áp dụng cho các **Agentic Models** như Gemini 3.1 Pro, Claude Sonnet 4.6):

```powershell
python engine/run_workflow.py --input examples/blog_input_template.md --client antigravity
```

> [!WARNING]
> Cơ chế Bridge yêu cầu model trên giao diện chat phải có năng lực **Tool Calling** xuất sắc để tự động đọc/ghi file (ví dụ: `view_file`, `write_to_file`). Nếu bạn chọn các model thuần text (như GPT-OSS 120B) trên giao diện chat, script sẽ bị treo (Timeout) do model không biết cách ghi file trả kết quả.

### Phân vai Model theo Stage (Client Map)

Gán client khác nhau cho từng stage:

```powershell
python engine/run_workflow.py --input examples/blog_input_template.md \
  --client antigravity \
  --client-map "story_architect=antigravity,writing_agent=antigravity,reader_experience=antigravity,editor_agent=antigravity,coach_agent=antigravity,future_self=antigravity,reflection_engine=antigravity"
```

Giải thích:
- `--client antigravity`: Fallback cho stage không được liệt kê.
- `--client-map`: Override client cụ thể cho từng stage.
- Stage không có trong map sẽ dùng `--client` làm mặc định.

## Chọn Model Theo Stage

`engine/config.example.yaml` hỗ trợ model mặc định và override từng stage:

```yaml
openai:
  model: gpt-4.1
  stages:
    story_architect:
      model: gpt-4.1-mini
    reader_experience:
      model: gpt-4.1-mini
    editor_agent:
      model: gpt-4.1
```

Gợi ý:

- Dùng model rẻ hơn cho `story_architect` và `reader_experience`.
- Dùng model mạnh hơn cho `writing_agent`, `editor_agent`, `coach_agent`, `future_self`.
- Dùng temperature thấp hơn cho `editor_agent` vì nhiệm vụ là can thiệp tối thiểu, không sáng tạo quá tay.

## Learning Loop

Sau khi bạn tạo `final_blog.md` hoặc `production_blog.md`, chạy learning loop:

```powershell
python engine/run_workflow.py --learn-from-run runs/<ten-lan-chay>
```

Nếu production file nằm ngoài run folder:

```powershell
python engine/run_workflow.py --learn-from-run runs/<ten-lan-chay> --production path/to/production_blog.md
```

Chạy offline, không cần API:

```powershell
python engine/run_workflow.py --learn-from-run runs/<ten-lan-chay> --offline-learning
```

Learning loop dùng full artifact từ `step_outputs.json`, không dùng handoff rút gọn. Điều này giữ đủ evidence để học từ các chỉnh sửa thật của người viết.

## Input Tốt

Input tốt không cần bóng bẩy. Nó nên có:

- một khoảnh khắc thật
- một cảm giác chưa hiểu hết
- một mâu thuẫn bên trong
- một kết luận ban đầu mà bạn còn nghi ngờ
- một câu hỏi bạn vẫn đang mang theo

Workflow hoạt động tốt nhất khi AI được phép ở lại với sự chưa rõ trước khi cố tạo insight.
