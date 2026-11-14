# Kế hoạch tổng thể: Mindful Blog Workflow trên Claude Artifact

> **Trạng thái:** FINAL (bản 2) — quyết định D1–D7 đã được người dùng chốt ngày 2026-11-14.
> Các PRD ở trạng thái BACKLOG, trừ ART-8.4 giữ DRAFT cho tới khi người dùng xác nhận cách làm rõ D3a (mục 1.7).
> **Mã dự án:** ART
> **Tài liệu đã đọc theo `.agents/AGENTS.md` §10:** `docs/current_architecture.md`, `docs/workflow_analysis.md`, `.agents/agentic-workflow-architect/SKILL.md` và các reference.

## Lịch sử thay đổi

| Bản | Ngày | Thay đổi |
|---|---|---|
| 1 | 2026-11-14 | Bản nháp đầu tiên; D1–D7 còn mở |
| 2 | 2026-11-14 | Chốt D1–D7:<br>• Thêm track Voice Lab (ART-8.1 → 8.4)<br>• Thêm phạm vi team (D2)<br>• Gmail chuyển thành ART-7, bỏ dictation<br>• Model gọi theo tên<br>• Thêm bước cập nhật quy tắc Voice Lab vào ART-1<br>• Làm rõ D3 thành D3a |

---

## 1. Baseline

### 1.1. Mục tiêu sản phẩm

Một Artifact trên claude.ai cho team cùng tổ chức Claude Team. Artifact này:

1. **Chạy hai workflow viết blog** (`deep`, `moment`) với mọi style.
   - Mỗi stage là một lần gọi `sample` độc lập, ngữ cảnh chỉ gồm những gì `context_policy` cho phép.
   - Mỗi stage dùng model Claude được gọi **theo tên**, kèm effort riêng.
2. **Lưu lịch sử run**, cho sửa bản cuối, chạy learning loop, và gửi kết quả qua Gmail.
3. **Có Voice Lab đủ 5 bước**, chạy bằng Claude, để mỗi người tạo style giọng văn của riêng mình.

Repo vẫn là nguồn chân lý cho flow, skill hệ thống, bảng model và các hằng số Voice Lab. Artifact dùng một bundle được build và kiểm tra từ repo.

### 1.2. Người dùng (D2)

| Vai trò | Ai | Mức chia sẻ trên Artifact | Ghi chú |
|---|---|---|---|
| Owner | Chủ repo | Editor (owner) | Duy nhất có quyền publish lại trang |
| Thành viên team | Đồng đội cùng tổ chức Claude Team, mỗi người có tài khoản riêng | **Contributor** (`interact`) | Bắt buộc Contributor mới ghi được dữ liệu, kể cả `data/users/<id>/` của chính họ. Viewer/Commenter không ghi được gì |

Hệ quả:

- Mỗi người tiêu quota Claude Team của chính mình.
- Mỗi người kết nối Gmail của chính mình.
- Run và hồ sơ giọng văn đang soạn là dữ liệu riêng; owner cũng không đọc được.

### 1.3. Nền tảng và năng lực runtime

claude.ai Artifact, runtime contract `0.2.96`.

| Capability | Dùng để |
|---|---|
| `sample` | Gọi Claude theo tên model cho workflow, learning, Voice Lab |
| `db` | Run riêng, hồ sơ Voice Lab riêng, thư viện style của team |
| `user` | Định danh người xem; tên tác giả trong thư viện style (scope `profile`) |
| `downloads` | Xuất `.md`/`.zip` |
| `mcp` | Kết nối Gmail: `create_draft`, `send_message` |

### 1.4. Ngoài phạm vi

- Nhập bằng giọng nói (`dictation`) (D5).
- Trình sửa YAML thô cho style hệ thống trong Artifact (D3).
- Định tuyến nhiều nhà cung cấp (OpenAI, Gemini, DeepSeek), Resend, Supabase, Render, Google OAuth.
- Thay đổi Streamlit UI và Voice Lab Python. **Voice Lab Python vẫn dùng Gemini.**
- `engine/claude_client.py` cho Python. Đây là track riêng, không phải dependency.

### 1.5. Dữ liệu và quyền

| Đường dẫn `db` | Nội dung | Đọc | Ghi |
|---|---|---|---|
| `data/users/<id>/runs/...` | Run, các stage, bản cuối, learning | Chính người đó | Chính người đó (Contributor+) |
| `data/users/<id>/voicelab/...` | Mẫu văn, hồ sơ giọng văn đang soạn, phỏng vấn, A/B | Chính người đó | Chính người đó |
| `data/users/<id>/settings` | Ghi đè model, người nhận email mặc định | Chính người đó | Chính người đó |
| `library/<authorId>/styles/<slug>/...` | Style đã publish lên thư viện team | Mọi Contributor+ | Tác giả; owner (admin) được dọn dẹp |

- Không lưu secret.
- Không sao chép run cũ trong `runs/` hay `web_runs/` vào Artifact.
- Artifact không ghi `runs/`.

### 1.6. Constraint

