# Kế hoạch tổng thể: Mindful Blog Workflow trên Claude Artifact

> **Trạng thái:** FINAL (bản 3) — quyết định D1–D7 và D3a đã được người dùng chốt ngày 2026-11-14.
> Toàn bộ PRD ở trạng thái BACKLOG; ART-0 bắt đầu thực hiện.
> **Mã dự án:** ART
> **Tài liệu đã đọc theo `.agents/AGENTS.md` §10:** `docs/current_architecture.md`, `docs/workflow_analysis.md`, `.agents/agentic-workflow-architect/SKILL.md` và các reference.

## Lịch sử thay đổi

| Bản | Ngày | Thay đổi |
|---|---|---|
| 1 | 2026-11-14 | Bản nháp đầu tiên; D1–D7 còn mở |
| 2 | 2026-11-14 | Chốt D1–D7:<br>• Thêm track Voice Lab (ART-8.1 → 8.4)<br>• Thêm phạm vi team (D2)<br>• Gmail chuyển thành ART-7, bỏ dictation<br>• Model gọi theo tên<br>• Thêm bước cập nhật quy tắc Voice Lab vào ART-1<br>• Làm rõ D3 thành D3a |
| 3 | 2026-11-14 | D2 đổi sang **mỗi tác giả một Artifact riêng**; đồng đội tự clone (publish lại bản build dưới tài khoản của họ):<br>• Bỏ thư viện style dùng chung và quy tắc `db` cho team<br>• Thư viện style (D3a) thành riêng của từng tác giả<br>• Thêm gói clone và tem phiên bản vào ART-4<br>• D3a được chốt; ART-8.4 sang BACKLOG<br>• Chỉ định tài khoản kiểm tra thứ hai cho ART-0 |
| 3.12 | 2026-11-15 | Owner đóng ART-6.2 (giữ bảng Cân bằng, ADR); ART-7 đổi từ Gmail sang tải `final_blog.md` và `run_log.md`; ghi kết quả ART-8.1 và ART-7 |
| 3.11 | 2026-11-15 | ART-6.1 DONE (phiên A/B thật đạt); ghi cặp A/B thật đầu tiên cho ART-6.2 |
| 3.10 | 2026-11-15 | Ghi kết quả ART-6.1 (AC1, AC2 đạt bằng test; chờ owner chạy một phiên A/B thật cho AC3); thêm preset mốc Opus 5.5 · medium |
| 3.9 | 2026-11-15 | ART-5 DONE (vòng học thật đạt) |
| 3.8 | 2026-11-14 | ART-4 chuyển PENDING (AC2 để sau); ghi kết quả ART-5 |
| 3.7 | 2026-11-14 | ART-4 AC3 đạt (lịch sử còn nguyên sau khi publish lại) |
| 3.6 | 2026-11-14 | ART-3 DONE; ghi kết quả ART-4 và đường dẫn lưu trữ thực tế |
| 3.5 | 2026-11-14 | ART-3 AC2 đạt; sửa lỗi tách bài Moment trong engine và JS |
| 3.4 | 2026-11-14 | ART-2 DONE; ghi kết quả ART-3 (AC1) và URL trang MVP |
| 3.3 | 2026-11-14 | ART-1 DONE; ghi kết quả ART-2 |
| 3.2 | 2026-11-14 | ART-0 DONE; ghi kết quả ART-1 và các đặc điểm engine mà ART-2/ART-8.1 phải bám theo |
| 3.1 | 2026-11-14 | Ghi kết quả ART-0; bổ sung yêu cầu `countWords` vào ART-2 và input 1200–1800 từ vào ART-3 |

---

## 1. Baseline

### 1.1. Mục tiêu sản phẩm

Một Artifact trên claude.ai, **mỗi tác giả dùng một bản riêng**. Đồng đội trong tổ chức Claude Team tự clone bản build và dùng cho riêng họ. Artifact này:

1. **Chạy hai workflow viết blog** (`deep`, `moment`) với mọi style.
   - Mỗi stage là một lần gọi `sample` độc lập, ngữ cảnh chỉ gồm những gì `context_policy` cho phép.
   - Mỗi stage dùng model Claude được gọi **theo tên**, kèm effort riêng.
2. **Lưu lịch sử run**, cho sửa bản cuối, chạy learning loop, và tải `final_blog.md`, `run_log.md` (D5, đổi ngày 2026-11-15: bỏ Gmail).
3. **Có Voice Lab đủ 5 bước**, chạy bằng Claude, để tác giả tạo style giọng văn của riêng mình.

Repo vẫn là nguồn chân lý cho flow, skill hệ thống, bảng model và các hằng số Voice Lab. Artifact dùng một bundle được build và kiểm tra từ repo.

### 1.2. Người dùng (D2)

| Vai trò | Ai | Quyền trên Artifact | Ghi chú |
|---|---|---|---|
| Tác giả (chủ Artifact) | Chủ repo; mỗi đồng đội là chủ của bản clone của họ | Owner | Người duy nhất dùng bản đó; không chia sẻ cho người khác |

Hệ quả:

- **Không có dữ liệu dùng chung giữa người.** Mỗi bản clone bắt đầu với `db` trống.
- Mỗi tác giả tiêu quota Claude Team của chính mình.
- **Clone** = publish lại cùng file `dist/index.html` (build từ repo) thành một Artifact mới dưới tài khoản của đồng đội. Cách này không phụ thuộc việc claude.ai có nút "nhân bản" hay không.
- Khi owner cập nhật bundle, mỗi đồng đội phải publish lại bản của mình lên **đúng URL cũ của họ** để giữ dữ liệu. Trang hiện tem phiên bản để dễ biết bản nào đã cũ.

### 1.3. Nền tảng và năng lực runtime

claude.ai Artifact, runtime contract `0.2.96`.

| Capability | Dùng để |
|---|---|
| `sample` | Gọi Claude theo tên model cho workflow, learning, Voice Lab |
| `db` | Run, hồ sơ Voice Lab, thư viện style riêng của tác giả |
| `user` | Định danh tác giả để lưu vào `data/users/<id>/` (không xin scope `profile` hay `email`) |
| `downloads` | Xuất `.md`/`.zip` |
| `mcp` | Không dùng (ART-7 đổi sang tải file, 2026-11-15) |

### 1.4. Ngoài phạm vi

