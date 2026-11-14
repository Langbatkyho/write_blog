# Kế hoạch tổng thể: Mindful Blog Workflow trên Claude Artifact

> **Trạng thái:** DRAFT — chờ người dùng duyệt baseline và các quyết định D1–D7.
> **Ngày lập:** 2026-11-14
> **Mã dự án:** ART
> **Cơ sở:** phân tích khả năng chuyển đổi Antigravity Bridge sang Claude Artifact và đề xuất phân bổ model Claude theo stage (phiên làm việc 2026-11-14).
> **Tài liệu đã đọc theo `.agents/AGENTS.md` §10:** `docs/current_architecture.md`, `docs/workflow_analysis.md`, `.agents/agentic-workflow-architect/SKILL.md` và các reference.

---

## 1. Baseline

### 1.1. Mục tiêu sản phẩm

Chạy hai workflow viết blog (`deep`, `moment`) với các style hiện có hoàn toàn trên claude.ai qua một Artifact:

- Mỗi stage là **một lần gọi `sample` độc lập**: ngữ cảnh chỉ gồm những gì `context_policy` cho phép, nên `reader_experience` đọc mù thật.
- Mỗi stage dùng **model và effort Claude riêng**.
- Thay Antigravity Bridge (`--client antigravity`) cho việc viết hằng ngày: không cần Python, IDE, `runs/temp_llm/`.
- **Repo vẫn là nguồn chân lý** cho flow, skill, bảng model. Artifact chỉ dùng bản bundle được build và kiểm tra từ repo.

### 1.2. Người dùng

| Vai trò | Ai | Quyền trên Artifact |
|---|---|---|
| Owner / người viết chính | Chủ repo | Editor: chạy workflow, xem lịch sử của mình, publish lại |
| Người viết khác (tùy chọn, D2) | Thành viên trong tổ chức, ví dụ chủ style `va-natural` | Contributor: chạy workflow bằng quota của chính họ, dữ liệu riêng |

### 1.3. Nền tảng và năng lực runtime

- claude.ai Artifact, runtime contract `0.2.96`.
- Bắt buộc: `sample` (gọi Claude), `db` (lưu run), `user` (định danh người xem), `downloads` (xuất file).
- Tùy chọn: `mcp` với kết nối Gmail (tạo bản nháp email), `dictation` (đọc ghi chú thô).

### 1.4. Ngoài phạm vi

- **Voice Lab:** `.agents/AGENTS.md` §4 và skill kiến trúc quy định Gemini-only (D1).
- Trình sửa style trong Artifact. Style vẫn sửa trong repo rồi build lại bundle (D3).
- Định tuyến nhiều nhà cung cấp (OpenAI, Gemini, DeepSeek), Resend, Supabase, Render, Google OAuth.
- Thay đổi Streamlit UI.
- `engine/claude_client.py` cho Python. Đây là track riêng, không phải dependency của kế hoạch này.

### 1.5. Dữ liệu và quyền

- Ghi chú thô và bài viết là dữ liệu cá nhân. Run lưu tại `data/users/<id>/runs/...`, riêng tư kể cả với owner của Artifact.
- Không lưu secret trong trang hoặc `db`.
- Không sao chép run cũ trong `runs/` hay `web_runs/` vào Artifact.
- Artifact không bao giờ ghi vào `runs/`. File zip xuất ra chỉ vào `runs/` khi người dùng tự tay giải nén.

### 1.6. Constraint

| Constraint | Hệ quả thiết kế |
|---|---|
| `sample` tiêu quota Claude của người xem; lần gọi đầu hỏi consent | Chỉ gọi khi người dùng bấm; có chế độ chạy từng bước |
| Không được tự động thử lại trong vòng lặp | Stage lỗi dừng workflow; có nút "Chạy lại stage" |
| Model được chỉ định có thể bị hạ xuống `modelTier` mà không báo lỗi | Ghi `modelApplied`/`modelTierApplied` vào telemetry, hiện cảnh báo |
| Kết quả được lưu đệm 5 phút | Mọi lần gọi stage dùng `cache: false` |
| Input tối đa 256 KiB mỗi lần gọi | Prompt thực tế khoảng 10–20 KB; có kiểm tra kích thước trước khi gọi |
| Mỗi document `db` tối đa 256 KiB | Mỗi stage là một document riêng |
| Không chỉnh được temperature hay max tokens | Chỉ điều khiển bằng model, effort và luật trong skill YAML |