| Constraint | Hệ quả thiết kế |
|---|---|
| `sample` tiêu quota của người xem; lần gọi đầu hỏi consent | Chỉ gọi khi người dùng bấm; có chế độ chạy từng bước |
| Không được tự động thử lại trong vòng lặp | Dừng khi lỗi; nút "Chạy lại stage" |
| Model gọi theo tên vẫn có thể bị hạ xuống `modelTier` mà không báo lỗi (chính sách tổ chức, quá tải) | Ghi `modelApplied`/`modelTierApplied`; cảnh báo trên UI |
| `sample.json` chỉ parse JSON kiểu dễ dãi, không kiểm tra theo schema | Voice Lab tự kiểm tra bằng JSON Schema xuất từ Pydantic; sai thì fail-closed, không bịa dữ liệu |
| Kết quả được lưu đệm 5 phút | `cache: false` cho mọi lần gọi stage, Voice Lab và learning |
| Input tối đa 256 KiB mỗi lần gọi | Kiểm tra kích thước trước khi gọi; Voice Lab chia mẫu văn theo ngân sách byte |
| Mỗi document `db` tối đa 256 KiB; **không có transaction** | Mỗi stage một document; publish style theo mô hình "phiên bản bất biến + con trỏ" (mục 2.4) |
| Thành viên phải là Contributor mới ghi được | Kiểm tra `user.can("data.write")`; nếu thiếu quyền thì hiện hướng dẫn xin quyền |

### 1.7. Quyết định đã chốt

| Mã | Quyết định | Hệ quả trong kế hoạch |
|---|---|---|
| D1 | **Có** đưa Voice Lab vào Artifact | Track ART-8.1 → 8.4. Voice Lab trong Artifact dùng **Claude**. ART-1 cập nhật quy tắc Gemini-only (xem bên dưới) |
| D2 | Owner và đồng đội cùng tổ chức Claude Team | Chia sẻ Contributor; quy tắc truy cập `db` theo mục 1.5; kiểm tra quyền với tài khoản thứ hai |
| D3 | Skill sửa trong repo rồi build lại; Artifact chỉ đọc | Style hệ thống trong bundle là read-only và được bảo vệ |
| D4 | Bảng model phương án Cân bằng | Khối `claude:` (mục 2.3); chốt lại sau ART-6.2 |
| D5 | Có Gmail, không có dictation | ART-7 (Gmail); bỏ dictation |
| D6 | Mã nguồn ở `artifact/` trong repo | — |
| D7 | Gọi model theo tên | `sample({ model, effort, modelTier })`; ART-0 xác nhận trên tài khoản của owner và một đồng đội |

**Xung đột cần ghi nhận (AGENTS.md §1):**

- `.agents/AGENTS.md` §4, `SKILL.md` và `architecture-invariants.md` hiện quy định Voice Lab chỉ dùng Gemini.
- Quyết định D1 của người dùng là phê duyệt cụ thể cho một ngoại lệ có phạm vi:
  - **Voice Lab trong Claude Artifact dùng Claude qua `sample`.**
  - Voice Lab Python/Streamlit giữ nguyên Gemini-only.
- ART-1 phải sửa ba tài liệu này **trước khi** viết code Voice Lab.

**D3a — làm rõ để D1 và D3 cùng đứng được.** Voice Lab sinh ra style mới, trong khi D3 nói Artifact chỉ đọc skill. Hướng xử lý:

- Style hệ thống (trong repo, bundle) chỉ đọc và được bảo vệ, giống `is_protected`.
- Style do Voice Lab tạo nằm trong **thư viện team trên `db`**, chạy được ngay trong Artifact.
- Muốn đưa một style thành style hệ thống: xuất zip đúng định dạng `engine/voice_lab/archive.py`, commit vào repo, build lại bundle. Bản trong thư viện được đánh dấu "đã chuyển vào repo" và bị ẩn.
- Mỗi style chỉ có **một nơi ở** tại một thời điểm, nên không có hai nguồn chân lý.
- ART-8.4 giữ DRAFT tới khi người dùng xác nhận D3a.

---

## 2. Kiến trúc mục tiêu

```text
REPO (nguồn chân lý)                         BUILD (Python)                      CLAUDE.AI ARTIFACT
flow/*.yaml ─────────────────────────┐
skills/{deep,moment}/<style>/*.yaml ─┤
skills/editorial_learning.yaml ──────┼─► artifact/build_bundle.py ─► bundle.json ─┐
engine/config.example.yaml (claude:) ┤   kiểm tra bằng contract Python;           │
engine/voice_lab/{models,compiler,   ┤   xuất JSON Schema + hằng số Voice Lab     ├─► dist/index.html
  calibration,prompts}.py ───────────┘                                            │     │
artifact/src/*.js (core thuần) ──────────────────────────────────────────────────┘     │
                                   sample (theo tên model) ◄───────────────────────────┤
                                   db: data/users/<id>/… , library/<authorId>/… ◄──────┤
                                   downloads (.md/.zip) ◄──────────────────────────────┤
                                   mcp Gmail: create_draft / send_message ◄────────────┘
```

### 2.1. Module JS — workflow

| Module | Tương ứng Python | Trách nhiệm duy nhất |
|---|---|---|
| `contracts.js` | `workflow_contracts.py` | Kiểm tra bundle khi tải; fail-closed |
| `context.js` | `parser.build_context_package` | Chọn handoff/artifact theo `context_policy` |
| `prompt.js` | `workflow_context.build_step_prompt`, `learning.build_*_prompt` | Dựng prompt, giống từng byte với Python |
| `parser.js` | `parser.parse_stage_response(strict=True)` | Tách `## Artifact` / `## Handoff`; đếm từ |
| `artifacts.js` | `workflow_artifacts.derive_artifact_file_contents` | Tách Edited Blog / Edit Log |
| `orchestrator.js` | `workflow_execution.run_workflow` | Điều phối; bỏ qua stage khi stage phụ thuộc lỗi; dừng khi lỗi; telemetry |
| `client_sample.js` / `client_fake.js` | `LlmClient` | Gọi Claude / phản hồi giả cho test (được inject) |
| `repository_db.js` / `repository_memory.js` | `RunRepository` | Lưu run; Run ID = timestamp + UUID |
| `export.js` | — | Zip bố cục `runs/`; zip style theo định dạng `archive.py` |
| `gmail.js` | `email_sender.py` | Dựng nội dung và file đính kèm; gọi `create_draft` / `send_message` |