- Nhập bằng giọng nói (`dictation`) (D5).
- Trình sửa YAML thô cho style hệ thống trong Artifact (D3).
- Định tuyến nhiều nhà cung cấp (OpenAI, Gemini, DeepSeek), Resend, Supabase, Render, Google OAuth.
- Thay đổi Streamlit UI và Voice Lab Python. **Voice Lab Python vẫn dùng Gemini.**
- `engine/claude_client.py` cho Python. Đây là track riêng, không phải dependency.

### 1.5. Dữ liệu và quyền

| Đường dẫn `db` | Nội dung |
|---|---|
| `data/users/<id>/blog/runs/...` | Run, các stage, bản cuối, learning |
| `data/users/<id>/voicelab/...` | Mẫu văn, hồ sơ giọng văn đang soạn, phỏng vấn, A/B |
| `data/users/<id>/library/<slug>/...` | Style tác giả đã publish (D3a) |
| `data/users/<id>/settings` | Ghi đè model, người nhận email mặc định |

- Mọi dữ liệu nằm trong `data/users/<id>/`. Dùng quy tắc mặc định của `db`, **không khai báo quy tắc riêng**. Nếu lỡ chia sẻ Artifact, người khác vẫn không đọc được dữ liệu này.
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

### 1.7. Quyết định đã chốt

| Mã | Quyết định | Hệ quả trong kế hoạch |
|---|---|---|
| D1 | **Có** đưa Voice Lab vào Artifact | Track ART-8.1 → 8.4. Voice Lab trong Artifact dùng **Claude**. ART-1 cập nhật quy tắc Gemini-only (xem bên dưới) |
| D2 | Mỗi tác giả một Artifact riêng; đồng đội tự clone | Gói clone + tem phiên bản (ART-4); kiểm tra bằng tài khoản thứ hai |
| D3 | Skill sửa trong repo rồi build lại; Artifact chỉ đọc | Style hệ thống trong bundle là read-only và được bảo vệ |
| D4 | Bảng model phương án Cân bằng | Khối `claude:` (mục 2.3); giữ nguyên sau ART-6.2 (`docs/2026-11-15-adr-claude-model-table.md`) |
| D5 | Không làm Gmail (đổi ngày 2026-11-15), không có dictation | ART-7 tải `final_blog.md` và `run_log.md`; bỏ dictation |
| D6 | Mã nguồn ở `artifact/` trong repo | — |
| D7 | Gọi model theo tên | `sample({ model, effort, modelTier })`; ART-0 xác nhận trên tài khoản của owner và tài khoản kiểm tra thứ hai |

**Xung đột cần ghi nhận (AGENTS.md §1):**

- `.agents/AGENTS.md` §4, `SKILL.md` và `architecture-invariants.md` hiện quy định Voice Lab chỉ dùng Gemini.
- Quyết định D1 của người dùng là phê duyệt cụ thể cho một ngoại lệ có phạm vi:
  - **Voice Lab trong Claude Artifact dùng Claude qua `sample`.**
  - Voice Lab Python/Streamlit giữ nguyên Gemini-only.
- ART-1 phải sửa ba tài liệu này **trước khi** viết code Voice Lab.

**D3a (đã chốt) — để D1 và D3 cùng đứng được:**

- Style hệ thống (trong repo, bundle) chỉ đọc và được bảo vệ, giống `is_protected`.
- Style do Voice Lab tạo nằm trong **thư viện riêng của tác giả** (`data/users/<id>/library/`), chạy được ngay trong Artifact của họ.
- Muốn đưa một style thành style hệ thống: xuất zip đúng định dạng `engine/voice_lab/archive.py`, commit vào repo, build lại bundle. Bản trong thư viện được đánh dấu "đã chuyển vào repo" và bị ẩn.
- Mỗi style chỉ có **một nơi ở** tại một thời điểm, nên không có hai nguồn chân lý.
- Đồng đội nhận style hệ thống mới bằng cách publish lại bản clone từ bundle mới.

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
                                   db: data/users/<id>/… (runs, voicelab, library) ◄───┤
                                   downloads (.md/.zip) ◄──────────────────────────────┤
                                   downloads: final_blog.md / run_log.md ◄────────────┘
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
| ~~`gmail.js`~~ | `email_sender.py` | Bỏ (2026-11-15); ART-7 tải `final_blog.md` và `run_log.md` qua `downloads` |

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

1. **Staging:** ghi toàn bộ style (6 hoặc 7 skill đã compile, `style_meta`, hồ sơ v2) thành **một** document bất biến `data/users/<id>/library/<slug>/versions/<versionId>`. Ước khoảng 50–80 KB, dưới giới hạn 256 KiB.
2. **Validate:** đọc lại document đó; kiểm tra schema, flow–skill contract, các trường bất biến, slug/alias duy nhất trong mode so với bundle và thư viện.
3. **Backup:** phiên bản trước vẫn được giữ nguyên, không xóa.
4. **Replace:** cập nhật **một** document con trỏ `data/users/<id>/library/<slug>` → `currentVersion`. Ghi một document là nguyên tử.
5. **Rollback:** trỏ con trỏ về phiên bản trước.

Style hệ thống trong bundle không bao giờ bị ghi đè. Slug trùng với style hệ thống thì bị từ chối.

---

## 3. Bản đồ output

| Mã | Output | Bằng chứng | Phụ thuộc |
|---|---|---|---|
| O-01 | Báo cáo spike: model gọi theo tên có chạy cho owner và tài khoản thứ hai; độ trễ; bài dài có bị cắt; độ tin cậy của `sample.json`; giới hạn `db` | Số liệu đo trên claude.ai | — |
| O-02 | Quy tắc Voice Lab được cập nhật trong AGENTS.md §4, SKILL.md, architecture-invariants.md | Diff tài liệu | D1 |
| O-03 | Khối `claude:` trong `engine/config.example.yaml` | Diff + test schema | O-01 |
| O-04 | `artifact/build_bundle.py` → `bundle.json` (flow, skill, bảng model, JSON Schema Voice Lab, hằng số, base template) | pytest (tmp_path); hash tất định | O-02, O-03 |
| O-05 | Golden fixtures: prompt workflow, learning, Voice Lab; kết quả compile do Python sinh | Script sinh lại + file golden | O-04 |
| O-06 | Core JS workflow + test `node --test` | Log test | O-04, O-05 |
| O-07 | Artifact MVP đã publish (chạy workflow, streaming, Stop, chạy lại stage, tải `.md`) | URL; run thật | O-06 |
| O-08 | Test render UI bằng Playwright, `window.claude` giả lập | Log + ảnh | O-07 |
| O-09 | Lưu `db` của tác giả, lịch sử, chạy tiếp stage lỗi; gói clone (`artifact/CLONE.md`) và tem phiên bản | `ArtifactData`; tài khoản thứ hai clone và chạy được | O-07 |
| O-10 | Zip tương thích `runs/` | pytest: `load_step_outputs_from_run` đọc được | O-09 |
| O-11 | Sửa bản cuối + learning loop + diff offline | Golden + run thật | O-09, O-05 |
| O-12 | Bảng chỉnh model/effort, 3 preset, A/B mù | Test render + phiên thử | O-09 |
| O-13 | ADR chốt bảng model | Kết quả A/B thật | O-12 |
| O-14 | Tải `final_blog.md` (bản cuối đang có trên trang) và `run_log.md` (định dạng engine) | File tải về thật | O-11 |
| O-15 | Core JS Voice Lab + test so khớp với Python | Log `node --test` | O-04, O-05 |
| O-16 | Voice Lab bước 1–2 (phân tích có bằng chứng, xem lại evidence) | Hồ sơ nháp thật | O-15, O-09 |
| O-17 | Voice Lab bước 3–4 (phỏng vấn, A/B calibration) | Phiên thật | O-16 |
| O-18 | Voice Lab bước 5 (compile, publish vào thư viện riêng, rollback, dùng trong workflow, xuất zip lên repo) | Run thật bằng style mới | O-17, O-07 |