### 1.7. Quyết định cần duyệt

| Mã | Quyết định | Đề xuất mặc định | Ảnh hưởng nếu đổi |
|---|---|---|---|
| D1 | Voice Lab có đưa vào Artifact không | **Không**, giữ Gemini-only | Cần sửa AGENTS.md và thêm chặng mới |
| D2 | Ai dùng Artifact | Chỉ owner tới hết ART-4; mở cho người viết khác từ ART-5 | Quy tắc truy cập `db`, kiểm thử quyền |
| D3 | Nguồn chân lý của skill | Bundle build từ repo; Artifact chỉ đọc | Nếu sửa trong Artifact: cần trình sửa và đồng bộ ngược, rủi ro trùng nguồn |
| D4 | Bảng model mặc định | Phương án "Cân bằng" đã đề xuất; chốt lại sau ART-6.2 | Chỉ đổi dữ liệu trong khối `claude:` |
| D5 | Có làm Gmail và dictation không | Có, ở chặng tùy chọn T7 | Bỏ ART-7.x |
| D6 | Vị trí mã nguồn Artifact | Thư mục `artifact/` trong repo | — |
| D7 | Model được chỉ định có chạy được trên gói của người dùng không | Chưa có bằng chứng → **ART-0 kiểm chứng** | Nếu không: dùng `modelTier` thay vì tên model |

---

## 2. Kiến trúc mục tiêu

```text
REPO (nguồn chân lý)                     BUILD (Python)                     CLAUDE.AI ARTIFACT
flow/write_blog.yaml        ─┐
flow/write_moment_blog.yaml ─┤
skills/{deep,moment}/<style>/*.yaml ─┼─► artifact/build_bundle.py ──► bundle.json ─┐
skills/editorial_learning.yaml ─┤        (kiểm tra bằng contract              │
engine/config.example.yaml  ─┘         Python, fail-closed)                  ├─► dist/index.html
  └─ khối claude: (model/effort)                                             │      │
artifact/src/*.js (core thuần) ─────────────────────────────────────────────┘      │
                                                                                     ├─ sample: 1 lần gọi/stage
                                                                                     ├─ db: data/users/<id>/runs/...
                                                                                     ├─ downloads: .md / .zip
                                                                                     └─ mcp Gmail (tùy chọn)
```

### 2.1. Module JS (giữ ranh giới trách nhiệm như phía Python, theo §11)

| Module | Tương ứng Python | Trách nhiệm duy nhất |
|---|---|---|
| `contracts.js` | `workflow_contracts.py` | Kiểm tra cấu trúc bundle khi tải; fail-closed |
| `context.js` | `parser.build_context_package` | Chọn handoff/artifact theo `context_policy` |
| `prompt.js` | `workflow_context.build_step_prompt`, `learning.build_*_prompt` | Dựng prompt, giống từng byte với Python |
| `parser.js` | `parser.parse_stage_response(strict=True)` | Tách `## Artifact` / `## Handoff`, đếm từ |
| `artifacts.js` | `workflow_artifacts.derive_artifact_file_contents` | Tách Edited Blog / Edit Log |
| `orchestrator.js` | `workflow_execution.run_workflow` | Điều phối thứ tự; bỏ qua stage khi stage phụ thuộc lỗi; dừng khi lỗi; telemetry |
| `client_sample.js` / `client_fake.js` | `LlmClient`, `build_dry_run_response` | Gọi Claude / phản hồi giả xác định cho test (được inject vào orchestrator) |
| `repository_memory.js` / `repository_db.js` | `workflow_persistence.RunRepository` | Lưu run; Run ID chống va chạm (timestamp + UUID) |
| `export.js` | — | Xuất zip có bố cục tương thích `runs/` |
| `ui/*.js` | `ui/views`, `ui/controllers` | Hiển thị và tương tác; không chứa prompt hay parser |

`artifact/build_html.py` gộp JS và `bundle.json` thành một file `dist/index.html`. Thư viện ngoài duy nhất dự kiến là JSZip, tải từ cdnjs với phiên bản cố định.

### 2.2. Định tuyến model