### 2.2. Module JS — Voice Lab

| Module | Tương ứng Python | Trách nhiệm duy nhất |
|---|---|---|
| `vl/schema.js` | `voice_lab/models.py` | Kiểm tra bằng JSON Schema xuất từ Pydantic (schema v2, fail-closed) |
| `vl/analyzer.js` | `analyzer.py`, `parser.py` | Chia mẫu văn theo ngân sách byte; gọi `sample.json`; kiểm tra quote khớp nguyên văn; gộp, khử trùng evidence |
| `vl/confidence.js` | `models.compute_profile_confidence` | Tính confidence bằng code, không dùng điểm LLM tự khai |
| `vl/interview.js` | `interview_routing.py`, `profile_patch.py` | Chọn tối đa 3 chiều yếu nhất; đề xuất `ProfilePatch`; chỉ áp dụng khi người dùng xác nhận |
| `vl/calibration.js` | `calibration.py` | A/B mù chỉ thay một chiều (90–165 từ); ẩn `shuffle_mapping`; cập nhật strength/examples/history |
| `vl/compiler.js` | `compiler.py`, `overrides.py` | Hàm tất định: chồng hồ sơ lên base template đầy đủ, giữ các trường bất biến; `DIMENSION_AGENTS`, `AGENT_FILENAME_MAP` lấy từ bundle |
| `vl/publisher.js` | `publisher.py` | Publish: phiên bản bất biến + con trỏ + rollback (mục 2.4) |
| `vl/prompts.js` | `prompts.py` | Prompt Voice Lab, giống từng byte với Python (golden) |

### 2.3. Bảng model (khối `claude:` — D4, D7)

| Nhóm | Stage | Model | Effort |
|---|---|---|---|
| Deep | `story_architect` | `claude-sonnet-5-5` | medium |
| | `reflection_engine` | `claude-opus-5-5` | high |
| | `writing_agent` | `claude-opus-5-5` | high |
| | `reader_experience` | `claude-sonnet-5-5` | low |
| | `editor_agent` | `claude-opus-5-5` | high |
| | `coach_agent` | `claude-opus-5-5` | medium |
| | `future_self` | `claude-sonnet-5-5` | high |
| Moment | `sensory_capture` | `claude-sonnet-5-5` | low |
| | `inner_weather` | `claude-sonnet-5-5` | medium |
| | `cosmic_signal_reader` | `claude-opus-5-5` | medium |
| | `moment_writer` | `claude-opus-5-5` | high |
| | `breath_editor` | `claude-opus-5-5` | medium |
| | `gentle_witness` | `claude-sonnet-5-5` | low |
| Learning | `editorial_learning` | `claude-opus-5-5` | high |
| | `workflow_tuning` | `claude-sonnet-5-5` | medium |
| Voice Lab (mới, đề xuất) | `vl_analysis` | `claude-opus-5-5` | high |
| | `vl_synthesis` | `claude-opus-5-5` | medium |
| | `vl_interview_patch` | `claude-sonnet-5-5` | medium |
| | `vl_calibration` | `claude-opus-5-5` | medium |

- `modelTier` khi bị hạ: Haiku → `quick`, Sonnet → `default`, Opus → `complex`.
- Telemetry mỗi lần gọi: `model_requested`, `model_applied`, `tier_applied`, `effort`, `duration_ms`, `truncated`, `status`, `error`.
- Metadata run: `run_source: "artifact"`, `persisted`, `api_called` theo đúng nhánh thực thi.

### 2.4. Publish style khi `db` không có transaction

Ánh xạ quy trình `staging → validate → backup → replace` của `publisher.py`:

1. **Staging:** ghi toàn bộ style (6 hoặc 7 skill đã compile, `style_meta`, hồ sơ v2) thành **một** document bất biến `library/<authorId>/styles/<slug>/versions/<versionId>`. Ước khoảng 50–80 KB, dưới giới hạn 256 KiB.
2. **Validate:** đọc lại document đó; kiểm tra schema, flow–skill contract, các trường bất biến, slug/alias duy nhất trong mode so với bundle và thư viện.
3. **Backup:** phiên bản trước vẫn được giữ nguyên, không xóa.
4. **Replace:** cập nhật **một** document con trỏ `library/<authorId>/styles/<slug>` → `currentVersion`. Ghi một document là nguyên tử.
5. **Rollback:** trỏ con trỏ về phiên bản trước.

Style hệ thống trong bundle không bao giờ bị ghi đè. Slug trùng với style hệ thống thì bị từ chối.

---

## 3. Bản đồ output