Không có vòng phụ thuộc. Đường găng: O-01 → O-03 → O-04 → O-05 → O-06 → O-07 → O-09 → O-11 → … → O-15 → O-16 → O-17 → O-18.

---

## 4. Roadmap

Nguồn lực: một agent build (Claude Code) và owner (duyệt, nghiệm thu, chạy thật, đánh giá A/B). Txx là thứ tự tương đối.

| Chặng | PRD | Increment khi đóng | Loại |
|---|---|---|---|
| T0 | ART-0 | Bằng chứng runtime cho D7 và Voice Lab, trên hai tài khoản | Spike |
| T1 | ART-1 | Quy tắc cập nhật; bundle và golden fixtures từ repo | Contract (repo) |
| T2 | ART-2 | Core JS workflow khớp Python | Build |
| T3 | ART-3 | **MVP:** viết blog trên claude.ai | Vertical slice |
| T4 | ART-4 | Lịch sử run, xuất zip, gói clone cho đồng đội | Build |
| T5 | ART-5 | Bản cuối và learning loop | Build |
| T6a | ART-6.1 | Công cụ chỉnh model và A/B | Build |
| T6b | ART-6.2 | Bảng model chốt bằng dữ liệu thật | **Owner chờ dữ liệu nhiều ngày**, chạy cùng lúc với T7–T8 |
| T7 | ART-7 | Tải final_blog.md và run_log.md | Build |
| T8a | ART-8.1 | Core JS Voice Lab khớp Python | Build |
| T8b | ART-8.2 | Voice Lab: phân tích và xem lại evidence | Build |
| T8c | ART-8.3 | Voice Lab: phỏng vấn và A/B calibration | Build |
| T8d | ART-8.4 | Voice Lab: compile, publish, dùng style mới để viết | Build |

---

## 5. PRD Registry

| PRD | Tên | Chặng | Owner tổng hợp | Nghiệm thu | Trạng thái |
|---|---|---|---|---|---|
| ART-0 | Spike runtime | T0 | Agent | Owner | DONE (owner duyệt 2026-11-14) |
| ART-1 | Quy tắc, bundle, contract | T1 | Agent | Owner | DONE (owner cho chuyển sang ART-2, 2026-11-14) |
| ART-2 | Core engine JS | T2 | Agent | Owner | DONE (owner cho chuyển sang ART-3, 2026-11-14) |
| ART-3 | MVP vertical slice | T3 | Agent | Owner | DONE (owner xác nhận 2026-11-14) |
| ART-4 | Lưu trữ, xuất file, gói clone | T4 | Agent | Owner | PENDING (AC3, AC4, AC5 đạt; AC1 một phần; AC2 để sau theo quyết định owner) |
| ART-5 | Bản cuối và learning loop | T5 | Agent | Owner | DONE (owner chạy vòng học thật 2026-11-15) |
| ART-6.1 | Cấu hình model và A/B | T6a | Agent | Owner | DONE (owner chạy phiên A/B thật 2026-11-15) |
| ART-6.2 | Đánh giá A/B, chốt bảng model | T6b | Owner | Owner | CLOSED (owner đóng 2026-11-15 với 1 cặp A/B; giữ bảng Cân bằng, xem ADR) |
| ART-7 | Tải final_blog.md và run_log.md | T7 | Agent | Owner | ON-GOING (AC1, AC2, AC4 đạt bằng test; chờ owner tải thật cho AC3) |
| ART-8.1 | Core Voice Lab JS | T8a | Agent | Owner | ON-GOING (AC1–AC5 đạt bằng test; chờ owner duyệt) |
| ART-8.2 | Voice Lab: phân tích và evidence | T8b | Agent | Owner | BACKLOG |
| ART-8.3 | Voice Lab: phỏng vấn và A/B calibration | T8c | Agent | Owner | BACKLOG |
| ART-8.4 | Voice Lab: compile, publish, sử dụng | T8d | Agent | Owner | BACKLOG |

---

## 6. Chi tiết PRD

### ART-0 — Spike runtime

- **Mục tiêu:** xác nhận D7 trên tổ chức Claude Team từ hai tài khoản; đo các giới hạn mà bài dài và Voice Lab phụ thuộc vào.
- **Phạm vi:** một Artifact nháp (`artifact/spike/`), chia sẻ **tạm thời** ở mức Contributor cho tài khoản kiểm tra thứ hai do owner chỉ định. Người dùng đã đồng ý tiêu quota (AGENTS §4).
  - **Owner (7 lần gọi):**
    - 3 lần gọi ngắn `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5` theo tên.
    - 1 lần `writing_agent` (Opus 5.5, high) với prompt cỡ thật, bài 1200–1800 từ.
    - 3 lần `sample.json` với prompt phân tích Voice Lab cỡ thật (Opus 5.5, high).
    - Ghi và đọc lại một document `db` khoảng 200 KB (không gọi Claude).
  - **Tài khoản thứ hai (3 lần gọi):** 3 lần gọi ngắn theo tên.
  - Prompt dựng bằng chính hàm Python (`build_step_prompt`, `build_analysis_prompt`) từ fixture `examples/`; không gọi `run_workflow()`, không ghi `runs/`.
  - Kết quả lưu vào `db` của spike để agent đọc bằng `ArtifactData`. JSON phân tích được kiểm lại bằng parser Pydantic của repo.
