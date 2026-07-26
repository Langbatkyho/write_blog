# Kiến trúc dự án hiện tại (Mindful Blog Workflow Engine - Guided Style Voice Lab & Multi-Style V6.0)

> **Tham chiếu kế hoạch phê duyệt:**  
> - [docs/2026-07-25-multi-editable-style-upgrade-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-25-multi-editable-style-upgrade-plan-final.md)  
> - [docs/2026-07-26-guided-style-voice-lab-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-26-guided-style-voice-lab-plan-final.md)  
> **Cập nhật ngày:** 2026-07-26

Dự án `mindful_writing_os` đã được nâng cấp toàn diện lên **Kiến Trúc Quản Trị Phong Cách & Voice Lab V6.0 (Guided Style Voice Lab & Multi-Style Engine)** trên nền tảng **Hệ Hai Writing Modes**:

1. **`deep_blog_mode` (`--mode deep`)**: Dành cho bài viết dài (1000-1500 từ), phản tư sâu, chuyển hóa trải nghiệm nội tâm qua 7 Agent (`story_architect`, `reflection_engine`, `writing_agent`, `reader_experience`, `editor_agent`, `coach_agent`, `future_self`).
2. **`moment_blog_mode` (`--mode moment`)**: Dành cho bài viết ngắn (300-600 từ), ghi nhận khoảnh khắc hiện tại qua giác quan & thời tiết bên trong với 6 Agent (`sensory_capture`, `inner_weather`, `cosmic_signal_reader`, `moment_writer`, `breath_editor`, `gentle_witness`).

---

## 1. Cấu trúc thư mục (Directory Structure)

```text
write_blog/
├── engine/
│   ├── __init__.py           # Package definition
│   ├── utils.py              # Xử lý đường dẫn và đọc/ghi YAML, text
│   ├── parser.py             # Phân tích nội dung Artifact/Handoff, đếm tokens
│   ├── openai_client.py      # Giao tiếp OpenAI API, retry loops, bảo mật key
│   ├── gemini_client.py      # [NEW V6.0] Giao tiếp Gemini API (gemini-3.5-flash) trực tiếp
│   ├── client_router.py      # Định tuyến stage-to-client mapping (--client-map, openai/antigravity/gemini)
│   ├── antigravity_bridge.py # Giao tiếp qua file-bridge cho Local Model Quota
│   ├── learning.py           # Quản lý prompts & offline/online learning phân tách theo mode
│   ├── style_manager.py      # [NEW V5.0] Style Service CRUD, Group-based Validator, Alias Wiring
│   ├── workflow.py           # Workflow Orchestrator (Strict Discovery resolution & flow routing)
│   ├── run_workflow.py       # CLI Entrypoint hỗ trợ Fail-Fast `--mode`, `--style`, `--client`
│   └── voice_lab/            # [NEW V6.0] Guided Style Voice Lab V1 Package
│       ├── __init__.py       # Voice Lab package init
│       ├── models.py         # Pydantic Schemas (StyleProfile, VoiceDNA, EvidenceClaim, CanonicalIR)
│       ├── analyzer.py       # Phân tích văn bản mẫu ra Voice DNA & Claims (100% tiếng Việt)
│       ├── interview.py      # Phỏng vấn bổ sung & Hiệu chỉnh A/B Blind Calibration (100% tiếng Việt)
│       ├── compiler.py       # Biên dịch Canonical IR thành Effective YAMLs qua Adjacency Matrix
│       ├── overrides.py      # 3-Way Diff Merge Engine cho chèn đè thủ công
│       ├── migration.py      # Legacy Style Importer (chuyển đổi YAML cũ sang StyleProfile)
│       └── archive.py        # Export/Import gói `.voice-style.zip` với SHA-256 integrity
├── ui/                       # [UPGRADED V6.0] Streamlit Local UI Experience
│   ├── app.py                # Giao diện quản trị 4 Tabs + 5-Step Guided Voice Lab Wizard & Publish Pipeline
│   └── styles.css            # Dark Theme CSS (Slate Gray, Warm Gold, Electric Cyan)
├── examples/
│   ├── blog_input_template.md        # Input mẫu cho Deep Blog Mode
│   ├── moment_blog_input_template.md # Input mẫu cho Moment Blog Mode
│   └── moment_1.md                   # Input thực tế test Moment Mode
├── flow/
│   ├── write_blog.yaml       # Quy trình Deep Blog Mode (7 bước)
│   └── write_moment_blog.yaml# Quy trình Moment Blog Mode (6 bước)
├── skills/                   # [UPGRADED V6.0] Phân cấp chuẩn 2 chiều Mode x Style
│   ├── deep/
│   │   ├── reflective/       # 7 Deep mode skills + style_meta.yaml (is_protected: true)
│   │   └── provocative/      # 7 Deep mode skills + style_meta.yaml (is_protected: true)
│   ├── moment/
│   │   ├── reflective/       # 6 Moment mode skills + style_meta.yaml (is_protected: true)
│   │   ├── va-natural/       # [NEW V6.0] Style tùy biến Vân Anh Natural (Moment Mode)
│   │   └── minh-hom-hinh/    # [NEW V6.0] Style tùy biến Minh Hóm Hỉnh (Moment Mode)
│   └── editorial_learning.yaml # System Exception (bất biến, không thuộc namespace style)
├── tests/
│   ├── test_handoff_parser.py
│   ├── test_openai_client.py
│   ├── test_workflow_contract.py # Assert cấu trúc skills/deep/...
│   ├── test_antigravity_bridge.py
│   ├── test_client_router.py
│   ├── test_moment_blog_mode.py  # Test suite Dual Writing Modes
│   ├── test_style_manager.py     # Test suite CRUD, Validator, Alias, Rollback
│   └── test_voice_lab.py         # [NEW V6.0] Contract Tests ma trận kề & Zero-cost Smoke Test
├── docs/                     # Tài liệu thiết kế, kế hoạch, review & changelog
├── README.md
└── mindful_writing_os.md
```