| Mã | Output | Bằng chứng | Phụ thuộc |
|---|---|---|---|
| O-01 | Báo cáo spike: model gọi theo tên có chạy cho owner và một đồng đội; độ trễ; bài dài có bị cắt; độ tin cậy của `sample.json`; giới hạn `db`; quyền Contributor | Số liệu đo trên claude.ai | — |
| O-02 | Quy tắc Voice Lab được cập nhật trong AGENTS.md §4, SKILL.md, architecture-invariants.md | Diff tài liệu | D1 |
| O-03 | Khối `claude:` trong `engine/config.example.yaml` | Diff + test schema | O-01 |
| O-04 | `artifact/build_bundle.py` → `bundle.json` (flow, skill, bảng model, JSON Schema Voice Lab, hằng số, base template) | pytest (tmp_path); hash tất định | O-02, O-03 |
| O-05 | Golden fixtures: prompt workflow, learning, Voice Lab; kết quả compile do Python sinh | Script sinh lại + file golden | O-04 |
| O-06 | Core JS workflow + test `node --test` | Log test | O-04, O-05 |
| O-07 | Artifact MVP đã publish (chạy workflow, streaming, Stop, chạy lại stage, tải `.md`) | URL; run thật | O-06 |
| O-08 | Test render UI bằng Playwright, `window.claude` giả lập | Log + ảnh | O-07 |
| O-09 | Lưu `db` riêng từng người, lịch sử, chạy tiếp stage lỗi; chia sẻ team ở mức Contributor | `ArtifactData`; kiểm tra bằng tài khoản thứ hai | O-07 |
| O-10 | Zip tương thích `runs/` | pytest: `load_step_outputs_from_run` đọc được | O-09 |
| O-11 | Sửa bản cuối + learning loop + diff offline | Golden + run thật | O-09, O-05 |
| O-12 | Bảng chỉnh model/effort, 3 preset, A/B mù | Test render + phiên thử | O-09 |
| O-13 | ADR chốt bảng model | Kết quả A/B thật | O-12 |
| O-14 | Gửi kết quả qua Gmail (tạo nháp mặc định; gửi ngay có xác nhận; đính kèm `.txt` như `email_sender.py`) | Bản nháp/email thật | O-11 |
| O-15 | Core JS Voice Lab + test so khớp với Python | Log `node --test` | O-04, O-05 |
| O-16 | Voice Lab bước 1–2 (phân tích có bằng chứng, xem lại evidence) | Hồ sơ nháp thật | O-15, O-09 |
| O-17 | Voice Lab bước 3–4 (phỏng vấn, A/B calibration) | Phiên thật | O-16 |
| O-18 | Voice Lab bước 5 (compile, publish vào thư viện team, rollback, dùng trong workflow, xuất zip lên repo) | Run thật bằng style mới; kiểm tra quyền | O-17, O-07 |

Không có vòng phụ thuộc. Đường găng: O-01 → O-03 → O-04 → O-05 → O-06 → O-07 → O-09 → O-11 → … → O-15 → O-16 → O-17 → O-18.

---

## 4. Roadmap

Nguồn lực: một agent build (Claude Code) và owner (duyệt, nghiệm thu, chạy thật, đánh giá A/B). Txx là thứ tự tương đối.

| Chặng | PRD | Increment khi đóng | Loại |
|---|---|---|---|
| T0 | ART-0 | Bằng chứng runtime cho D2, D7 và Voice Lab | Spike |
| T1 | ART-1 | Quy tắc cập nhật; bundle và golden fixtures từ repo | Contract (repo) |
| T2 | ART-2 | Core JS workflow khớp Python | Build |
| T3 | ART-3 | **MVP:** viết blog trên claude.ai | Vertical slice |
| T4 | ART-4 | Lịch sử riêng từng người, chia sẻ team, xuất zip | Build |
| T5 | ART-5 | Bản cuối và learning loop | Build |
| T6a | ART-6.1 | Công cụ chỉnh model và A/B | Build |
| T6b | ART-6.2 | Bảng model chốt bằng dữ liệu thật | **Owner chờ dữ liệu nhiều ngày**, chạy cùng lúc với T7–T8 |
| T7 | ART-7 | Gửi kết quả qua Gmail | Build |
| T8a | ART-8.1 | Core JS Voice Lab khớp Python | Build |
| T8b | ART-8.2 | Voice Lab: phân tích và xem lại evidence | Build |
| T8c | ART-8.3 | Voice Lab: phỏng vấn và A/B calibration | Build |
| T8d | ART-8.4 | Voice Lab: compile, publish, dùng style mới để viết | Build (chờ xác nhận D3a) |

---

## 5. PRD Registry

| PRD | Tên | Chặng | Owner tổng hợp | Nghiệm thu | Trạng thái |
|---|---|---|---|---|---|
| ART-0 | Spike runtime | T0 | Agent | Owner | BACKLOG |
| ART-1 | Quy tắc, bundle, contract | T1 | Agent | Owner | BACKLOG |
| ART-2 | Core engine JS | T2 | Agent | Owner | BACKLOG |
| ART-3 | MVP vertical slice | T3 | Agent | Owner | BACKLOG |
| ART-4 | Lưu trữ, team, xuất file | T4 | Agent | Owner | BACKLOG |
| ART-5 | Bản cuối và learning loop | T5 | Agent | Owner | BACKLOG |
| ART-6.1 | Cấu hình model và A/B | T6a | Agent | Owner | BACKLOG |
| ART-6.2 | Đánh giá A/B, chốt bảng model | T6b | Owner | Owner | BACKLOG |
| ART-7 | Gmail | T7 | Agent | Owner | BACKLOG |
| ART-8.1 | Core Voice Lab JS | T8a | Agent | Owner | BACKLOG |
| ART-8.2 | Voice Lab: phân tích và evidence | T8b | Agent | Owner | BACKLOG |
| ART-8.3 | Voice Lab: phỏng vấn và A/B calibration | T8c | Agent | Owner | BACKLOG |
| ART-8.4 | Voice Lab: compile, publish, sử dụng | T8d | Agent | Owner | DRAFT (chờ D3a) |