- Khối `claude:` trong `engine/config.example.yaml` là nguồn duy nhất. Builder đưa nó vào `bundle.models`.
- Mỗi stage gọi `sample(prompt, { model, effort, modelTier, cache: false, signal, onText })`.
- `modelTier` lấy theo hạng của model, để khi bị hạ vẫn ở hạng tương đương: Haiku → `quick`, Sonnet → `default`, Opus → `complex`.
- Telemetry mỗi stage ghi: `model_requested`, `model_applied`, `tier_applied`, `effort`, `duration_ms`, `truncated`, `status`, `error`.
- Metadata run ghi `run_source: "artifact"`, `persisted`, `api_called` theo đúng nhánh thực thi (AGENTS §5).

---

## 3. Bản đồ output

| Mã | Output | Bên làm → bên nhận | Bằng chứng | Phụ thuộc |
|---|---|---|---|---|
| O-01 | Báo cáo spike runtime: model nào chạy được, độ trễ, `truncated` với bài ~1800 từ tiếng Việt, consent, doc `db` | Agent → Owner | Báo cáo kèm số liệu đo trên claude.ai | — |
| O-02 | Khối `claude:` trong `engine/config.example.yaml` | Agent → builder | Diff và test kiểm tra schema | O-01 |
| O-03 | `artifact/build_bundle.py` và `bundle.json` đã kiểm tra | Agent → core JS | pytest (tmp_path); bundle tất định (hash) | O-02 |
| O-04 | Golden fixtures: prompt do Python sinh cho các fixture | Agent → test JS | File golden kèm script sinh lại | O-03 |
| O-05 | Core JS (`contracts`, `context`, `prompt`, `parser`, `artifacts`, `orchestrator`, `client_fake`) | Agent → UI | Kết quả `node --test` | O-03, O-04 |
| O-06 | Bộ test JS: so khớp prompt với golden; các case parser như `tests/test_handoff_parser.py` | Agent → Reviewer | Log test | O-04, O-05 |
| O-07 | Artifact MVP đã publish: chạy deep/moment, mọi style, streaming, Stop, chạy lại stage, tải `.md` | Agent → Owner | URL Artifact; run thật do Owner thực hiện | O-05 |
| O-08 | Test render UI bằng Playwright, `window.claude` giả lập | Agent → Reviewer | Log test và ảnh chụp màn hình | O-07 |
| O-09 | Lưu run vào `db`, xem lịch sử, chạy tiếp stage lỗi | Agent → Owner | `ArtifactData list`; kiểm tra quyền ở cấp thấp hơn | O-07 |
| O-10 | Xuất zip tương thích `runs/` | Agent → engine Python | Test: `load_step_outputs_from_run` đọc được zip (tmp_path) | O-09 |
| O-11 | Khung sửa bản cuối + learning loop (`editorial_learning`, `workflow_tuning`, diff offline) | Agent → Owner | So khớp golden learning prompt; run thật | O-09, O-04 |
| O-12 | Bảng chỉnh model/effort theo stage, 3 preset, chế độ A/B mù | Agent → Owner | Test render; một phiên A/B thử | O-09 |
| O-13 | ADR chốt bảng model, cập nhật khối `claude:` | Owner + Agent | Kết quả A/B trên 3–5 input thật | O-12 |
| O-14 | Tạo bản nháp Gmail từ bài cuối (tùy chọn) | Agent → Owner | Bản nháp xuất hiện trong Gmail của người dùng | O-07 |
| O-15 | Nhập ghi chú thô bằng giọng nói (tùy chọn) | Agent → Owner | Thử trên Chrome/desktop app | O-07 |

Không có vòng phụ thuộc. Đường găng: O-01 → O-02 → O-03 → O-04 → O-05 → O-07 → O-09 → O-11 → O-12 → O-13.

---

## 4. Roadmap

Txx là thứ tự tương đối, chưa gắn ngày. Nguồn lực: một agent build (Claude Code) và người dùng (duyệt, nghiệm thu, chạy thật). Mỗi chặng chỉ có một việc chính.