---

## 2. Các Cải tiến Kiến trúc Cốt lõi (V6.0 Core Architectural ADRs)

### 2.1. Gói Quản Trị Giọng Văn 5 Bước (Guided Style Voice Lab Package)
Module `engine/voice_lab/` cung cấp quy trình khép kín giúp người dùng kiến tạo phong cách viết riêng từ mẫu văn bản thực tế:
- **Bước 1: Nạp Mẫu & Phân Tích (Sample & Quota Estimator)**: Tiếp nhận văn bản mẫu, tính toán ước lượng token quota, bảo mật tránh Prompt Injection qua `sanitize_sample`.
- **Bước 2: Phân Tích DNA & Bằng Chứng (Voice DNA & Evidence Claims)**: Trích xuất 12 chiều đặc trưng văn phong (`tone`, `vocabulary`, `sentence_structure`, `rhythm`, `formatting`, `humor`, `sensory_density`, `emoji`, `metaphor_density`, `emotional_depth`, `pacing`, `perspective`) kèm bằng chứng dẫn chứng 100% bằng tiếng Việt.
- **Bước 3: Phỏng Vấn Bổ Sung (Guided Interview)**: Tự động phát hiện các chiều có độ tin cậy thấp hoặc thiếu bằng chứng để đưa ra câu hỏi phỏng vấn chiều sâu bằng tiếng Việt (`DIMENSION_VI`).
- **Bước 4: Hiệu Chỉnh A/B Mù (Blind A/B Calibration)**: Sinh 2 đoạn văn mẫu tương phản (Bản A đậm chất, Bản B tiết chế) hoàn toàn bằng tiếng Việt để người dùng thử nghiệm mù và chọn lựa.
- **Bước 5: Biên Dịch & Xuất Bản An Toàn (Compiler & Publish Safety Pipeline)**: 
  - **Adjacency Matrix (`DIMENSION_AGENTS`)**: Ánh xạ từ các chiều DNA sang đúng danh sách Agent chịu trách nhiệm trong từng Mode.
  - **Filename Mapping (`AGENT_FILENAME_MAP`)**: Đảm bảo tên file skill xuất ra trùng khớp tuyệt đối với hợp đồng quy trình Flow (`story_architect.yaml`, `writing_agent.yaml`, `sensory_capture.yaml`, `cosmic_signal_reader.yaml`...).

### 2.2. Quy Trình Xuất Bản An Toàn 4 Tầng (Publish Safety Pipeline)
Khi nhấn Publish một phong cách mới trong Voice Lab, hệ thống thực thi 4 bước bảo vệ giao dịch:
1. **Staging**: Ghi các file skill vừa biên dịch vào thư mục tạm `skills/<mode>/<slug>.staging/`.
2. **Contract Validation**: Gọi `validate_style_contract` kiểm tra trực tiếp nội dung staging, đảm bảo không thiếu bất kỳ file skill bắt buộc nào.
3. **Backup**: Tạo bản sao lưu dự phòng nếu style đã tồn tại.
4. **Atomic Replace & Rollback**: Tráo đổi thư mục nguyên tử (`os.replace`). Nếu gặp bất kỳ lỗi nào, hệ thống tự động hoàn tác (Rollback) về trạng thái cũ và báo lỗi minh bạch.

### 2.3. Hỗ Trợ Local Model Quota qua Antigravity Bridge
Hệ thống hỗ trợ chạy workflow hoàn toàn bằng **Local Model Quota** thông qua Antigravity Bridge (`--client antigravity`):
- `antigravity_bridge.py` tạo luồng trao đổi prompt/response dạng file tại `runs/temp_llm/`.
- AI Agent đóng vai trò xử lý ngôn ngữ nội tại, đọc file `prompt_<stage>_<ts>.txt` và ghi đè `response_<stage>_<ts>.txt` theo đúng quy ước, giúp người dùng chạy thử nghiệm thực tế mà không tốn API Key ngoài.

### 2.4. Đa Client Router & Động cơ Gemini API (`engine/gemini_client.py`)
- Bổ sung module `gemini_client.py` hỗ trợ gọi trực tiếp Gemini API với model mặc định `gemini-3.5-flash`.
- Router `client_router.py` cho phép định tuyến linh hoạt giữa 3 Client provider: `openai`, `antigravity`, và `gemini`.

---

## 3. Giao Diện Người Dùng Streamlit Local UI (`ui/app.py`)

Giao diện Dark Theme được mở rộng tích hợp toàn bộ Trình quản lý Voice Lab 5 bước:
1. **📚 Style Gallery**: Quản lý danh sách card style, phân biệt `SYSTEM STYLE` và `CUSTOM STYLE`.
2. **🎨 Style Studio & Voice Lab Wizard**: Tích hợp 5 bước thiết kế giọng văn trực quan (Nạp mẫu -> Evidence -> Interview -> Blind Calibration -> Publish Safety Pipeline).
3. **💻 YAML Code Editor**: Soạn thảo live YAML prompt kèm bộ kiểm duyệt Group-Based Validator.
4. **🧪 Live Workbench & Layer Inspector**: Soạn và so sánh trực tiếp Canonical IR (tri thức nguyên bản) với Effective YAML (kỹ năng được biên dịch), mô phỏng định tuyến mà không tốn Quota.