---

## 6. Chi tiết PRD

### ART-0 — Spike runtime

- **Mục tiêu:** xác nhận D7 và D2 hoạt động đúng trên tổ chức Claude Team; đo các giới hạn mà Voice Lab và bài dài phụ thuộc vào.
- **Phạm vi:** một Artifact nháp. Người dùng đồng ý tiêu quota cho khoảng 10–12 lần gọi thật (AGENTS §4).
  - Gọi `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5` theo tên, từ tài khoản owner và **một đồng đội**.
  - Gọi `writing_agent` với prompt cỡ thật, bài khoảng 1800 từ.
  - Gọi `sample.json` 3 lần với prompt phân tích Voice Lab cỡ thật.
  - Ghi một document `db` khoảng 200 KB.
  - Đồng đội ở mức Contributor ghi vào `data/users/<id>/`.
- **Output:** O-01.
- **AC:**
  - ART-0-AC1: bảng `modelApplied` / `modelTierApplied` / thời gian / `truncated` cho từng model × tài khoản.
  - ART-0-AC2: bài khoảng 1800 từ kèm handoff không bị `truncated`. Nếu bị cắt: đề xuất cách xử lý trước ART-2.
  - ART-0-AC3: tỉ lệ `sample.json` qua được JSON Schema phân tích. Nếu dưới 3/3: đề xuất chiến lược sửa prompt hoặc chia nhỏ.
  - ART-0-AC4: đồng đội Contributor ghi và đọc được dữ liệu riêng; owner không đọc được dữ liệu đó.
- **Điều kiện đóng:** owner duyệt báo cáo. Nếu model nào không chạy theo tên, ghi rõ việc hạ xuống `modelTier` vào ART-1.
- **Issue dự kiến:** 1.

### ART-1 — Quy tắc, bundle, contract

- **Mục tiêu:** chốt contract và quy tắc trước mọi code Artifact.
- **Phạm vi:**
  1. **O-02:** sửa `.agents/AGENTS.md` §4, `.agents/agentic-workflow-architect/SKILL.md`, `references/architecture-invariants.md`.
     - Ghi ngoại lệ: "Voice Lab trong Claude Artifact dùng Claude qua `sample` — người dùng phê duyệt 2026-11-14".
     - Ghi rõ: "Voice Lab Python/Streamlit giữ Gemini-only".
  2. **O-03:** khối `claude:` (mục 2.3) trong `engine/config.example.yaml`.
  3. **O-04:** `artifact/build_bundle.py`.
     - Dùng lại resolver và validator Python. Không suy luận lại tên file trong JS (Bài học 14).
     - Xuất JSON Schema của `StyleProfile`, `AnalysisResult`, `ProfilePatch`, `CalibrationSession`… bằng `model_json_schema()`.
     - Xuất hằng số `VOICE_DIMENSIONS`, `DIMENSION_AGENTS`, `AGENT_FILENAME_MAP`, `REQUIRED_AGENTS`, `SKILL_LEVEL_INVARIANTS`, `CALIBRATION_MIN_WORDS` / `CALIBRATION_MAX_WORDS`, và base template của các style hệ thống.
     - Style hệ thống mang cờ `protected` trong bundle.
  4. **O-05:** golden fixtures do Python sinh, ghi vào thư mục tạm hoặc `artifact/tests/golden/`:
     - Prompt workflow, learning, Voice Lab.
     - Kết quả `compile_style` cho hồ sơ mẫu.
     - Các case parser và evidence.
- **AC:**
  - ART-1-AC1: ba tài liệu quy tắc được cập nhật; không còn mâu thuẫn với D1.
  - ART-1-AC2: build hai lần cho cùng hash.
  - ART-1-AC3: skill sai, slug sai, stage thiếu cấu hình model, schema xuất lỗi → build fail rõ ràng (test).
  - ART-1-AC4: toàn bộ regression test hiện có vẫn pass; `runs/` không đổi; không gọi API.
- **Điều kiện đóng:** AC pass; `docs/current_architecture.md` và `docs/changelog.md` được cập nhật.
- **Issue dự kiến:** 3 (quy tắc; config + builder; golden).

### ART-2 — Core engine JS (workflow)

- **Phạm vi:** các module workflow ở mục 2.1, trừ `client_sample`, `repository_db`, `export`, `gmail`; test bằng `node --test`.
- **Dependency:** O-04, O-05.
- **AC:**
  - ART-2-AC1: prompt khớp từng byte với golden cho mọi stage × mode.
  - ART-2-AC2: parser chặt pass các case tương đương `tests/test_handoff_parser.py`.
  - ART-2-AC3: orchestrator với client giả: chạy đủ stage; dừng khi lỗi; bỏ qua đúng stage phụ thuộc; telemetry đủ; `api_called: false`.
  - ART-2-AC4: tách Edited Blog / Edit Log giống Python.
- **NFR:** core không chạm DOM hay `window.claude`.
- **Issue dự kiến:** 2.

### ART-3 — MVP vertical slice