| Chặng | PRD | Increment dùng / kiểm chứng được khi đóng | Loại |
|---|---|---|---|
| T0 | ART-0 | Biết chắc model nào gọi được, độ trễ và giới hạn độ dài thực tế | Spike |
| T1 | ART-1 | Bundle đã kiểm tra, sinh ra từ repo; golden fixtures | Build (repo) |
| T2 | ART-2 | Core engine JS chạy được với client giả, khớp từng byte với Python | Build (JS) |
| T3 | ART-3 | **MVP dùng được:** viết blog trên claude.ai, tải bài về | Vertical slice |
| T4 | ART-4 | Lịch sử run, chạy tiếp stage lỗi, xuất zip | Build |
| T5 | ART-5 | Sửa bản cuối và learning loop trên Artifact | Build |
| T6a | ART-6.1 | Công cụ chỉnh model và A/B mù | Build |
| T6b | ART-6.2 | Bảng model được chốt bằng dữ liệu thật | **Chờ bên ngoài:** người dùng viết thật nhiều ngày |
| T7 | ART-7.1, ART-7.2 | Gmail draft, dictation (tùy chọn) | Build, chạy cùng lúc với thời gian chờ của T6b |

---

## 5. PRD Registry

| PRD | Tên | Chặng | Owner tổng hợp | Người nghiệm thu | Trạng thái |
|---|---|---|---|---|---|
| ART-0 | Spike runtime `sample` | T0 | Agent | Owner | DRAFT |
| ART-1 | Bundle và contract từ repo | T1 | Agent | Owner | DRAFT |
| ART-2 | Core engine JS | T2 | Agent | Owner | DRAFT |
| ART-3 | MVP vertical slice | T3 | Agent | Owner | DRAFT |
| ART-4 | Lưu trữ, lịch sử, xuất file | T4 | Agent | Owner | DRAFT |
| ART-5 | Bản cuối và learning loop | T5 | Agent | Owner | DRAFT |
| ART-6.1 | Cấu hình model và công cụ A/B | T6a | Agent | Owner | DRAFT |
| ART-6.2 | Đánh giá A/B và chốt bảng model | T6b | Owner | Owner | DRAFT |
| ART-7.1 | Bản nháp Gmail (tùy chọn) | T7 | Agent | Owner | DRAFT |
| ART-7.2 | Nhập bằng giọng nói (tùy chọn) | T7 | Agent | Owner | DRAFT |

---

## 6. Chi tiết PRD

### ART-0 — Spike runtime `sample`

- **Mục tiêu:** có bằng chứng cho D7 và các giả định thời gian, độ dài trước khi viết code sản phẩm.
- **User story:** Là owner, tôi muốn biết các model Claude dự định dùng có chạy trong Artifact trên gói của tôi không, chạy mất bao lâu, có bị cắt bài dài không.
- **Phạm vi:**
  - Một Artifact nháp nhỏ gọi `sample` với Haiku 5.5, Sonnet 5.5, Opus 5.5 ở các effort khác nhau.
  - Dùng một prompt cỡ thật: prompt `writing_agent` dựng từ fixture.
  - Thử ghi và đọc một document `db` khoảng 50 KB.
- **Ngoài phạm vi:** UI sản phẩm, engine.
- **Output:** O-01.
- **Dependency:** không có. Cần người dùng đồng ý tiêu quota cho khoảng 6–9 lần gọi thật (AGENTS §4).
- **AC:**
  - ART-0-AC1: bảng cho mỗi model × effort: `modelApplied`, `modelTierApplied`, thời gian tới chữ đầu tiên, tổng thời gian, `truncated`, số từ đầu ra.
  - ART-0-AC2: kết luận rõ cho D7: dùng tên model, hay chỉ dùng `modelTier`.
  - ART-0-AC3: xác nhận một bài khoảng 1800 từ tiếng Việt kèm handoff không bị `truncated`. Nếu bị cắt: đề xuất cách xử lý.
- **Bằng chứng:** báo cáo `docs/` kèm số liệu; URL Artifact nháp.
- **Điều kiện đóng:** Owner duyệt báo cáo; D7 được chốt.
- **Issue dự kiến:** 1.

### ART-1 — Bundle và contract từ repo

- **Mục tiêu:** một bundle JSON duy nhất, tất định, được kiểm tra bằng chính contract Python.
- **User story:** Là người bảo trì, tôi sửa skill hoặc model trong repo, chạy một lệnh build và được bundle hợp lệ. Nếu skill sai contract, build dừng lại.
- **Phạm vi:**
  - Thêm khối `claude:` vào `engine/config.example.yaml`, dùng giá trị phương án Cân bằng đã hiệu chỉnh theo O-01.
  - `artifact/build_bundle.py`:
    - Dùng lại `WorkflowDefinition.from_dict`, `validate_style_contract`, `resolve_step_skill_path`, `validate_step_skill_contract`, `validate_workflow_artifact_set`.
    - Không suy luận lại tên file trong JS (Bài học 14).
    - Kiểm tra khối `claude:`: model ID và effort hợp lệ; mọi stage của hai flow đều có cấu hình.
  - Golden fixtures (O-04): script Python sinh prompt mẫu từ fixture `examples/`, ghi vào thư mục tạm hoặc `artifact/tests/golden/`.