- **Output:** O-01.
- **AC:**
  - ART-0-AC1: bảng `modelApplied` / `modelTierApplied` / thời gian tới chữ đầu / tổng thời gian / `truncated` cho từng model × tài khoản.
  - ART-0-AC2: bài 1200–1800 từ kèm handoff không bị `truncated`, đủ hai section. Nếu bị cắt: đề xuất cách xử lý trước ART-2.
  - ART-0-AC3: tỉ lệ `sample.json` qua được `parse_analysis_response` của repo. Nếu dưới 3/3: đề xuất cách sửa prompt hoặc chia nhỏ.
  - ART-0-AC4: ghi và đọc lại document khoảng 200 KB thành công.
- **Kết quả (2026-11-14):** AC1, AC3, AC4 đạt; AC2 đạt một phần (bài 721 từ, chưa thử 1200–1800 từ, chuyển sang ART-3-AC2). Chi tiết: `docs/2026-11-14-art0-spike-report.md`.
- **Điều kiện đóng:**
  - Owner duyệt báo cáo `docs/2026-11-14-art0-spike-report.md`.
  - Gỡ quyền chia sẻ tạm của spike.
  - Nếu model nào không chạy theo tên, ghi rõ việc hạ xuống `modelTier` vào ART-1.
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
- **Kết quả (2026-11-14):**
  - AC1: ba tài liệu quy tắc ghi ngoại lệ D1 có phạm vi.
  - AC2: hai lần build cho cùng `content_hash`; bundle khoảng 220 KB.
  - AC3: 22 test trong `tests/test_artifact_bundle.py`, gồm skill thiếu, output lệch flow, slug sai, base style không tồn tại, khối `claude:` sai (thiếu/thừa stage, model chưa kiểm chứng, effort sai, thiếu khối), JSON Schema xuất lỗi, CLI không ghi file khi lỗi.
  - AC4: 151 test pass; 2 test lỗi có sẵn từ trước (đường dẫn kiểu Windows khi chạy trên Linux); không gọi API; `runs/` không tồn tại, `skills/`, `flow/`, `web_runs/` không đổi.
  - Quyết định thiết kế: skill trong bundle kèm chuỗi YAML do PyYAML dựng sẵn, nên JS không cần port PyYAML cho style hệ thống. Style do Voice Lab tạo (ART-8) sẽ cần một bộ dump YAML phía JS.
- **Issue dự kiến:** 3 (quy tắc; config + builder; golden).

### ART-2 — Core engine JS (workflow)

- **Phạm vi:** các module workflow ở mục 2.1, trừ `client_sample`, `repository_db`, `export`, `gmail`; test bằng `node --test`.
- **Dependency:** O-04, O-05.
- **AC:**
  - ART-2-AC1: prompt khớp từng byte với golden cho mọi stage × mode; `countWords` khớp `count_words` của Python (`\w+`) trên các bài có emoji (ART-0: bản dùng regex Unicode đếm thừa 3 từ do ký tự U+FE0F).
  - ART-2-AC2: parser chặt pass các case tương đương `tests/test_handoff_parser.py`.
  - ART-2-AC3: orchestrator với client giả: chạy đủ stage; dừng khi lỗi; bỏ qua đúng stage phụ thuộc; telemetry đủ; `api_called: false`.
  - ART-2-AC4: tách Edited Blog / Edit Log giống Python.
- **NFR:** core không chạm DOM hay `window.claude`.
- **Ghi chú từ ART-1 (golden đã ghi lại hành vi thật của engine):**
  - Parser chặt từ chối chuỗi có CRLF; Python chỉ đọc file qua `read_text` (đã chuẩn hóa xuống dòng). JS nên chuẩn hóa `\r\n` → `\n` trước khi parse để tương đương đường file, và golden `crlf` dùng để kiểm tra hàm parse thuần.
  - `count_words` theo `\w+` của Python; learning prompt chịu `textwrap.dedent` sau khi nội suy (dòng chỉ có khoảng trắng bị xóa, thụt lề 8 dấu cách của template giữ nguyên).
- **Kết quả (2026-11-14):** mã tại `artifact/src/core/` (ES module, không dependency), test tại `artifact/tests/js/` (51 case, `node --test`), chạy kèm regression qua `tests/test_artifact_js.py`.
  - AC1: prompt của mọi stage deep/reflective và moment/va-natural khớp từng byte với golden, cả khi gọi trực tiếp lẫn qua orchestrator; `countWords`/`estimateTokens` khớp Python trên mọi case golden, gồm emoji có U+FE0F.
  - AC2: parser chặt khớp 12 case golden (gồm 2 case lấy từ `tests/test_handoff_parser.py`, CRLF và BOM bị từ chối như engine) và các case port từ test Python.
  - AC3: chạy đủ 7/6 stage; dừng khi lỗi; khi không dừng thì bỏ qua đúng chuỗi stage phụ thuộc (ví dụ lỗi ở `reader_experience` kéo theo `editor_agent`, `coach_agent`, `future_self`); có cảnh báo khi bị cắt hoặc bị hạ hạng; trạng thái `cancelled` khi dừng; chạy từng bước và chạy lại stage lỗi; client giả cho `api_called: false`.
  - AC4: tách Edited Blog/Edit Log khớp golden cho 3 skill × 5 kiểu artifact.
  - NFR: test tĩnh xác nhận core không dùng `window`, `document`, `localStorage`, `claude.use`, `fetch` và không import ngoài core.
  - Kiểm tra độ nhạy: cố ý làm hỏng 4 chỗ (đếm cả dấu kết hợp, đổi một câu hướng dẫn, nhận CRLF, bỏ sắp xếp dependency); test bắt được cả 4.
  - Khác biệt có chủ đích so với engine: khi phản hồi sai contract sau một lời gọi thật, JS ghi `api_called: true` (engine ghi `false`); phản hồi được chuẩn hóa CRLF trước khi parse, tương đương đường đọc file của engine.
  - Để lại cho ART-3: core gồm nhiều ES module với tên export không trùng nhau, nên có thể publish nhiều file hoặc gộp thành một script; chọn cách nào sẽ quyết định khi dựng trang.
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
  - ART-3-AC2 (run thật): một run `moment/va-natural` và một run `deep/reflective` hoàn tất trên claude.ai. Run deep dùng input có `desired_length` 1200–1800 từ để đóng phần còn thiếu của ART-0-AC2 (không bị cắt, đủ hai section).
  - ART-3-AC3: telemetry đúng model thực chạy.
  - ART-3-AC4: không dùng mock để tuyên bố runtime đạt.