- **User story:** Là người viết, tôi dán ghi chú thô, chọn mode và style, bấm Chạy, xem từng stage hiện ra, rồi tải bài cuối về.
- **Phạm vi:**
  - Form đúng định dạng `examples/*_input_template.md`.
  - Chọn mode và style hệ thống.
  - Hai chế độ chạy: liền một mạch, hoặc từng bước.
  - `client_sample.js` gọi theo tên model, `cache: false`, nút Stop, chữ "Đang suy nghĩ…".
  - Mỗi stage hiện Artifact, Handoff, model yêu cầu so với model thực chạy, và cảnh báo khi bị hạ.
  - Nút "Chạy lại stage"; số từ; tải `.md`.
  - Bản nháp form lưu `localStorage`, bọc try/catch.
  - Xử lý lỗi theo `code`.
- **Dependency:** O-06.
- **AC:**
  - ART-3-AC1: Playwright với `window.claude` giả: màn 390px và desktop, sáng/tối, đủ các trạng thái.
  - ART-3-AC2 (run thật): một run `moment/va-natural` và một run `deep/reflective` hoàn tất trên claude.ai.
  - ART-3-AC3: telemetry đúng model thực chạy.
  - ART-3-AC4: không dùng mock để tuyên bố runtime đạt.
- **NFR:** trang vẫn tải được khi không có `sample`; không cuộn ngang ở 390px.
- **Issue dự kiến:** 2.

### ART-4 — Lưu trữ, team, xuất file

- **Phạm vi:**
  - `repository_db.js` lưu tại `data/users/<id>/runs/{runId}` và `.../stages/{stageId}`; checkpoint sau mỗi stage.
  - Lịch sử run; "Chạy tiếp từ stage lỗi".
  - Zip bố cục `runs/`.
  - Khai báo quy tắc `db` cho team (mục 1.5, trừ `library` sẽ thêm ở ART-8.4).
  - Màn kiểm tra quyền: thiếu Contributor thì hiện hướng dẫn xin quyền.
  - Hướng dẫn owner chia sẻ Artifact ở mức Contributor cho thành viên tổ chức.
- **Dependency:** O-07.
- **AC:**
  - ART-4-AC1: `ArtifactData list` thấy run của owner; đọc ở cấp quyền thấp hơn không thấy dữ liệu riêng.
  - ART-4-AC2: một đồng đội chạy, lưu, mở lại run của họ; owner không thấy run đó.
  - ART-4-AC3: pytest (tmp_path): `load_step_outputs_from_run` đọc đúng zip mẫu.
  - ART-4-AC4: Run ID không trùng; không ghi đè run; hẹn giờ tải 10 giây; `db` rỗng hiển thị đúng.
- **Issue dự kiến:** 2.

### ART-5 — Bản cuối và learning loop

- **Phạm vi:**
  - Khung soạn `production_blog.md`.
  - `editorial_learning` và `workflow_tuning` dùng model trong `claude.learning`; dùng **artifact đầy đủ** (Bài học 4).
  - Diff offline.
  - Xuất báo cáo gắn nhãn mode/style (Bài học 13).
  - Không tự sửa skill (D3).
- **Dependency:** O-09, O-05.
- **AC:**
  - ART-5-AC1: learning prompt khớp golden.
  - ART-5-AC2: một vòng học thật hoàn tất.
  - ART-5-AC3: thiếu production → nút learning bị khóa kèm giải thích; diff offline vẫn chạy.
- **Issue dự kiến:** 2.

### ART-6.1 — Cấu hình model và công cụ A/B

- **Phạm vi:**
  - Bảng chỉnh model/effort cho mọi stage, kể cả learning và Voice Lab. Ghi đè lưu ở `data/users/<id>/settings`.
  - 3 preset: Chất lượng tối đa / Cân bằng / Nhanh.
  - A/B mù hai cấu hình trên cùng input; lưu kết quả.
- **Dependency:** O-09.
- **AC:**
  - ART-6.1-AC1: ghi đè chỉ áp dụng cho người đó; có nút khôi phục mặc định.
  - ART-6.1-AC2: thứ tự A/B được xáo và ẩn tới khi chọn.
  - ART-6.1-AC3: một phiên thử được lưu.
- **Issue dự kiến:** 1.

### ART-6.2 — Đánh giá A/B và chốt bảng model

- **Phạm vi:**
  - Owner, có thể cùng đồng đội, chạy A/B trên 3–5 input thật: mốc "Opus 5.5 ở mọi stage, effort medium" so với phương án Cân bằng.
  - Agent viết ADR, cập nhật khối `claude:`, build và publish lại lên đúng URL.
- **Loại:** chờ bên ngoài, không chặn ART-7 và ART-8.x.
- **AC:**
  - ART-6.2-AC1: có ít nhất 3 cặp A/B.
  - ART-6.2-AC2: ADR ghi bảng cuối và lý do.
  - ART-6.2-AC3: bundle mới được publish.
- **Nếu chậm:** ghi PENDING ("chờ dữ liệu A/B"); Artifact vẫn dùng phương án Cân bằng.
- **Issue dự kiến:** 1.

### ART-7 — Gmail

- **Mục tiêu:** thay `email_sender.py` (Resend) bằng Gmail của chính người dùng.
- **Phạm vi:**
  - Khai báo `mcp: { servers: [{ server: "Gmail", tools: ["create_draft", "send_message"] }] }`.
  - Nội dung và file đính kèm `.txt` như `email_sender._build_attachments`:
    - Deep: `final_blog.txt`, `coaching_report.txt`, `future_reflection.txt`.
    - Moment: `final_moment.txt`, `witness_report.txt`.
  - Mặc định **tạo bản nháp**. "Gửi ngay" chỉ chạy sau hộp xác nhận hiện rõ người nhận và danh sách file.
  - Người nhận do người dùng nhập, nhớ ở `data/users/<id>/settings`. Không xin scope email của `user`.
  - Người xem chưa kết nối Gmail hoặc tổ chức chưa bật kết nối → nút bị ẩn hoặc vô hiệu, kèm hướng dẫn.