- **Ngoài phạm vi:** `engine/claude_client.py`.
- **Output:** O-02, O-03, O-04.
- **Dependency:** O-01 (bảng model khả dụng).
- **AC:**
  - ART-1-AC1: build hai lần cho cùng một hash.
  - ART-1-AC2: skill thiếu file, slug sai, hoặc stage thiếu cấu hình model → build fail kèm thông báo rõ ràng (test).
  - ART-1-AC3: bundle chứa đủ 2 flow, các style hợp lệ của từng mode, `editorial_learning`, bảng model.
  - ART-1-AC4: toàn bộ regression test hiện có vẫn pass; `runs/` không đổi trước và sau.
- **Quyền dữ liệu:** chỉ đọc `skills/`, `flow/`; ghi vào `artifact/` và thư mục tạm.
- **NFR:** không gọi API.
- **Bằng chứng:** log pytest, hash bundle, ảnh chụp trạng thái `runs/` trước và sau.
- **Điều kiện đóng:** AC pass; cập nhật `docs/current_architecture.md` và `docs/changelog.md` về khối `claude:` và thư mục `artifact/`.
- **Issue dự kiến:** 2 (config + builder; golden fixtures).

### ART-2 — Core engine JS

- **Mục tiêu:** core JS thuần, chạy được với client giả và khớp hành vi với Python.
- **Phạm vi:** các module ở mục 2.1, trừ `client_sample`, `repository_db`, `export`, `ui`; test bằng `node --test` (Node 22 có sẵn).
- **Output:** O-05, O-06.
- **Dependency:** O-03, O-04.
- **AC:**
  - ART-2-AC1: `buildStepPrompt` khớp từng byte với golden cho mọi stage × mode × một style mỗi mode.
  - ART-2-AC2: parser chặt pass các case tương đương `tests/test_handoff_parser.py`: thiếu section, sai thứ tự, rỗng, có lời dẫn trước `## Artifact`.
  - ART-2-AC3: orchestrator với client giả:
    - Chạy đủ 7 hoặc 6 stage.
    - Stage lỗi → dừng; nếu `stop_on_error: false` thì bỏ qua đúng các stage phụ thuộc.
    - Telemetry đầy đủ; `api_called: false` khi dùng client giả.
  - ART-2-AC4: tách Edited Blog / Edit Log giống Python trên cùng input.
- **NFR:** core không truy cập DOM hay `window.claude` (inject từ biên, Bài học 6).
- **Bằng chứng:** log `node --test`.
- **Điều kiện đóng:** AC pass; không có module nào chưa có consumer.
- **Issue dự kiến:** 2 (context/prompt/parser/artifacts; orchestrator/client giả).

### ART-3 — MVP vertical slice

- **Mục tiêu:** increment đầu tiên dùng được: viết blog trên claude.ai.
- **User story:** Là người viết, tôi dán ghi chú thô, chọn chế độ và style, bấm Chạy. Tôi xem từng stage hiện ra khi đang sinh, rồi tải bài cuối về.
- **Phạm vi:**
  - Form nhập: `title`, `raw_notes`, `optional_context`, `target_reader`, `desired_length`. Form dựng thành markdown đúng định dạng `examples/*_input_template.md`.
  - Chọn mode và style từ bundle.
  - Hai chế độ chạy: liền một mạch, hoặc từng bước bấm "Tiếp".
  - `client_sample.js` với model/effort theo bảng; hiện chữ "Đang suy nghĩ…"; nút Stop.
  - Mỗi stage hiển thị Artifact và Handoff, model yêu cầu so với model thực chạy, và cảnh báo khi bị hạ.
  - Nút "Chạy lại stage" (`cache: false`).
  - Bài cuối kèm số từ; tải `.md`.
  - Bản nháp của form lưu `localStorage`, bọc trong try/catch.
  - Xử lý lỗi theo `code`: `not_granted` (ẩn tính năng), `rate_limited` (dừng, báo), `cancelled`.