- **NFR:** trang vẫn tải được khi không có `sample`; không cuộn ngang ở 390px.
- **Kết quả (2026-11-14):**
  - Trang: https://claude.ai/artifact/A4a9RofpD22TCCx6cgWEHT, publish từ `artifact/dist/index.html` (capability `sample`, `downloads`). Lần cập nhật sau phải publish lại đúng file này để giữ URL.
  - Đóng gói: `artifact/build_html.py` gộp bundle và các ES module thành một trang duy nhất (script inline, cách đã chạy được ở spike). Bundler tối giản, mỗi module một phạm vi riêng; từ chối cú pháp không hỗ trợ, import vòng, `</script`.
  - Lõi mới: `input.js` (input đúng mẫu `examples/*_input_template.md`, `slugify`), `outputs.js` (thành phẩm theo `final_output` của flow, file gộp toàn bộ), `client_sample.js` (`model`/`modelTier`/`effort`, `cache: false`, chặn prompt > 256 KiB trước khi gọi, `apiCalled` chỉ true khi chắc lời gọi đã tới Claude).
  - AC1: 15 kịch bản Playwright với `window.claude` giả ở 390px và 1280px, sáng/tối: trang trống, chạy liền đủ bước rồi tải bài, lỗi rồi chạy lại bước, bấm dừng giữ phần đã viết, chạy từng bước, bị hạ hạng/bị cắt, đổi sang Deep không mất kết quả cũ, khôi phục bản nháp form, thiếu input, không có Claude; nội dung độc hại từ model không được thực thi. Đã xem ảnh chụp và sửa lỗi khung "Bản nháp" hiện ra khi chưa có bài.
  - AC2 (2026-11-14): owner chạy thật một lượt Deep và một lượt Moment trên claude.ai, cả hai hoàn tất không lỗi.
  - Lỗi phát hiện khi nghiệm thu: bước `breath_editor` của Moment báo không tách được bài khỏi edit log. Nguyên nhân có sẵn trong engine Python: skill Moment chỉ khai báo tên phần (`output.sections: [edited_moment_blog, edit_log]`), model đặt tiêu đề theo tên file (`### moment_edited.md`, `### edit_log.md`), còn hàm tách chỉ nhận tiêu đề kiểu Deep, nên edit log bị dính vào cuối bản nháp. Run cũ trong `web_runs/` cũng bị như vậy. Đã sửa ở `engine/workflow_artifacts.py` và port sang `artifact/src/core/artifacts.js`: nhận thêm tên phần trong `output.sections` và tên file làm tiêu đề, coi gạch dưới và khoảng trắng như nhau; tiêu đề cũ vẫn được ưu tiên nên Deep không đổi. Chạy lại trên artifact thật của run cũ (chỉ đọc): không còn cảnh báo, bản nháp sạch, edit log tách đúng. Trang đã publish lại cùng URL.
  - AC3: chờ owner xác nhận mọi bước đều hiện "đúng model". AC4: không tuyên bố runtime đạt dựa trên bản giả lập.
- **Issue dự kiến:** 2.

### ART-4 — Lưu trữ, xuất file, gói clone

- **Phạm vi:**
  - `repository.js` lưu tại `data/users/<id>/blog/runs/{runId}` và `.../stages/{stageId}` (đường dẫn đã chỉnh theo quy tắc phân đoạn của `db`); checkpoint sau mỗi stage.
  - Lịch sử run; "Chạy tiếp từ stage lỗi".
  - Zip bố cục `runs/`.
  - **Gói clone cho đồng đội:**
    - `artifact/CLONE.md` hướng dẫn publish `dist/index.html` thành Artifact riêng dưới tài khoản của họ, và cách cập nhật lên đúng URL cũ.
    - Tem phiên bản (hash bundle, ngày build) hiện trên trang.
- **Dependency:** O-07.
- **AC:**
  - ART-4-AC1: `ArtifactData list` thấy run của owner; đọc ở cấp quyền thấp hơn không thấy dữ liệu trong `data/users/`.
  - ART-4-AC2: tài khoản thứ hai làm theo `CLONE.md`, publish bản riêng, chạy và lưu một run; dữ liệu hai bản độc lập.
  - ART-4-AC3: publish lại bản build mới lên cùng URL vẫn giữ lịch sử run.
  - ART-4-AC4: pytest (tmp_path): `load_step_outputs_from_run` đọc đúng zip mẫu.
  - ART-4-AC5: Run ID không trùng; không ghi đè run; hẹn giờ tải 10 giây; `db` rỗng hiển thị đúng.