- **Dependency:** O-11 (cần bản cuối do người viết sửa).
- **AC:**
  - ART-7-AC1: bản nháp có đủ file đính kèm xuất hiện trong Gmail của owner.
  - ART-7-AC2: "Gửi ngay" chỉ chạy sau xác nhận.
  - ART-7-AC3: đồng đội dùng Gmail của chính họ.
  - ART-7-AC4: lỗi `tool_error` hoặc thiếu quyền được hiển thị rõ, không tự thử lại.
- **Issue dự kiến:** 1.

### ART-8.1 — Core Voice Lab JS

- **Phạm vi:** các module mục 2.2 dạng hàm thuần; test `node --test` so khớp golden Python; tham chiếu `tests/test_voice_lab.py`.
- **Dependency:** O-04, O-05.
- **AC:**
  - ART-8.1-AC1: `compiler.js` cho kết quả **giống hệt** `compile_style` trên các hồ sơ golden, cho deep (7 agent) và moment (6 agent).
  - ART-8.1-AC2: quote không khớp nguyên văn → evidence bị loại và lưu lại để audit; confidence tính bằng code khớp Python.
  - ART-8.1-AC3: chọn tối đa 3 chiều phỏng vấn giống `interview_routing`; patch chỉ áp dụng khi có cờ xác nhận.
  - ART-8.1-AC4: calibration chỉ thay đúng một chiều; `shuffle_mapping` không lộ ra dữ liệu hiển thị.
  - ART-8.1-AC5: dữ liệu không qua schema v2 → lỗi; không có nhánh tự bịa dữ liệu.
- **Issue dự kiến:** 2.

### ART-8.2 — Voice Lab: phân tích và xem lại evidence (bước 1–2)

- **User story:** Là người viết, tôi dán 3–10 bài mẫu, nhận một hồ sơ giọng văn 12 chiều có quote làm bằng chứng, rồi duyệt hoặc loại từng bằng chứng.
- **Phạm vi:**
  - Nhập mẫu văn: dán hoặc chọn file `.md`/`.txt` đọc tại trình duyệt.
  - Chia nhỏ theo ngân sách byte.
  - `sample.json` dùng model `vl_analysis`, sau đó `vl_synthesis`.
  - Kiểm tra schema và quote.
  - Màn xem lại evidence.
  - Lưu hồ sơ nháp ở `data/users/<id>/voicelab/`.
- **Dependency:** O-15, O-09.
- **AC:**
  - ART-8.2-AC1: một hồ sơ nháp thật được tạo từ mẫu văn thật.
  - ART-8.2-AC2: lỗi `invalid_json` hoặc sai schema → hiện lỗi, hồ sơ giữ nguyên trạng thái draft, không có DNA giả.
  - ART-8.2-AC3: dữ liệu mẫu văn và hồ sơ nháp riêng tư (kiểm tra bằng tài khoản thứ hai).
- **Issue dự kiến:** 2.

### ART-8.3 — Voice Lab: phỏng vấn và A/B calibration (bước 3–4)

- **Phạm vi:**
  - Phỏng vấn tối đa 3 chiều yếu nhất; `vl_interview_patch` đề xuất patch; người dùng xác nhận mới áp dụng.
  - A/B mù chỉ thay một chiều, dùng `vl_calibration`; lựa chọn cập nhật strength, examples, history.
- **Dependency:** O-16.
- **AC:**
  - ART-8.3-AC1: một phiên phỏng vấn và một phiên A/B thật hoàn tất.
  - ART-8.3-AC2: từ chối patch thì hồ sơ không đổi.
  - ART-8.3-AC3: mapping A/B chỉ lộ sau khi chọn.
- **Issue dự kiến:** 2.

### ART-8.4 — Voice Lab: compile, publish và sử dụng (bước 5) — DRAFT, chờ D3a

- **Phạm vi:**
  - Compile lên base template của style hệ thống đã chọn.
  - Publish theo mục 2.4 vào `library/<authorId>/styles/<slug>`, có rollback.
  - Khai báo thêm quy tắc `library` (đọc: `interact`; ghi: tác giả ở `{self}`; prefix: `admin`). Nhắc lại đầy đủ các quy tắc cũ vì khai báo capability là thay toàn bộ.
  - Style thư viện xuất hiện trong danh sách chọn style của workflow, có nhãn "Thư viện team · tác giả".
  - Xuất zip theo định dạng `archive.py` để đưa lên repo; đánh dấu "đã chuyển vào repo" khi bundle mới chứa style đó.
- **Dependency:** O-17, O-07.
- **AC:**
  - ART-8.4-AC1: một style mới được publish và dùng để chạy một workflow thật thành công.
  - ART-8.4-AC2: slug trùng style hệ thống hoặc style thư viện cùng mode → bị từ chối; style hệ thống không bị ghi đè.
  - ART-8.4-AC3: rollback đưa con trỏ về phiên bản trước; phiên bản cũ còn nguyên.
  - ART-8.4-AC4: đồng đội đọc được style trong thư viện nhưng không sửa được style của người khác; owner xóa được (`ArtifactData` ở các cấp quyền).
  - ART-8.4-AC5: zip xuất ra được `import_style` của Python đọc thành công (pytest, tmp_path).