- **Ngoài phạm vi:** lưu `db`, learning, A/B.
- **Output:** O-07, O-08.
- **Dependency:** O-05.
- **AC:**
  - ART-3-AC1: test Playwright với `window.claude` giả: render ở 390px và desktop, sáng/tối, đủ các trạng thái chờ / đang chạy / lỗi / xong.
  - ART-3-AC2 (runtime thật, Owner chạy): một run `moment/va-natural` và một run `deep/reflective` hoàn tất trên claude.ai.
  - ART-3-AC3: telemetry hiển thị đúng model thực chạy cho từng stage.
  - ART-3-AC4: bản giả lập không được dùng để tuyên bố runtime đạt; AC2 bắt buộc là run thật.
- **Quyền dữ liệu:** không lưu ngoài trình duyệt.
- **NFR:** trang tải được khi không có `sample` (hiện thông báo, không vỡ trang); không cuộn ngang ở 390px.
- **Bằng chứng:** URL, ảnh chụp, log Playwright, biên bản run thật.
- **Điều kiện đóng:** Owner nghiệm thu AC2.
- **Issue dự kiến:** 2 (client + orchestrator binding; UI).

### ART-4 — Lưu trữ, lịch sử, xuất file

- **Mục tiêu:** run không mất khi đóng tab; mở lại, chạy tiếp, xuất được.
- **Phạm vi:**
  - `repository_db.js`:
    - Lưu tại `data/users/<id>/runs/{runId}` (metadata) và `.../runs/{runId}/stages/{stageId}` (artifact, handoff, file đã tách, telemetry).
    - Checkpoint sau mỗi stage hoàn tất.
  - Danh sách lịch sử, mở lại run, "Chạy tiếp từ stage lỗi".
  - `export.js`: zip gồm `input.md`, `metadata.json`, `step_outputs.json`, các file artifact/handoff theo tên trong flow, `run_log.md`, `handoff_log.md`.
- **Output:** O-09, O-10.
- **Dependency:** O-07.
- **AC:**
  - ART-4-AC1: sau khi publish, `ArtifactData list` thấy run của owner. Đọc với `as_level` thấp hơn không thấy dữ liệu riêng.
  - ART-4-AC2: test Python (tmp_path) giải nén zip mẫu và `load_step_outputs_from_run` đọc đúng các stage hoàn tất.
  - ART-4-AC3: Run ID không trùng khi tạo liên tiếp; không ghi đè run đã có.
  - ART-4-AC4: tải dữ liệu có hẹn giờ 10 giây và trạng thái lỗi rõ ràng; `db` rỗng vẫn hiển thị đúng.
- **Quyền dữ liệu:** chỉ dùng đường dẫn riêng; không có collection dùng chung.
- **Bằng chứng:** kết quả `ArtifactData`, log pytest, ảnh chụp.
- **Điều kiện đóng:** AC pass; Owner mở lại được một run cũ.
- **Issue dự kiến:** 2 (repository + lịch sử; export + test tương thích).

### ART-5 — Bản cuối và learning loop

- **Mục tiêu:** khép vòng "AI nháp → người viết sửa → hệ thống học" ngay trên Artifact.
- **Phạm vi:**
  - Khung soạn `production_blog.md` khởi tạo từ bản AI; lưu vào run.
  - Hai stage learning với model/effort theo khối `claude.learning`.
    - Prompt port từ `build_learning_prompt` / `build_tuning_prompt`, có kiểm tra ngân sách token.
    - Dùng **artifact đầy đủ**, không dùng handoff (Bài học 4).
  - Diff offline: báo cáo không cần gọi Claude, port từ `build_offline_learning_report`.
  - Xuất `editorial_learning_report.md` và `workflow_tuning_suggestions.md`, gắn nhãn mode/style (Bài học 13).
  - Không tự áp dụng thay đổi vào skill (D3).
- **Output:** O-11.
- **Dependency:** O-09, O-04 (golden learning prompt bổ sung).
- **AC:**
  - ART-5-AC1: learning prompt khớp golden Python.
  - ART-5-AC2: run learning thật hoàn tất trên một run đã có production.
  - ART-5-AC3: thiếu production → nút learning bị khóa kèm giải thích; diff offline vẫn chạy.
  - ART-5-AC4 (nếu D2 mở cho người viết khác): người dùng thứ hai không đọc được run của owner.
- **Bằng chứng:** log test, báo cáo mẫu, kết quả kiểm tra quyền.
- **Điều kiện đóng:** Owner nghiệm thu một vòng học đầy đủ.
- **Issue dự kiến:** 2 (bản cuối + diff offline; hai stage learning).