- **Kết quả (2026-11-14):**
  - Đường dẫn thực tế: `data/users/<uid>/blog/runs/<runId>` và `.../runs/<runId>/stages/<stageId>`, vì theo quy tắc chẵn/lẻ phân đoạn của `db`, `data/users/<uid>/runs` là document chứ không phải collection.
  - Mã: `core/run_record.js` (Run ID cùng dạng engine, chuyển đổi và khôi phục run), `core/repository.js` (hàng đợi ghi tuần tự, không ghi đè, chặn document > 256 KiB), `core/export.js` (bố cục thư mục run của engine), giao diện lịch sử/mở lại/chạy tiếp/tải zip, tem phiên bản trong `build_html.py`, `artifact/CLONE.md`. Không lưu `files` của stage; khi khôi phục thì tách lại từ artifact.
  - Trang đã publish lại cùng URL (phiên bản 3) với capability `sample`, `downloads`, `db`, `user`.
  - AC1 (một phần): ghi, đọc, xóa một document thử tại `data/users/me/blog/runs` qua `ArtifactData`. Đọc ở quyền `view` vẫn thấy vì công cụ giữ danh tính owner, nên phép thử này không chứng minh được tính riêng tư với người khác; điều đó dựa trên quy tắc mặc định của nền tảng và được kiểm chứng thật ở AC2.
  - AC3 (2026-11-14): owner chạy và lưu một bài Moment thật. Trước và sau khi publish lại (phiên bản 4), cả 7 document của run (1 run + 6 stage) giữ nguyên đường dẫn, nội dung và version (so qua `ArtifactData`, bản sao tạm đã xóa).
  - Dữ liệu của run thật đó cũng xác nhận thêm: 6/6 stage có `model_applied` trùng model yêu cầu (bằng chứng cho ART-3-AC3); `breath_editor` không còn cảnh báo tách bài (bản sửa lỗi Moment chạy đúng trên claude.ai); `api_called: true` ở mọi stage.
  - AC2: chờ đồng đội clone theo `CLONE.md`.
  - AC4: `tests/test_artifact_export.py`: engine đọc đúng `step_outputs.json` của run xuất ra (bỏ qua stage lỗi như run của chính nó) và chạy trọn learning loop offline trên đó.
  - AC5: test JS cho Run ID (định dạng, 200 ID không trùng, thử lại khi trùng, báo lỗi sau 5 lần, không ghi đè); Playwright cho lịch sử trống, hết 10 giây chờ, lưu lỗi, không có quyền lưu trữ, mở lại sau khi tải lại trang, chạy tiếp run bị gián đoạn, tải zip đúng bố cục (kiểm tra bằng `zipfile` của Python).
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
- **Kết quả (2026-11-14):**
  - Mã: `core/learning.js` (learning prompt, tuning prompt, báo cáo và gợi ý offline, `runLearning`), `core/learning_templates.js` sinh từ f-string của `engine/learning.py` bằng `artifact/gen_learning_templates.py` (có test báo khi cũ), `core/pydifflib.js` (port `SequenceMatcher` có autojunk và `unified_diff` của CPython 3.13), thêm `pyDedent`/`pySplitlines`/`pyFormatFixed` (half-even)/`truncateWords`. Lưu bản cuối tại `runs/<runId>/production/current`, mỗi vòng học tại `runs/<runId>/learning/<learningId>`; zip có `production_blog.md` và `learning/<mode>/<timestamp>/` đúng bố cục engine. Trang publish lại cùng URL (phiên bản 5); lịch sử cũ còn nguyên.
  - AC1: learning prompt (4 case, gồm vượt ngân sách), tuning prompt (2 case), 5 báo cáo offline (gồm bản giống hệt, chuỗi dài kích hoạt autojunk, CRLF) và định dạng số khớp golden; fuzz `difflib` 300/300. Kiểm chứng chéo: learning loop offline của engine Python chạy trên run do Artifact xuất ra cho báo cáo và gợi ý giống hệt từng byte bản Artifact tạo.
  - AC3: nút học bị khóa kèm giải thích khi bản cuối trống; học qua Claude bị khóa khi bản cuối giống hệt bản nháp AI hoặc không có Claude, so sánh offline vẫn chạy (Playwright).
  - AC2 (2026-11-15): owner chạy một vòng học thật qua Claude trên run Moment đã lưu. Bản ghi cho thấy: trạng thái completed, so với `moment_edited.md`, `editorial_learning` chạy `claude-opus-5-5` (high, 26,0 s) và `workflow_tuning` chạy `claude-sonnet-5-5` (medium, 16,7 s), cả hai đúng model, không bị cắt, `api_called: true`; báo cáo khoảng 10.300 ký tự, gợi ý khoảng 5.100 ký tự nhắc đủ 6 stage của Moment; bản cuối đã lưu trùng với bản dùng để học. Chỉ đọc thông tin kỹ thuật, không đọc nội dung; bản sao tạm đã xóa.
  - Cách hiểu đã chọn cho "diff offline vẫn chạy": so sánh offline luôn chạy được khi có bản cuối, kể cả khi không có Claude; cả hai cách học đều cần bản cuối.
  - Kiểm thử giao diện: `db` giả chuyển sang `window.name` vì Chromium ghi `localStorage`/`sessionStorage` bất đồng bộ khiến test tải lại trang chập chờn; sửa hai race chờ chữ đang viết. Sáu lượt toàn bộ 27 kịch bản đều pass.
- **Issue dự kiến:** 2.

### ART-6.1 — Cấu hình model và công cụ A/B

- **Phạm vi:**
  - Bảng chỉnh model/effort cho mọi stage, kể cả learning và Voice Lab. Ghi đè lưu ở `data/users/<id>/settings`.
  - 3 preset: Chất lượng tối đa / Cân bằng / Nhanh (thêm preset mốc Opus 5.5 · medium để ART-6.2 so sánh).
  - A/B mù hai cấu hình trên cùng input; lưu kết quả.
- **Dependency:** O-09.
- **AC:**
  - ART-6.1-AC1: ghi đè chỉ áp dụng cho người đó; có nút khôi phục mặc định.
  - ART-6.1-AC2: thứ tự A/B được xáo và ẩn tới khi chọn.
  - ART-6.1-AC3: một phiên thử được lưu.
- **Kết quả (2026-11-15):**
  - Contract: `artifact/claude_config.py` giới hạn effort ở `low`/`medium`/`high`; bundle có `model_catalog` (model đã kiểm chứng và hạng, các mức effort) để trang chỉ cho chọn những giá trị build chấp nhận.
  - Mã: `core/model_settings.js` (4 preset: Cân bằng = bảng trong repo; Chất lượng tối đa = Opus 5.5 high mọi bước; Nhanh = Sonnet 5.5 medium, riêng 4 bước viết/biên tập dùng Opus 5.5 medium; Mốc Opus 5.5 · medium cho ART-6.2), cài đặt chỉ lưu phần khác mặc định, giá trị ngoài danh mục bị bỏ và báo lại. `core/ab.js` (phiên A/B: nhãn A/B gán ngẫu nhiên bằng `crypto`, bài mù không kèm cấu hình, tiết lộ sau khi chốt, chọn được "ngang nhau"). Mỗi run lưu bảng model lúc tạo (`models`, `model_profile`), nên chạy tiếp hoặc chạy lại một bước vẫn dùng đúng cấu hình đó; run cũ không có bảng thì dùng cấu hình hiện tại.
  - Lưu trữ: cài đặt tại `data/users/<uid>/settings` (không có `db` thì lưu `localStorage`); phiên A/B tại `data/users/<uid>/blog/ab/<abId>`, hai bài là hai run bình thường gắn `ab_session`.
  - Giao diện: khung "Model cho từng bước" (preset, chỉnh từng bước kèm giá trị mặc định để đối chiếu, Lưu, Về mặc định); khung "So sánh A/B mù" (chọn hai cấu hình, báo tốn gấp đôi lượt gọi, chạy A rồi B, chỉ hiện tiến độ và số ký tự, dừng, chạy tiếp, chốt kèm ghi chú, xem lại phiên cũ). Bài A/B chưa chốt bị ẩn khỏi lịch sử vì mở ra sẽ thấy model của từng bước.
  - AC1: Playwright kiểm tra cài đặt lưu đúng vùng riêng, chỉ chứa phần khác mặc định, lần chạy gọi đúng model/effort, tải lại vẫn còn, "Về mặc định" xóa hết ghi đè; trường hợp không có `db` lưu trong trình duyệt.
  - AC2: test JS kiểm tra cả hai cách gán nhãn; Playwright kiểm tra trước khi chốt khung A/B không chứa tên cấu hình hay tên model, sau khi chốt mới hiện đúng cấu hình của bài đã chọn.
  - AC3 (2026-11-15): owner chạy một phiên A/B thật, Moment/reflective, Cân bằng so với Mốc Opus 5.5 · medium. Bản ghi cho thấy: phiên ở trạng thái `decided` và đủ trường; nhãn đã xáo (A là cấu hình Mốc Opus 5.5 · medium, B là Cân bằng); hai run đều completed, mỗi run gắn `ab_session` đã chốt và lưu đúng bảng model của cấu hình mình. Cả 12 bước gọi đúng model và effort của cấu hình, không bị hạ hạng, không bị cắt, không có cảnh báo, `api_called: true`. Owner chọn bài A (Mốc Opus 5.5 · medium, 224 từ) thay vì bài B (Cân bằng, 197 từ), không ghi chú. Tổng thời gian các bước: Mốc Opus 57,6 s, Cân bằng 66,6 s. Chỉ đọc thông tin kỹ thuật, không đọc bài, ghi chú thô hay ghi chú; bản sao tạm đã xóa.
  - Test đã kiểm tra thêm: phiên được lưu, mở lại sau khi tải trang, chạy tiếp sau gián đoạn hoặc sau khi bấm Dừng.
  - Trang publish lại cùng URL (phiên bản 6), capability giữ nguyên; run cũ còn nguyên.
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
- **Dữ liệu đã có:**
  - Cặp 1 (2026-11-15, Moment/reflective): owner chọn Mốc Opus 5.5 · medium thay vì Cân bằng; không ghi chú. Một cặp chưa đủ để kết luận.