- **Issue dự kiến:** 2.

---

## 7. Chiến lược kiểm thử theo độ trưởng thành

| Chặng | Lớp kiểm thử | Không được làm |
|---|---|---|
| T0 | Đo trực tiếp trên claude.ai, có sự đồng ý, với hai tài khoản | Coi spike là bằng chứng kiến trúc |
| T1 | pytest với `tmp_path`, không gọi API, chụp `runs/` trước và sau | Chạy `run_workflow()` với `log_dir: runs` |
| T2, T8a | `node --test`, client giả, so khớp golden | Gọi `sample` thật |
| T3 | Playwright với `window.claude` giả để kiểm tra UI; **run thật** để nghiệm thu | Dùng mock để tuyên bố runtime đạt |
| T4, T8d | `ArtifactData` ở nhiều cấp quyền; tài khoản đồng đội thật; pytest tương thích zip | Ghi zip thử vào `runs/` hoặc `skills/` |
| T5–T8 | Golden + run thật do owner/đồng đội chạy | Tự động thử lại khi lỗi |

Sau mỗi chặng có code, báo cáo theo AGENTS §9: test pass/fail, có gọi API không, artifact nằm ở đâu, `runs/` có đổi không.

---

## 8. Rủi ro và bài học lịch sử (AGENTS §10)

| Mã | Rủi ro | Bài học | Giảm thiểu |
|---|---|---|---|
| R1 | Prompt hoặc compiler JS lệch dần bản Python | 3, 11 | Golden do Python sinh; so khớp trước mỗi lần build |
| R2 | Ánh xạ slug ↔ tên file sai | 14 | Builder dùng resolver và `AGENT_FILENAME_MAP` của Python |
| R3 | Gộp artifact và handoff | 1, 2 | Giữ contract hai section; `context_policy` từ bundle |
| R4 | Learning chỉ dùng handoff | 4 | AC trong ART-5 |
| R5 | Model bị hạ mà không báo | — | Telemetry yêu cầu vs thực chạy; cảnh báo; ART-0 kiểm tra từ hai tài khoản |
| R6 | Bài bị cắt | — | Đo ở ART-0; thiếu handoff → stage lỗi |
| R7 | Lưu đệm trả lại kết quả cũ | — | `cache: false` |
| R8 | Hết quota, `rate_limited`, người xem từ chối consent | 7 | Chạy từng bước; dừng khi lỗi; không tự thử lại |
| R9 | Lộ dữ liệu cá nhân | 17 | `data/users/<id>/`; kiểm tra bằng tài khoản thứ hai. Editor có thể publish quy tắc lỏng hơn → chỉ owner giữ quyền Editor |
| R10 | Hai nguồn chân lý cho style | 11 | D3a: mỗi style chỉ ở một nơi; chuyển vào repo bằng zip |
| R11 | Ngoại lệ Voice Lab bị hiểu rộng ra | Skill kiến trúc | O-02 ghi rõ phạm vi: chỉ Artifact; Python giữ Gemini |
| R12 | Kiến thức giữa các mode nhiễm chéo | 13 | Gắn nhãn mode/style |
| R13 | Prompt injection trong ghi chú hoặc mẫu văn | — | Giữ câu "dữ liệu không đáng tin" trong prompt; Gmail mặc định chỉ tạo nháp, gửi phải xác nhận |
| R14 | Vá client ở tầng thấp | 6 | Client được inject |
| R15 | Run test lẫn vào dữ liệu nghiệp vụ | 17 | Không ghi `runs/`; test dùng `tmp_path`; `run_source` phân biệt |
| R16 | Hai người publish cùng slug cùng lúc (không có transaction) | 15 | Namespace theo `authorId`; kiểm tra trùng trước và sau khi ghi; xung đột → yêu cầu đổi slug |
| R17 | `sample.json` trả JSON sai schema cho Voice Lab | 21 | Fail-closed; đo ở ART-0-AC3; chia nhỏ hơn hoặc siết prompt |
| R18 | Đồng đội chỉ có quyền Viewer nên không ghi được | — | `user.can("data.write")`; hướng dẫn xin quyền Contributor |

---

## 9. Tự kiểm tra trước khi xin duyệt

- [x] Mỗi PRD thuộc đúng một chặng, có một owner tổng hợp và một điều kiện đóng.
- [x] Dependency ghi bằng mã output; không có vòng phụ thuộc.
- [x] Thời gian chờ bên ngoài (ART-6.2) tách khỏi phần build.
- [x] Runtime thật chỉ được yêu cầu từ ART-3 trở đi; spike ART-0 có sự đồng ý của người dùng.
- [x] Không ai làm hai việc chính cùng lúc: agent build T7–T8 trong khi owner đánh giá A/B ở T6b.
- [x] Xung đột quy tắc Voice Lab được nêu rõ và xử lý trong ART-1 trước khi có code.
- [ ] D3a chờ người dùng xác nhận → ART-8.4 giữ DRAFT.

## 10. Bước tiếp theo

1. Người dùng xác nhận D3a.
2. Người dùng đồng ý tiêu quota cho ART-0 và chỉ định một đồng đội tham gia kiểm tra.
3. Bắt đầu ART-0, sau đó ART-1. Tạo Issue khi người dùng yêu cầu.
