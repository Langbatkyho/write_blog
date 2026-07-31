# Kiến trúc dự án hiện tại (Mindful Blog Workflow Engine - Guided Style Voice Lab & Multi-Style V6.0)

> **Tham chiếu kế hoạch phê duyệt:**  
> - [docs/2026-07-25-multi-editable-style-upgrade-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-25-multi-editable-style-upgrade-plan-final.md)  
> - [docs/2026-07-26-guided-style-voice-lab-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-26-guided-style-voice-lab-plan-final.md)  
> - [docs/2026-07-27-voice-lab-refactor-plan-final.md](file:///D:/Nghi%C3%AAn%20c%E1%BB%A9u%20AI/write_blog/docs/2026-07-27-voice-lab-refactor-plan-final.md)
>
> **Cập nhật ngày:** 2026-07-28

Dự án `mindful_writing_os` đã được nâng cấp toàn diện lên **Kiến Trúc Quản Trị Phong Cách & Voice Lab V6.0 (Guided Style Voice Lab & Multi-Style Engine)** trên nền tảng **Hệ Hai Writing Modes**:

1. **`deep_blog_mode` (`--mode deep`)**: Dành cho bài viết dài (1000-1500 từ), phản tư sâu, chuyển hóa trải nghiệm nội tâm qua 7 Agent (`story_architect`, `reflection_engine`, `writing_agent`, `reader_experience`, `editor_agent`, `coach_agent`, `future_self`).
2. **`moment_blog_mode` (`--mode moment`)**: Dành cho bài viết ngắn (300-600 từ), ghi nhận khoảnh khắc hiện tại qua giác quan & thời tiết bên trong với 6 Agent (`sensory_capture`, `inner_weather`, `cosmic_signal_reader`, `moment_writer`, `breath_editor`, `gentle_witness`).

---

## 1. Cấu trúc thư mục (Directory Structure)

```text
write_blog/
├── AGENTS.md                  # Bắt buộc mọi agent đọc .agents/AGENTS.md
├── .agents/
│   ├── AGENTS.md              # RULES về dữ liệu, API, test, I/O và hoàn tất
│   └── agentic-workflow-architect/
│       ├── SKILL.md           # Quy trình refactor contract-first
│       └── references/        # Invariants, patterns và checklist
├── engine/
│   ├── __init__.py           # Package definition
│   ├── utils.py              # Xử lý đường dẫn và đọc/ghi YAML, text
│   ├── parser.py             # Phân tích nội dung Artifact/Handoff, đếm tokens
│   ├── openai_client.py      # Giao tiếp OpenAI API, retry loops, bảo mật key
│   ├── gemini_client.py      # [NEW V6.0] Giao tiếp Gemini API (gemini-3.5-flash) trực tiếp
│   ├── client_router.py      # Định tuyến stage-to-client mapping (--client-map, openai/antigravity/gemini)
│   ├── antigravity_bridge.py # Giao tiếp qua file-bridge cho Local Model Quota
│   ├── learning.py           # Quản lý prompts & offline/online learning phân tách theo mode
│   ├── style_contracts.py    # Contract metadata/slug/style namespace
│   ├── style_repository.py   # Transaction repository cho style CRUD
│   ├── style_manager.py      # Style service, validation và alias wiring
│   ├── workflow.py           # Facade/orchestrator workflow
│   ├── workflow_contracts.py # Runtime contracts và kiểu dữ liệu workflow
│   ├── workflow_execution.py # Thực thi stage qua LLM client được inject
│   ├── workflow_persistence.py # Run directory, metadata và checkpoint
│   ├── workflow_context.py   # Context assembly Artifact/Handoff
│   ├── workflow_resolution.py # Mode/style/flow/skill resolution
│   ├── workflow_artifacts.py # Chuẩn hóa và ghi artifact
│   ├── workflow_learning.py  # Điều phối learning loop
│   ├── run_workflow.py       # CLI Entrypoint hỗ trợ Fail-Fast `--mode`, `--style`, `--client`
│   └── voice_lab/            # Guided Style Voice Lab schema v2
│       ├── __init__.py       # Voice Lab package init
│       ├── models.py         # Schema v2 nested, result/error/history models
│       ├── prompts.py        # Prompt builders + Gemini JSON response schemas
│       ├── parser.py         # Parse strict JSON, xác minh exact quote, tính confidence
│       ├── analyzer.py       # Adaptive single/multi-pass Gemini analysis
│       ├── interview.py      # Compatibility facade cho interview/calibration
│       ├── interview_routing.py # Chọn dimension yếu, tối đa 3 câu/vòng
│       ├── profile_patch.py  # Propose/apply interview patch có xác nhận
│       ├── calibration.py    # Blind A/B, provenance và cập nhật profile
│       ├── compiler.py       # Full-template overlay qua Adjacency Matrix
│       ├── overrides.py      # Three-way diff, conflict explicit
│       ├── migration.py      # Reader v1 -> v2, legacy incomplete state
│       ├── archive.py        # Archive v2 + checksum + safe import
│       └── publisher.py      # Staging/validate/backup/atomic rollback service
├── ui/                       # [UPGRADED V6.0] Streamlit Local UI Experience
│   ├── app.py                # Composition root và render 4 tab
│   ├── state.py              # Session-state contract và reset theo mode
│   ├── controllers/
│   │   ├── workflow_controller.py # Use case workflow/preview
│   │   └── voice_lab_controller.py # Use case Voice Lab/compile/publish
│   ├── views/
│   │   ├── gallery.py       # Style Gallery
│   │   ├── voice_lab.py     # Studio và wizard 5 bước
│   │   ├── editor.py        # YAML editor
│   │   └── workbench.py     # Preview và layer inspector
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
│   │   ├── va-natural/       # [NEW V6.0] Style tùy biến Vân Anh Natural (Moment Mode) + profile_dna.json
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
│   └── test_voice_lab.py         # Schema/prompt/compiler/archive/publish contract tests
├── docs/                     # Tài liệu thiết kế, kế hoạch, review & changelog
├── README.md
└── mindful_writing_os.md
```

---

## 2. Các Cải tiến Kiến trúc Cốt lõi (V6.0 Core Architectural ADRs)

### 2.1. Gói Quản Trị Giọng Văn 5 Bước (Guided Style Voice Lab Package)
Module `engine/voice_lab/` cung cấp quy trình khép kín giúp người dùng kiến tạo phong cách viết riêng từ mẫu văn bản thực tế:
- **Bước 1: Nạp Mẫu & Phân Tích**: Đóng gói sample không tin cậy bằng JSON, định tuyến single/multi-pass bằng estimator bảo thủ cho Unicode và gọi trực tiếp Gemini API với structured JSON output. Estimator là guardrail offline, không phải số token thanh toán chính xác.
- **Bước 2: DNA & Evidence Review**: Trích xuất 12 chiều thành `DimensionProfile`; quote phải khớp nguyên văn với sample. Evidence sai bị reject để audit và không tham gia confidence.
- **Bước 3: Guided Interview**: Chọn tối đa 3 chiều yếu nhất, tạo `ProfilePatch`; chỉ áp dụng sau khi người dùng duyệt và lưu provenance.
- **Bước 4: Blind A/B Calibration**: Chỉ thay một dimension, ẩn mapping A/B; lựa chọn trực tiếp của người dùng có thể nâng confidence tới `0.95` và phải lưu before/after cùng provenance trong history.
- **Bước 5: Biên Dịch & Xuất Bản An Toàn (Compiler & Publish Safety Pipeline)**: 
  - **Adjacency Matrix (`DIMENSION_AGENTS`)**: Ánh xạ từ các chiều DNA sang đúng danh sách Agent chịu trách nhiệm trong từng Mode.
  - **Full-template overlay**: Base style được chọn rõ ràng; compiler giữ nguyên toàn bộ role/tasks/input/output/workflow và chỉ thêm vùng `voice_lab_style`.
  - **Invariant Contract**: Canonical IR lưu base hash, invariant snapshot và effective skill đầy đủ.

Voice Lab hiện chỉ dùng `engine/gemini_client.py`; không gọi OpenAI API hoặc Antigravity Bridge. Router đa client vẫn tồn tại cho workflow bên ngoài Voice Lab.

#### Schema và Data Contract v2

- `VoiceDNA` giữ 12 dimension cố định; mỗi dimension là `DimensionProfile(description, strength, confidence, do, avoid, examples, evidence_ids, source)`.
- `EvidenceClaim` lưu `sample_id`, `exact_quote`, offsets, stance và trạng thái active/rejected.
- `StyleProfile` tách `schema_version` khỏi `revision`, lưu warning, interview/calibration history và trạng thái phân tích.
- `CanonicalIR` chỉ giữ contract chính thức: invariant snapshot, style overlays và `effective_skill` đầy đủ. Ba contract runtime được chuẩn hóa thành object; scalar legacy được bọc bằng `{"reference": ...}`.
- Toàn bộ runtime model Voice Lab từ chối field dư; `prompt`/`style_rules` phẳng không còn là nguồn dữ liệu song song.
- Reader v1 là migration adapter tách biệt; contract v2 không tự migrate hoặc âm thầm bỏ field. Legacy thiếu evidence luôn ở trạng thái `incomplete_legacy_data` và bị chặn publish.

### 2.2. Quy Trình Xuất Bản An Toàn 4 Tầng (Publish Safety Pipeline)
Khi nhấn Publish một phong cách mới trong Voice Lab, hệ thống thực thi 4 bước bảo vệ giao dịch:
1. **Staging**: Ghi full effective skills, profile v2 và metadata vào thư mục giao dịch riêng cùng filesystem.
2. **Contract Validation**: Kiểm tra YAML schema, required agents, workflow references và invariant snapshot.
3. **Backup**: Tạo bản sao lưu dự phòng nếu style đã tồn tại.
4. **Atomic Replace & Rollback**: Tráo đổi thư mục bằng `os.replace`; lỗi giữa giao dịch sẽ phục hồi tombstone và dọn staging. Nếu chính rollback thất bại, hệ thống giữ tombstone, trả `PublishRollbackError` cùng đường dẫn phục hồi thủ công.

### 2.3. Hỗ Trợ Local Model Quota qua Antigravity Bridge
Hệ thống hỗ trợ chạy workflow hoàn toàn bằng **Local Model Quota** thông qua Antigravity Bridge (`--client antigravity`):
- `antigravity_bridge.py` tạo luồng trao đổi prompt/response dạng file tại `runs/temp_llm/`.
- AI Agent đóng vai trò xử lý ngôn ngữ nội tại, đọc file `prompt_<stage>_<ts>.txt` và ghi đè `response_<stage>_<ts>.txt` theo đúng quy ước, giúp người dùng chạy thử nghiệm thực tế mà không tốn API Key ngoài.

### 2.4. Đa Client Router & Động cơ Gemini API (`engine/gemini_client.py`)
- Bổ sung module `gemini_client.py` hỗ trợ gọi trực tiếp Gemini API với model mặc định `gemini-3.5-flash`.
- Nâng cấp **Chế độ tư duy High (`thinking_budget: int = 1024`)** mặc định cho `gemini-3.5-flash`, cho phép AI suy nghĩ sâu hơn khi trích xuất Voice DNA và biên dịch kỹ năng.
- Triển khai **Dual Strategy**: Ưu tiên sử dụng official SDK `google.genai` (`types.ThinkingConfig(thinking_budget=1024)`) và tự động fallback sang REST API payload (`"thinkingConfig": {"thinkingBudget": 1024}`) khi có sự cố SDK.
- Xử lý mã hóa chuẩn Unicode/ASCII (`[OK]`) chống lỗi console encoding trên môi trường Windows.
- Router `client_router.py` cho phép định tuyến linh hoạt giữa 3 Client provider: `openai`, `antigravity`, và `gemini`.

### 2.5. Trích xuất & Lưu trữ Trung gian Dữ liệu Voice Lab (`profile_dna.json`)
- Nâng cấp quy trình xuất bản (Step 5 Publish Pipeline trong `ui/app.py`): Mỗi khi xuất bản một style mới từ Voice Lab Studio, hệ thống tự động ghi file `profile_dna.json` vào thư mục `skills/<mode>/<slug>/`.
- File `profile_dna.json` cố định vĩnh viễn cấu trúc Voice DNA (12 chiều), danh sách Evidence Claims (quotes, confidence), câu trả lời phỏng vấn (Interview answers), và lựa chọn A/B Calibration để phục vụ cho công tác kiểm duyệt và audit sau này.

### 2.6. Trạng thái kiểm chứng

- 124/124 regression test toàn dự án pass; 4 subtest parser strict pass.
- UI acceptance bao phủ 4 tab, đổi mode hai chiều, Workbench template/custom in-memory và Voice Lab đến Compile Review bằng fake.
- Parser production khóa duy nhất `## Artifact`/`## Handoff` theo đúng thứ tự nhưng vẫn giữ H2 nội bộ của bài blog.
- Gemini router descriptor và request dùng cùng model global/per-stage.
- Style save/create/rename validate toàn staging theo Flow–Skill contract; alias collision bị chặn trước replace.
- Voice Lab v2 fail-closed; v1 chỉ được đọc qua migration adapter. `profile_dna.json` hiện có đã được kiểm tra tương thích ở chế độ chỉ đọc.
- Deep và Moment mode đều được test compile/publish đủ required agents.
- Streamlit AppTest và kiểm tra trực quan không có exception/overflow; style widget được namespace theo mode.
- `compileall` và `git diff --check` đạt.

### 2.7. Lớp quản trị Agentic

- `AGENTS.md` ở repository root bắt buộc mọi agent đọc `.agents/AGENTS.md`.
- RULES phân loại `runs/` là dữ liệu nghiệp vụ: run cũ chỉ đọc; workflow thật được tạo run mới collision-safe; test/dry-run phải dùng vùng tạm.
- `runs/temp_llm/` là ngoại lệ tương thích có giới hạn cho file bridge của chính lần chạy hiện tại.
- Test mặc định dùng fake/mock, không gọi API thật; Voice Lab chỉ dùng Gemini API.
- Skill `agentic-workflow-architect` bắt buộc cho thay đổi workflow, engine, contract, provider, compiler, publisher và rollback.
- Trình tự refactor chuẩn: contract → engine → prompt → integration → verification.

---

## 3. Giao Diện Người Dùng Streamlit Local UI (`ui/app.py`)

Giao diện Dark Theme được mở rộng tích hợp toàn bộ Trình quản lý Voice Lab 5 bước:
1. **📚 Style Gallery**: Quản lý danh sách card style, phân biệt `SYSTEM STYLE` và `CUSTOM STYLE`.
2. **🎨 Style Studio & Voice Lab Wizard**: Tích hợp 5 bước thiết kế giọng văn trực quan (Nạp mẫu -> Evidence -> Interview -> Blind Calibration -> Publish Safety Pipeline).
3. **💻 YAML Code Editor**: Soạn thảo live YAML prompt kèm bộ kiểm duyệt Group-Based Validator.
4. **🧪 Live Workbench & Layer Inspector**: Soạn và so sánh trực tiếp Canonical IR (tri thức nguyên bản) với Effective YAML (kỹ năng được biên dịch), mô phỏng định tuyến mà không tốn Quota.

---

## 4. Trạng thái Refactor P0–P2

- **P0 — Modularization:** `ui/app.py` chỉ còn composition/render; state, view và controller được tách. `workflow.py` trở thành facade; execution, persistence, context, resolution, artifact và learning có module riêng. `interview.py` trở thành compatibility facade cho routing, profile patch và calibration.
- **P1 — Contract hardening:** UI acceptance, parser strict, Gemini stage model telemetry, style transaction, alias namespace và migration v1/v2 fail-closed.
- **P2 — Audit hardening:** bỏ compiler legacy fallback, token guardrail Unicode, calibration provenance và lỗi rollback thứ cấp có cấu trúc.
- Sau mỗi gate, workflow vẫn sử dụng được; regression cuối đạt **124/124 test + 4 parser subtest**, không gọi API thật và không thay đổi `runs/`.


### 3. UI Layer (Streamlit)
- ui/app.py: Điều hướng chính, chọn chế độ (Blog vs Voice Lab).
- ui/views/blog_workflow.py: Giao diện 4 bước (Nhập -> Kết quả -> Sửa -> Học hỏi) dùng st.session_state.
- ui/controllers/workflow_controller.py: Kết nối giao diện với core Engine, đảm bảo cách ly State.