### ART-6.1 — Cấu hình model và công cụ A/B

- **Mục tiêu:** đổi model/effort theo stage không cần build lại; so sánh hai cấu hình một cách mù.
- **Phạm vi:**
  - Bảng cấu hình theo stage: ghi đè cho từng người xem, mặc định từ bundle.
  - 3 preset: Chất lượng tối đa / Cân bằng / Nhanh.
  - Chế độ A/B: cùng một input chạy hai cấu hình; hiện hai bài cuối A/B đã xáo trộn; người dùng chọn; ghi kết quả, cấu hình, số từ, thời gian vào `db`.
  - Mỗi lựa chọn kèm chênh lệch so với `production_blog.md` nếu có.
- **Output:** O-12.
- **Dependency:** O-09.
- **AC:**
  - ART-6.1-AC1: ghi đè chỉ ảnh hưởng người xem đó; nút "Khôi phục mặc định" hoạt động.
  - ART-6.1-AC2: thứ tự A/B được xáo và ẩn tới khi chọn xong.
  - ART-6.1-AC3: một phiên A/B thử hoàn tất và được lưu.
- **Điều kiện đóng:** Owner nghiệm thu AC3.
- **Issue dự kiến:** 1.

### ART-6.2 — Đánh giá A/B và chốt bảng model

- **Mục tiêu:** chốt D4 bằng dữ liệu thật, không theo phỏng đoán.
- **Phạm vi:**
  - Owner chạy A/B trên 3–5 input thật (không dùng `examples/`), so sánh mốc "Opus 5.5 ở mọi stage, effort medium" với phương án Cân bằng.
  - Agent tổng hợp kết quả, viết ADR, cập nhật khối `claude:`, build lại, publish lại.
- **Loại:** **chờ bên ngoài** (người dùng viết thật trong nhiều ngày). Không chặn ART-7.x.
- **Output:** O-13.
- **Dependency:** O-12.
- **AC:**
  - ART-6.2-AC1: có ít nhất 3 cặp A/B có lựa chọn.
  - ART-6.2-AC2: ADR ghi bảng cuối cùng, lý do, các stage đã đổi.
  - ART-6.2-AC3: bundle mới được publish lên đúng URL cũ.
- **Nếu chậm:** Registry ghi PENDING ("chờ dữ liệu A/B"); Artifact vẫn dùng bảng Cân bằng.
- **Issue dự kiến:** 1.

### ART-7.1 — Bản nháp Gmail (tùy chọn)

- **Phạm vi:**
  - Nút "Tạo bản nháp email" dùng `mcp` với kết nối Gmail, chỉ khai báo tool tạo bản nháp. Tên tham số lấy từ schema thật của tool, không đoán.
  - Chỉ tạo bản nháp, không tự gửi. Người dùng bấm xác nhận trước khi tạo.
- **Dependency:** O-07.
- **AC:**
  - ART-7.1-AC1: bản nháp xuất hiện trong Gmail của người dùng.
  - ART-7.1-AC2: người xem chưa kết nối Gmail thì nút bị ẩn hoặc vô hiệu.
- **Issue dự kiến:** 1.

### ART-7.2 — Nhập bằng giọng nói (tùy chọn)

- **Phạm vi:** nút micro cho ô `raw_notes` dùng `dictation`; ẩn khi không hỗ trợ.
- **Dependency:** O-07.
- **AC:** ART-7.2-AC1: đọc ghi chú tiếng Việt và chèn vào ô trên Chrome hoặc desktop app; trình duyệt khác vẫn gõ phím bình thường.
- **Issue dự kiến:** 1.

---

## 7. Chiến lược kiểm thử theo độ trưởng thành

| Chặng | Lớp kiểm thử | Không được làm |
|---|---|---|
| T0 | Đo trực tiếp trên claude.ai, có sự đồng ý của người dùng | Tuyên bố kiến trúc đạt chỉ dựa trên spike |
| T1 | pytest với `tmp_path`, không gọi API, chụp `runs/` trước và sau | Dùng `config.example.yaml` có `log_dir: runs` để chạy `run_workflow()` |
| T2 | `node --test`, client giả, so khớp golden | Gọi `sample` thật |
| T3 | Playwright với `window.claude` giả để kiểm tra UI; **run thật trên claude.ai** để nghiệm thu runtime | Dùng mock để tuyên bố runtime đạt |
| T4 | `ArtifactData` list/query (kể cả đọc ở cấp quyền thấp hơn); pytest kiểm tra tương thích zip | Ghi zip thử vào `runs/` |
| T5–T6 | Golden learning prompt; run thật do Owner chạy | Tự động thử lại khi lỗi |
| T7 | Thử thủ công trên đúng nền tảng hỗ trợ | — |