- **Kết quả (2026-11-15):** owner đóng ART-6.2 sau 1 cặp. ADR `docs/2026-11-15-adr-claude-model-table.md`: giữ bảng Cân bằng làm mặc định; ai muốn dùng mốc Opus 5.5 · medium thì tự chọn preset trong ART-6.1. AC1 bị bỏ qua theo quyết định owner; AC2 đạt bằng ADR; AC3 không phát sinh vì bundle không đổi.
- **Nếu chậm:** ghi PENDING ("chờ dữ liệu A/B"); Artifact vẫn dùng phương án Cân bằng.
- **Issue dự kiến:** 1.

### ART-7 — Tải final_blog.md và run_log.md (thay cho Gmail)

- **Đổi phạm vi (2026-11-15, quyết định owner):** không làm Gmail nữa. Thay vào đó là hai nút tải file trên trang. Phạm vi Gmail cũ (khai báo `mcp`, file `.txt` như `email_sender._build_attachments`, tạo nháp, gửi có xác nhận) bị bỏ.
- **Phạm vi:**
  - "Tải final_blog.md": đúng bài đang có trong khung "Bản cuối của bạn", kể cả khi chưa lưu. Đây là bài người viết hoàn thiện, giống `human_final: final_blog.md` của flow.
  - "Tải run_log.md": cùng nội dung với `run_log.md` trong zip, theo định dạng `append_run_log` của engine (metadata, input, artifact của từng bước, lỗi nếu có).
  - Dùng capability `downloads` đã có; không thêm capability mới.
- **Dependency:** O-11.
- **AC:**
  - ART-7-AC1: `final_blog.md` tải về đúng bài đang có trên trang; bản cuối trống thì nút bị khóa.
  - ART-7-AC2: `run_log.md` tải riêng giống hệt `run_log.md` trong zip.
  - ART-7-AC3: owner tải thật cả hai file trên claude.ai.
  - ART-7-AC4: không có quyền tải file thì hai nút bị khóa.
- **Kết quả (2026-11-15):**
  - Mã: `downloadFinalBlog` và `downloadRunLog` trong `src/ui/app.js`. `run_log.md` lấy từ `exportRunFiles` nên không có bản dựng thứ hai.
  - `final_blog.md` **không** được thêm vào zip, vì learning loop của engine ưu tiên `human_final` khi có file này. Nếu thêm, engine sẽ so `final_blog.md` với `production_blog.md` (hai bản của người viết) thay vì so bản nháp AI với bản cuối.
  - AC1, AC2, AC4: 3 kịch bản Playwright (nội dung và tên file, so khớp từng byte với zip, khóa nút khi không có `downloads`). Trang publish lại cùng URL (phiên bản 7).
  - AC3: chờ owner.
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
- **Kết quả (2026-11-15):**
  - Mã `artifact/src/vl/`:
    - `prompts.js`: 4 prompt giống từng byte. Bản Claude nối JSON Schema do Python dựng sẵn (`bundle.voice_lab.schema_texts`), đúng cách spike ART-0.
    - `schema.js`: kiểm tra JSON Schema xuất từ Pydantic. Gặp từ khóa chưa hỗ trợ thì báo lỗi (fail-closed). Điền mặc định giống `model_dump`.
    - `analyzer.js`: chia mẫu theo ngân sách token tính theo code point; kiểm tra quote nguyên văn; khử trùng; tính Voice DNA và confidence bằng code. Ngoài ngân sách token, mỗi prompt còn phải vừa giới hạn byte của `sample`; quá thì giảm nửa ngân sách và chia lại (tất định). Prompt vừa ngân sách thì cách chia giống hệt Python.
    - `interview.js`, `calibration.js`, `compiler.js` (kèm merge overrides), `models.js`.
  - `pycompat.js` thêm: `pyJsonDumps` (giữ `1.0` cho trường float), `pyFloatRepr`, `pyRound`, `pyFind`/`pyLen` theo code point, `pyCasefold`, `pyCompare`.
  - Bundle thêm: nhãn tiếng Việt của 12 chiều, tham số chia mẫu, `ir_level_invariants`, `schema_texts`.
  - Golden mới `voicelab_flow.json`, sinh bằng Gemini giả và uuid tất định. Gồm: phân tích một lượt và nhiều lượt (4 lời gọi, mẫu dài bị cắt có gối đầu), 5 lỗi, phỏng vấn, patch, calibration, merge, 31 trường hợp schema có kết luận của Pydantic.
  - AC1: `compile_style` giống hệt cho deep (7 agent), moment (6 agent), moment không DNA, compile một phần và lỗi rule trùng do/avoid.
  - AC2: quote không khớp bị loại, lưu kèm lý do; confidence khớp Python.
  - AC3: chọn tối đa 3 chiều giống `interview_routing`; patch chỉ áp dụng khi `confirmed`, hồ sơ cũ không đổi.
  - AC4: calibration chỉ đổi đúng một chiều; `blindCalibrationView` không có `shuffle_mapping`.
  - AC5: sai JSON, sai schema, hoặc không có quote hợp lệ thì báo lỗi và không tạo hồ sơ.
  - Tổng cộng 15 test JS mới (gồm test hàm thuần cho `src/vl`).
  - Khác bản Python có chủ đích: mã lỗi `gemini_unavailable` đổi thành `model_unavailable`, thông báo nói "Claude"; kiểm tra "token prompt + token output > context" của Gemini thay bằng kiểm tra byte.
  - `publisher.js` (mục 2.2) chuyển sang ART-8.4, vì publish dùng `db` (phiên bản bất biến, con trỏ, rollback), không phải hàm thuần.
