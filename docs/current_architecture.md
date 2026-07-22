# Kiến trúc dự án hiện tại (Mindful Blog Workflow Engine)

> **Tham chiếu kế hoạch phê duyệt:** [docs/2026-07-22-mindful_writing_os-two-writing-modes-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-22-mindful_writing_os-two-writing-modes-final.md)  
> **Cập nhật ngày:** 2026-07-22

Dự án `mindful_writing_os` đã được nâng cấp toàn diện từ một hệ thống phản tư đơn sang **Hệ Hai Writing Modes** (Dual Writing Modes Architecture):

1. **`deep_blog_mode` (`--mode deep`)**: Dành cho bài viết dài (1000-1500 từ), phản tư sâu, chuyển hóa trải nghiệm nội tâm.
2. **`moment_blog_mode` (`--mode moment`)**: Dành cho bài viết ngắn (300-600 từ), hiện tại, trực giác, ghi nhận tín hiệu giác quan & thời tiết bên trong mà không ép bài học hay triết lý hóa.

---

## 1. Cấu trúc thư mục (Directory Structure)

```text
write_blog/
├── engine/
│   ├── __init__.py           # Package definition
│   ├── utils.py              # Xử lý đường dẫn và đọc/ghi YAML, text
│   ├── parser.py             # Phân tích nội dung Artifact/Handoff, đếm tokens
│   ├── openai_client.py      # Giao tiếp OpenAI API, retry loops, bảo mật key
│   ├── client_router.py      # Định tuyến stage-to-client mapping (--client-map)
│   ├── antigravity_bridge.py # Giao tiếp qua file-bridge cho Local Model Quota
│   ├── learning.py           # Quản lý prompts & offline/online learning phân tách theo mode
│   ├── workflow.py           # Workflow Orchestrator (Dynamic skill resolution & flow routing)
│   └── run_workflow.py       # CLI Entrypoint hỗ trợ `--mode`, `--style`, `--client`, `--learn-from-run`
├── examples/
│   ├── blog_input_template.md        # Input mẫu cho Deep Blog Mode
│   └── moment_blog_input_template.md # Input mẫu cho Moment Blog Mode
├── flow/
│   ├── write_blog.yaml       # Quy trình Deep Blog Mode (7 bước)
│   └── write_moment_blog.yaml# Quy trình Moment Blog Mode (6 bước)
├── skills/
│   ├── reflective/           # 7 Deep mode skills (Story, Reflection, Writing, Reader, Editor, Coach, Future Self)
│   ├── provocative/          # 7 Deep mode skills gai góc
│   ├── moment/
│   │   └── reflective/       # 6 Moment mode skills:
│   │       ├── sensory_capture.yaml     # Ghi nhận cảnh & thân thể
│   │       ├── inner_weather.yaml       # Gọi tên thời tiết bên trong
│   │       ├── cosmic_signal_reader.yaml# Tín hiệu trực giác nhỏ
│   │       ├── moment_writer.yaml       # Nháp ngắn (300-600 từ)
│   │       ├── breath_editor.yaml       # Cắt gọt nhẹ nhàng (Breath edit)
│   │       └── gentle_witness.yaml      # Xác nhận độ trong & tươi mới
│   └── editorial_learning.yaml# Skill phân tích học tập biên tập
├── tests/
│   ├── test_handoff_parser.py
│   ├── test_openai_client.py
│   ├── test_workflow_contract.py
│   ├── test_antigravity_bridge.py
│   ├── test_client_router.py
│   └── test_moment_blog_mode.py  # Test suite toàn diện cho Dual Writing Modes
├── docs/                     # Tài liệu thiết kế, kế hoạch, review & changelog
├── README.md
└── mindful_writing_os.md
```

---

## 2. Luồng làm việc & Phân vai Agent theo Mode

### 2.1. Deep Blog Mode (`--mode deep`)

Luồng xử lý 7 bước:
```text
story_architect -> reflection_engine -> writing_agent -> reader_experience -> editor_agent -> coach_agent -> future_self -> Human Writer
```

| Agent | Trung thành với | Câu hỏi chính |
| :--- | :--- | :--- |
| `story_architect` | Câu chuyện | Điều gì thật sự đã xảy ra? |
| `reflection_engine` | Nhận thức | Điều gì thay đổi bên trong người viết? |
| `writing_agent` | Giọng người viết | Nếu có đủ thời gian, tác giả sẽ kể chuyện này thế nào? |
| `reader_experience` | Trải nghiệm đọc | Độc giả lần đầu đã cảm thấy gì? |
| `editor_agent` | Kết nối | Cần thay đổi tối thiểu điều gì để giảm ma sát? |
| `coach_agent` | Sự phát triển | Người viết còn chưa nhìn thấy điều gì? |
| `future_self` | Con người tương lai | 5 năm nữa, tác giả còn muốn đứng tên bài này không? |

### 2.2. Moment Blog Mode (`--mode moment`)

Luồng xử lý 6 bước:
```text
sensory_capture -> inner_weather -> cosmic_signal_reader -> moment_writer -> breath_editor -> gentle_witness -> Human Writer
```

| Agent | Trung thành với | Câu hỏi chính |
| :--- | :--- | :--- |
| `sensory_capture` | Giác quan | Khoảnh khắc này đang hiện ra qua giác quan như thế nào? |
| `inner_weather` | Trạng thái | Thời tiết bên trong người viết ngay lúc này là gì? |
| `cosmic_signal_reader` | Trực giác | Khoảnh khắc này đang thì thầm điều gì với người viết? |
| `moment_writer` | Năng lượng hiện tại | Nếu chỉ giữ lại khoảnh khắc này, bài viết cần nói điều gì? |
| `breath_editor` | Độ trong | Cần bỏ hoặc làm nhẹ điều gì để khoảnh khắc được tự cất tiếng? |
| `gentle_witness` | Sự thật | Bài viết còn là một khoảnh khắc sống hay đã bị kéo thành bài học? |

---

## 3. Quy Tắc Routing & Skill Resolution

- **Flow Routing (`resolve_workflow_file`)**: Tự động chuyển hướng tới `flow/write_moment_blog.yaml` nếu `mode == "moment"`, hoặc `flow/write_blog.yaml` nếu `mode == "deep"`.
- **Skill Path Resolution (`resolve_step_skill_path`)**: Ưu tiên tìm skill theo cấu trúc `skills/moment/{style}/{skill_name}` khi ở Moment mode, hoặc `skills/{style}/{skill_name}` khi ở Deep mode.
- **Style-Mode Fallback**: Nếu người dùng chọn `--mode moment --style provocative`, CLI sẽ cảnh báo và tự động fallback về `reflective` do Moment mode không hỗ trợ provocative.

---

## 4. Mode-Separated Learning Loop

Vòng lặp học tập (Learning Loop) phân tách hoàn toàn dữ liệu tri thức theo mode:
- Kết quả chạy lưu tại: `runs/<run_dir>/learning/<mode>/<timestamp>/`
- Tên báo cáo mẫu tri thức:
  - Deep mode: `deep_blog_patterns.md`
  - Moment mode: `moment_blog_patterns.md`
- Đảm bảo tri thức bài viết ngắn (khoảnh khắc) không làm ô nhiễm quy tắc biên tập bài viết dài (phản tư sâu).