Sau mỗi chặng có code, báo cáo theo AGENTS §9: số test pass/fail, có gọi API không, artifact nằm ở đâu, `runs/` có đổi không.

---

## 8. Rủi ro và bài học lịch sử (AGENTS §10)

| Mã | Rủi ro | Bài học liên quan | Giảm thiểu |
|---|---|---|---|
| R1 | Prompt JS lệch dần prompt Python | 3, 11 | Golden fixtures sinh từ Python; test so khớp chạy trong CI cục bộ trước mỗi lần build |
| R2 | Ánh xạ slug ↔ tên file sai | 14 | Builder dùng resolver Python; JS không suy luận lại |
| R3 | Gộp artifact và handoff, tốn token | 1, 2 | Giữ nguyên contract hai section; `context_policy` lấy từ bundle |
| R4 | Learning chỉ dùng handoff | 4 | ART-5 bắt buộc dùng artifact đầy đủ; có AC kiểm tra |
| R5 | Model bị hạ mà không báo, lệch chất lượng | — | Telemetry yêu cầu vs thực chạy; cảnh báo trên UI |
| R6 | Bài bị cắt (`truncated`) | — | ART-0 đo trước; nếu thiếu handoff → stage lỗi; nếu đủ hai section nhưng bị cắt → cảnh báo |
| R7 | Lưu đệm trả lại kết quả cũ khi chạy lại | — | Luôn `cache: false` cho stage |
| R8 | Hết quota, `rate_limited`, người xem từ chối consent | 7 | Chạy từng bước; dừng khi lỗi; không tự thử lại |
| R9 | Lộ dữ liệu cá nhân qua `db` dùng chung | 17 | Chỉ dùng `data/users/<id>/`; kiểm tra quyền ở cấp thấp hơn |
| R10 | Trùng nguồn chân lý skill/model | 11 (AGENTS §11) | D3: Artifact chỉ đọc bundle; đề xuất từ learning được xuất ra để commit vào repo |
| R11 | Vi phạm quy tắc Voice Lab Gemini-only | Skill kiến trúc | D1: ngoài phạm vi |
| R12 | Kiến thức giữa các mode nhiễm chéo nhau | 13 | Báo cáo learning gắn nhãn mode/style |
| R13 | Prompt injection trong ghi chú thô hoặc dữ liệu đọc từ Gmail | — | Giữ câu "dữ liệu không đáng tin" trong prompt learning; Gmail chỉ tạo bản nháp, có xác nhận |
| R14 | Vá client ở tầng thấp | 6 | Client inject vào orchestrator; core không biết `window.claude` |
| R15 | Run test lẫn vào dữ liệu nghiệp vụ | 17 | Artifact không ghi `runs/`; test dùng `tmp_path`; metadata `run_source` phân biệt |

---

## 9. Tự kiểm tra trước khi xin duyệt

- [x] Mỗi PRD thuộc đúng một chặng và có một điều kiện đóng.
- [x] Không có output nào được bàn giao trước khi PRD của nó đóng.
- [x] Không có vòng phụ thuộc; dependency ghi bằng mã output.
- [x] Thời gian chờ bên ngoài (A/B thật) tách thành ART-6.2, không trộn vào ART-6.1.
- [x] Không AC nào đòi môi trường chưa tồn tại ở thời điểm đó: runtime thật chỉ xuất hiện từ ART-3.
- [x] Không ai làm hai việc chính cùng lúc: T7 chạy trong thời gian chờ của Owner ở T6b.
- [ ] D1–D7 chưa được duyệt → toàn bộ PRD giữ ở DRAFT.

## 10. Bước tiếp theo

1. Người dùng duyệt baseline và D1–D7. ART-0 cần thêm sự đồng ý tiêu quota cho các lần gọi thật.
2. Chuyển PRD sang BACKLOG; tạo Issue khi người dùng yêu cầu.
3. Bắt đầu ART-0.