- **Ghi chú từ ART-1:** prompt Voice Lab nhúng payload bằng `json.dumps` của Python (separators `", "`/`": "`, giữ `1.0`); `quote_start`/`quote_end` tính theo code point, không theo UTF-16; 10 skill có số thực (`version: 3.0`) mà JSON làm mất dạng (thành `3`), nên JS không tự tính được `stable_skill_hash`: dùng `base_hash` do Python tính sẵn trong `styles[mode][slug].files[file].base_hash`.
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
  - ART-8.2-AC3: mẫu văn và hồ sơ nháp nằm trong `data/users/<id>/voicelab/`; đọc ở cấp quyền thấp hơn không thấy.
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

### ART-8.4 — Voice Lab: compile, publish và sử dụng (bước 5)

- **Phạm vi:**
  - Compile lên base template của style hệ thống đã chọn.
  - Publish theo mục 2.4 vào `data/users/<id>/library/<slug>`, có rollback.
  - Style thư viện xuất hiện trong danh sách chọn style của workflow, có nhãn "Style của tôi".
  - Xuất zip theo định dạng `archive.py` để đưa lên repo; đánh dấu "đã chuyển vào repo" khi bundle mới chứa style đó.
- **Dependency:** O-17, O-07.
- **AC:**
  - ART-8.4-AC1: một style mới được publish và dùng để chạy một workflow thật thành công.
  - ART-8.4-AC2: slug trùng style hệ thống hoặc style thư viện cùng mode → bị từ chối; style hệ thống không bị ghi đè.
  - ART-8.4-AC3: rollback đưa con trỏ về phiên bản trước; phiên bản cũ còn nguyên.
  - ART-8.4-AC4: zip xuất ra được `import_style` của Python đọc thành công (pytest, tmp_path).
- **Issue dự kiến:** 2.

---

## 7. Chiến lược kiểm thử theo độ trưởng thành

| Chặng | Lớp kiểm thử | Không được làm |
|---|---|---|
| T0 | Đo trực tiếp trên claude.ai, có sự đồng ý, với hai tài khoản | Coi spike là bằng chứng kiến trúc |
| T1 | pytest với `tmp_path`, không gọi API, chụp `runs/` trước và sau | Chạy `run_workflow()` với `log_dir: runs` |
| T2, T8a | `node --test`, client giả, so khớp golden | Gọi `sample` thật |
| T3 | Playwright với `window.claude` giả để kiểm tra UI; **run thật** để nghiệm thu | Dùng mock để tuyên bố runtime đạt |
| T4, T8d | `ArtifactData` ở nhiều cấp quyền; tài khoản thứ hai clone thật; pytest tương thích zip | Ghi zip thử vào `runs/` hoặc `skills/` |
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
| R9 | Lộ dữ liệu cá nhân khi lỡ chia sẻ Artifact | 17 | Mọi dữ liệu trong `data/users/<id>/`; không khai báo quy tắc mở rộng; kiểm tra ở cấp quyền thấp hơn |
| R10 | Hai nguồn chân lý cho style | 11 | D3a: mỗi style chỉ ở một nơi; chuyển vào repo bằng zip |
| R11 | Ngoại lệ Voice Lab bị hiểu rộng ra | Skill kiến trúc | O-02 ghi rõ phạm vi: chỉ Artifact; Python giữ Gemini |
| R12 | Kiến thức giữa các mode nhiễm chéo | 13 | Gắn nhãn mode/style |
| R13 | Prompt injection trong ghi chú hoặc mẫu văn | — | Giữ câu "dữ liệu không đáng tin" trong prompt |
| R14 | Vá client ở tầng thấp | 6 | Client được inject |
| R15 | Run test lẫn vào dữ liệu nghiệp vụ | 17 | Không ghi `runs/`; test dùng `tmp_path`; `run_source` phân biệt |
| R16 | Hai tab cùng publish một slug (không có transaction) | 15 | Kiểm tra trùng trước và sau khi ghi con trỏ; xung đột → báo và giữ phiên bản thắng |
| R17 | `sample.json` trả JSON sai schema cho Voice Lab | 21 | Fail-closed; đo ở ART-0-AC3; chia nhỏ hơn hoặc siết prompt |
| R18 | Bản clone của đồng đội bị cũ so với bundle mới | — | Tem phiên bản trên trang; `CLONE.md` hướng dẫn publish lại lên đúng URL cũ |
| R19 | Publish clone lên URL mới làm mất lịch sử | — | `CLONE.md` nhấn mạnh cập nhật đúng URL cũ; AC3 của ART-4 kiểm tra |

---

## 9. Tự kiểm tra trước khi xin duyệt

- [x] Mỗi PRD thuộc đúng một chặng, có một owner tổng hợp và một điều kiện đóng.
- [x] Dependency ghi bằng mã output; không có vòng phụ thuộc.
- [x] Thời gian chờ bên ngoài (ART-6.2) tách khỏi phần build.
- [x] Runtime thật chỉ được yêu cầu từ ART-3 trở đi; spike ART-0 có sự đồng ý của người dùng.
- [x] Không ai làm hai việc chính cùng lúc: agent build T7–T8 trong khi owner đánh giá A/B ở T6b.
- [x] Xung đột quy tắc Voice Lab được nêu rõ và xử lý trong ART-1 trước khi có code.
- [x] D3a đã được chốt.

## 10. Bước tiếp theo

1. Thực hiện ART-0: build và publish spike; owner và tài khoản thứ hai bấm chạy; agent đọc kết quả và viết báo cáo.
2. Sau khi owner duyệt báo cáo: bắt đầu ART-1. Tạo Issue khi người dùng yêu cầu.
