# Báo cáo tiến độ và chỉ dẫn bàn giao cho Agent kế tiếp

**Ngày cập nhật:** 28/07/2026
**Repository:** `D:\Nghiên cứu AI\write_blog`
**Nhánh hiện tại:** `main`
**Checkpoint code ổn định:** `7d2576d`
**Chuỗi commit P1:** `ea7d08d` → `9a003ee` → `bebd980` → `7d2576d`
**Trạng thái:** P0 và P1 hoàn tất; workflow sử dụng được.

---

## 1. Mục đích tài liệu

Tài liệu này là nguồn bàn giao để agent khác có thể tiếp tục công việc nếu phiên hiện tại hết model quota.

Agent tiếp quản phải:

1. Đọc toàn bộ tài liệu này.
2. Đọc `AGENTS.md` và `.agents/AGENTS.md`.
3. Dùng skill `.agents/agentic-workflow-architect/SKILL.md` khi thay đổi workflow, engine, prompt contract, provider, learning, compiler, publisher hoặc UI liên quan.
4. Không giả định worktree sạch.
5. Không sửa, xóa, reset hoặc commit lẫn thay đổi nội dung của người dùng.
6. Chỉ thực hiện một checkpoint nhỏ tại một thời điểm và báo cáo ngay khi checkpoint xanh.

---

## 2. Trạng thái sử dụng hiện tại

Workflow viết blog hiện có thể sử dụng:

- `deep_blog_mode`: 7 stage.
- `moment_blog_mode`: 6 stage.
- CLI workflow.
- Streamlit UI khởi động được.
- Workbench preview in-memory.
- Voice Lab phân tích, interview, calibration, compile và publish theo contract hiện tại.

Điều kiện bên ngoài:

- Sinh bài thật cần quota/API key của provider workflow tương ứng.
- Voice Lab chỉ dùng Gemini API.
- Hết quota Codex không ảnh hưởng khả năng chạy ứng dụng đã cài đặt.
- Hết quota API thì preview/dry-run vẫn dùng được nhưng không sinh nội dung AI thật.

---

## 3. Bằng chứng kiểm chứng P0

### 3.1. Regression

Kết quả gần nhất:

```text
111 passed, 4 warnings in 13.88s
```

Lệnh đã chạy:

```powershell
python -m pytest -q
```

Test đã chạy ngoài sandbox Windows vì `pytest tmp_path` từng gặp lỗi ACL trong sandbox.

Không có API thật được gọi:

- OpenAI test dùng mock HTTP.
- Gemini test dùng monkeypatch/fake.
- Workflow test dùng fake/dry-run.
- Learning test dùng offline/fake.

### 3.2. Warning không chặn

1. OpenAI test dùng API key giả hardcode để kiểm thử warning.
2. `dateutil` có deprecation warning trong Streamlit AppTest.
3. Hai workflow fixture không có đủ section để tách secondary artifact nên phát warning fallback.

Không warning nào làm sai kết quả nghiệp vụ.

### 3.3. Bất biến `runs/`

Trước và sau P0:

```text
File count : 838
Total bytes: 1,576,920
Latest write: 2026-07-27T17:33:15.1794859+07:00
```

P0 không tạo, sửa hoặc xóa dữ liệu trong `runs/`.

### 3.4. Vệ sinh phiên

- Không còn tiến trình Python/Streamlit nền.
- Không còn `.agent-test-*`.
- Hai log Streamlit rỗng do lần thử visual trước đã được xóa.
- Diff P0 đã qua `git diff --cached --check` trước commit.

---

## 4. Git checkpoint và phạm vi commit

Checkpoint:

```text
b850b7267f7f90eae3ac645ef02aea93cd8f24e4
```

Commit chứa:

- RULES và skill kiến trúc.
- Refactor workflow engine.
- Refactor Voice Lab interview.
- Refactor Streamlit UI.
- Style transaction foundation.
- Learning prompt/runtime refactor.
- P0 safety patches.
- Tests mới và tests được cập nhật.
- Kế hoạch `docs/2026-07-27-rules-skill-refactor-plan.md`.

Commit không chứa:

- Nội dung blog mẫu đang sửa.
- Style `va-natural` đang sửa.
- Tài liệu phản biện có thay đổi của người dùng.
- Tài liệu handoff hiện tại.

Không dùng `git reset --hard`, `git checkout --` hoặc `git restore` trên toàn worktree.

Nếu cần so sánh code ổn định:

```powershell
git show --stat b850b72
git diff b850b72 -- <đường-dẫn-code>
```

Không rollback file nếu chưa xác định ownership.

---

## 5. Thay đổi P0 đã hoàn tất

### 5.1. Workflow I/O và persistence

File chính:

- `engine/workflow_contracts.py`
- `engine/workflow_execution.py`
- `engine/workflow_persistence.py`
- `tests/test_workflow_runtime_contract.py`

Đã thực hiện:

- Chặn Flow/Skill output trùng file nội bộ:
  - `input.md`
  - `metadata.json`
  - `step_outputs.json`
  - `run_log.md`
  - `handoff_log.md`
- Chặn secondary artifact trùng output/handoff khác.
- Tách API ghi internal file khỏi API ghi artifact.
- Path phải tương đối và không thoát run root.
- Persistence failure được ghi thành stage/run `failed`.
- Không chuyển artifact lỗi cho downstream.

### 5.2. Telemetry API/provider

File chính:

- `engine/client_router.py`
- `engine/workflow_contracts.py`
- `engine/workflow_execution.py`
- `engine/workflow_learning.py`
- `ui/controllers/workflow_controller.py`

Đã thực hiện:

- Tách `api_attempted` khỏi `api_called`.
- Antigravity Bridge được mô tả là local/non-API.
- OpenAI/Gemini được mô tả là API-capable.
- Metadata run và stage có cả hai trường.
- Fake client có thể khai báo `api_capable=False`.

Không suy luận rằng metadata `provider` đồng nghĩa API đã được gọi.

### 5.3. Voice Lab publish integrity

File chính:

- `engine/voice_lab/compiler.py`
- `engine/voice_lab/publisher.py`
- `ui/controllers/voice_lab_controller.py`
- `tests/test_voice_lab.py`

Đã thực hiện:

- `profile.mode` phải khớp compile mode.
- `profile.mode` phải khớp publish mode.
- UI không được tự sửa mode để che mismatch.
- Publisher đọc lại base style hiện hành và so `base_hash`.
- Base style đổi sau compile thì phải compile lại.
- Incremental compile không được publish.
- Publish vẫn dùng staging → validate → backup → replace → rollback.

### 5.4. Learning safety

File chính:

- `engine/workflow_learning.py`
- `engine/workflow_persistence.py`
- `engine/learning.py`

Đã thực hiện:

- Learning dùng `WorkflowDefinition`, không dùng raw Flow chưa validate.
- Chặn unsafe `final_output`.
- Stage outputs được lọc theo stage ID trong Flow.
- Đường dẫn output được giữ trong `run_dir`.
- `run_source` và dry-run persistence policy được validate trước client call.
- Dữ liệu author/output/final/production được đánh dấu là không tin cậy.

### 5.5. Quota guardrail

File chính:

- `engine/voice_lab/analyzer.py`
- `engine/learning.py`

Đã thực hiện:

- Structured Gemini call kiểm tra:

```text
estimated_input_tokens + max_output_tokens <= context_budget
```

- Quá budget thì fail trước API với `AnalysisError(code="input_too_large")`.
- Learning prompt giới hạn tổng context, không chỉ step outputs.
- Tuning prompt có budget riêng.
- Nội dung dài được truncate có marker thay vì gửi không giới hạn.

---

## 6. Kiến trúc sau refactor

### 6.1. Workflow

`engine/workflow.py` là compatibility facade.

Các module:

- `workflow_contracts.py`: runtime contracts và validators.
- `workflow_context.py`: context/prompt assembly.
- `workflow_execution.py`: stage execution.
- `workflow_persistence.py`: run repository và atomic writes.
- `workflow_resolution.py`: Flow/Skill path resolution.
- `workflow_artifacts.py`: artifact formatter/log helpers.
- `workflow_learning.py`: learning runtime.

Public API cũ vẫn được export qua facade:

- `run_workflow`
- `preview_workflow`
- `preview_workflow_text`
- `run_learning_loop`
- các helper tương thích cần thiết

### 6.2. Voice Lab interview

`engine/voice_lab/interview.py` là compatibility facade.

Các module:

- `interview_routing.py`: chọn dimension/câu hỏi.
- `profile_patch.py`: đề xuất và apply interview patch.
- `calibration.py`: blind A/B và apply selection.

Invariant:

- Proposal không sửa profile.
- Chỉ apply đã xác nhận mới tăng revision.
- Gemini callable được inject tại module domain để test.
- Không thêm OpenAI hoặc Antigravity vào Voice Lab.

### 6.3. UI

`ui/app.py` chỉ composition.

Các lớp:

- `ui/state.py`: session defaults và transition.
- `ui/controllers/`: use-case boundary.
- `ui/views/`: Streamlit rendering.

Workbench:

- Preview in-memory.
- Không tạo `runs/temp_dry_run_input.md`.
- Không gọi API.

---

## 7. Worktree còn bẩn và ownership bắt buộc

Tại thời điểm bàn giao, các file sau còn ngoài checkpoint.

### 7.1. Thay đổi của người dùng — không tự sửa/reset/commit

```text
docs/2026-07-27-voice-lab-refactor-plan.md
examples/finals/VA writing style.md
examples/moment_1.md
skills/moment/va-natural/breath_editor.yaml
skills/moment/va-natural/cosmic_signal_reader.yaml
skills/moment/va-natural/gentle_witness.yaml
skills/moment/va-natural/inner_weather.yaml
skills/moment/va-natural/moment_writer.yaml
skills/moment/va-natural/profile_dna.json
skills/moment/va-natural/sensory_capture.yaml
skills/moment/va-natural/style_meta.yaml
```

### 7.2. Tài liệu untracked có phản biện chuyên gia

```text
docs/2026-07-27-voice-lab-rules-skill-refactor-summary.md
```

Tài liệu này chứa nội dung phản biện qua nhiều model; không tự stage/commit nếu người dùng chưa yêu cầu.

### 7.3. Tài liệu handoff này

```text
docs/2026-07-27-project-progress-agent-handoff.md
```

Được tạo sau checkpoint `b850b72`; mặc định chưa commit.

---

## 8. P1 đã triển khai

P1 được triển khai tuần tự, mỗi mục có regression xanh và checkpoint riêng.

### P1.1 — UI acceptance và visual verification ✅

**Ưu tiên cao nhất.**

Mục tiêu:

- Xác nhận người dùng thao tác được UI thật, không chỉ import/smoke.
- Không sửa domain logic trừ khi test phát hiện lỗi chặn.

Phạm vi test:

1. Khởi động 4 tab:
   - Style Gallery
   - Style Studio
   - YAML Code Editor
   - Live Workbench
2. Chuyển `deep → moment → deep`.
3. Xác nhận Voice Lab transient state được reset khi đổi mode.
4. Workbench:
   - custom text;
   - template input;
   - `persisted=false`;
   - `api_attempted=false`;
   - `api_called=false`;
   - `runs/` không đổi.
5. Voice Lab wizard bằng mock Gemini:
   - analyze;
   - evidence;
   - interview proposal;
   - confirmation;
   - A/B;
   - compile review.
6. Không nhấn publish vào workspace thật trong AppTest.
7. Nếu test publish UI, inject `workspace_root=tmp_path`.
8. Kiểm tra trực quan:
   - không mất tab;
   - không mất nút chính;
   - không lỗi state/widget key;
   - không overflow nghiêm trọng;
   - thông báo Voice Lab Gemini-only đúng.

File dự kiến:

- `tests/test_ui_architecture.py`
- Có thể thêm `tests/test_ui_interactions.py`
- Chỉ sửa `ui/` nếu test chứng minh lỗi.

Tiêu chí hoàn tất:

- Targeted UI tests pass.
- Screenshot/visual check có bằng chứng.
- Không gọi API thật.
- `runs/` bất biến.
- Commit riêng.

### P1.2 — Parser strict và model telemetry ✅

Mục tiêu:

- `parse_stage_response(strict=True)` chỉ chấp nhận đúng hai top-level section.
- Từ chối section dư hoặc section lặp.
- Gemini descriptor phải báo đúng model client thực sự dùng.

File dự kiến:

- `engine/parser.py`
- `engine/client_router.py`
- `engine/gemini_client.py`
- tests liên quan

Rủi ro:

- Parser quá nghiêm có thể từ chối output model cũ.
- Phải có test compatibility rõ ràng.

Không thay model mặc định nếu người dùng chưa phê duyệt.

### P1.3 — Style editor full-transaction validation ✅

Mục tiêu:

- Editor không chỉ validate một YAML file.
- Trước commit phải validate lại toàn staging style với Flow.
- Chặn alias collision.
- Không làm hỏng System Style hoặc custom style đang dùng.

File dự kiến:

- `engine/style_manager.py`
- `engine/style_contracts.py`
- `engine/style_repository.py`
- `tests/test_style_manager.py`

Tiêu chí:

- staging → validate toàn style → replace/rollback.
- Flow/Skill output contract nhất quán.
- Rename/save/delete có failure tests.
- Không dùng thư mục style thật làm fixture.

### P1.4 — Voice Lab schema và migration hardening ✅

Mục tiêu:

- Contract hiện hành fail-closed với field dư.
- Legacy data chỉ đi qua migration adapter rõ ràng.
- Không phá `profile_dna.json` hiện có.

File dự kiến:

- `engine/voice_lab/models.py`
- `engine/voice_lab/migration.py`
- `engine/voice_lab/archive.py`
- tests fixture legacy

Đây là thay đổi rủi ro cao hơn:

- Phải audit dữ liệu legacy trước.
- Không bật `extra="forbid"` hàng loạt nếu chưa có migration test.
- Phải giữ khả năng đọc profile v1/v2 đã xuất bản.

### P1.5 — Architecture hygiene và tài liệu ✅

Mục tiêu:

- Tìm dead import/reference.
- Loại duplicate source of truth.
- Đồng bộ tài liệu với code đã kiểm chứng.

Tài liệu dự kiến:

- `README.md`
- `docs/current_architecture.md`
- `docs/changelog.md`
- `docs/git_diff.md`
- `docs/agent_activities.md`

Chỉ ghi trạng thái đã kiểm chứng; không mô tả P1 chưa làm như tính năng hoàn tất.

---

## 9. Quy trình bắt buộc cho từng checkpoint tiếp theo

### 9.1. Trước khi sửa

1. Đọc RULES và skill bắt buộc.
2. Chạy:

```powershell
git status --short
git show -s --format="%H %s" HEAD
```

3. Xác nhận HEAD vẫn dựa trên hoặc chứa checkpoint `b850b72`.
4. Ghi baseline `runs/`:

```powershell
$files = Get-ChildItem -LiteralPath runs -Recurse -File
$files.Count
($files | Measure-Object Length -Sum).Sum
($files | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
```

5. Xác định file ownership.
6. Nêu rõ task nào đang `in_progress`.

### 9.2. Khi sửa

- Dùng `apply_patch`.
- Không sửa file người dùng ngoài scope.
- Không tạo abstraction không có consumer.
- Mỗi patch phải kèm test tái hiện lỗi hoặc contract test.
- Không gọi API thật.
- Không dùng `runs/` làm output test.
- Dùng `tmp_path`, `TemporaryDirectory` hoặc workspace root tạm.
- Nếu sandbox Windows khóa `tmp_path`, chạy test ngoài sandbox sau khi được phê duyệt; không đổi test để né lỗi ACL.

### 9.3. Sau mỗi patch

1. Chạy test nhỏ nhất liên quan.
2. So `runs/` trước/sau.
3. Kiểm tra process nền.
4. Dọn đúng artifact tạm do patch tạo.
5. Báo:

```text
Pn — HOÀN TẤT
- Thay đổi:
- Test:
- API thật: Không
- runs/: Không đổi
- Rủi ro còn lại:
- Task tiếp theo:
```

6. Không chuyển task nếu test chưa xanh.

### 9.4. Trước commit

Stage bằng danh sách file tường minh.

Không dùng:

```powershell
git add .
git add -A
```

Kiểm tra:

```powershell
git diff --cached --name-status
git diff --cached --check
```

Xác nhận không stage:

- `examples/`
- `skills/moment/va-natural/`
- tài liệu phản biện của người dùng

Commit riêng cho từng checkpoint P1.

---

## 10. Điều kiện dừng khẩn cấp

Dừng ngay và báo người dùng nếu:

- `runs/` thay đổi ngoài dự kiến.
- Test gọi API thật.
- Publish chạm style thật trong test.
- Worktree xuất hiện thay đổi không xác định ownership.
- Cần sửa dữ liệu/style của người dùng để test pass.
- Cần thay provider hoặc model Voice Lab.
- Cần dùng OpenAI hoặc Antigravity trong Voice Lab.
- Patch yêu cầu thay đổi contract lớn hơn task đã phê duyệt.
- Test không xanh sau hai vòng sửa cục bộ và cần mở rộng scope.

Không tự cleanup dữ liệu người dùng khi phát hiện bất thường.

---

## 11. Chỉ dẫn provider

### Voice Lab

- Chỉ Gemini API.
- Không OpenAI API.
- Không Antigravity Bridge.
- Inject fake Gemini callable trong test.
- Structured output phải qua schema/parser.
- Prompt phải cô lập sample/answer/content brief không tin cậy.

### Workflow viết blog

- Có thể dùng OpenAI, Gemini hoặc Antigravity theo router/config.
- Antigravity là local bridge, không phải API call.
- Telemetry phải dùng `api_attempted` và `api_called`.
- Không dùng provider metadata làm bằng chứng duy nhất cho network call.

---

## 12. Rủi ro còn lại không chặn sử dụng

- Envelope Markdown không thể phân biệt một heading H2 nội bộ với “section dư” tùy ý; parser vì vậy khóa duy nhất hai heading contract `Artifact/Handoff` và cho phép H2 trong Artifact.
- `docs/2026-07-27-voice-lab-refactor-plan.md` có blank-line-at-EOF trong thay đổi ngoài P0.
- `.pytest_cache` trên Windows từng phát warning quyền truy cập; không ảnh hưởng regression ngoài sandbox.

Không cần sửa các mục này để chạy workflow hiện tại.

---

## 13. Điểm tiếp tục được khuyến nghị

Không còn task P1. Chỉ bắt đầu P2 hoặc tính năng mới khi người dùng phê duyệt phạm vi mới.

---

## 14. Tóm tắt ngắn cho agent tiếp quản

```text
P0 và P1 đã hoàn tất.
120 tests + 4 parser subtests pass; không API thật; runs/ bất biến.
Worktree còn thay đổi nội dung/style của người dùng, không được reset hoặc commit lẫn.
Voice Lab Gemini-only.
Không còn task P1; task tiếp theo cần phạm vi mới được người dùng phê duyệt.
```

---

## 15. Báo cáo Audit Cross-Review (Claude Opus 4.6)

> **Reviewer:** Claude Opus 4.6 (Thinking) | **Ngày:** 2026-07-28  
> **Plan:** [2026-07-27-voice-lab-refactor-plan-final.md](file:///D:/Nghiên cứu AI/write_blog/docs/2026-07-27-voice-lab-refactor-plan-final.md)  
> **Handoff:** [2026-07-27-project-progress-agent-handoff.md](file:///D:/Nghiên cứu AI/write_blog/docs/2026-07-27-project-progress-agent-handoff.md)  
> **Phạm vi:** Voice Lab refactor (P0) + P1 consolidation | **Test:** 111 passed, 0 failed  
> **Phương pháp:** 4 audit subagent song song + manual cross-verification trên source code

### 15.1. 🔍 ĐỐI CHIẾU SỰ TUÂN THỦ (PLAN VS IMPLEMENTATION)

| Mã Task | Tên Task (Trong PLAN) | Trạng thái | Ghi chú kỹ thuật nhanh |
| :--- | :--- | :--- | :--- |
| §3.2 | `DimensionProfile` nested model 8 trường | ✅ Đạt | [models.py:35-43](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L35-L43) — đúng 8 trường, `StrictModel(extra="forbid")` |
| §3.3 | `EvidenceClaim` v2 (`exact_quote`, `stance`, `rejection_reason`) | ✅ Đạt | [models.py:68-84](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L68-L84) — có compat alias `quote` → `exact_quote` |
| §3.4 | `StyleProfile` bổ sung (`analysis_status`, history, `base_style_slug`) | ✅ Đạt | [models.py:129-157](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L129-L157) — `enforce_publish_state` validator đúng |
| §3.5 | `AnalysisResult` / `AnalysisError` 4 mã lỗi | ✅ Đạt | [models.py:173-204](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L173-L204) — đủ 4 error code |
| §3.1 | `schema_version=2`, `revision`, reader v1→v2 | ✅ Đạt | L10 `SCHEMA_VERSION=2`, L130 `Literal[2]`, `migrate_profile_data` idempotent |
| §2.2 | Tách `prompts.py`, `parser.py`, `publisher.py` | ✅ Đạt | 3 file mới tồn tại + thêm 3 sub-module facade: `interview_routing.py`, `profile_patch.py`, `calibration.py` |
| §4.1 | Tách analyzer thành orchestrator thuần | ✅ Đạt | [analyzer.py](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/analyzer.py) — gọi `prompts` + `parser`, không parse trực tiếp |
| §4.2 | Adaptive routing theo token budget | ✅ Đạt | L29 `DEFAULT_CONTEXT_TOKENS=200_000`, L40-46 env-var override, L220-223 so sánh `total_tokens <= input_budget` |
| §4.3 | Confidence tính bằng code, đúng công thức + trần | ✅ Đạt | [parser.py:86-104](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/parser.py#L86-L104) — `0.45*cov + 0.35*cons + 0.20*qv`, cap 0.55/0.75/0.90 |
| §4.4 | An toàn prompt injection: JSON serialize, không `sanitize_sample` | ✅ Đạt | [prompts.py:78](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/prompts.py#L78) `json.dumps(samples)`, AN TOÀN block; `sanitize_sample()` xóa sạch (grep=0) |
| §5.1 | Prompt 6 khối + `temperature=0.1` + structured output | ✅ Đạt | Prompt đủ VAI TRÒ/AN TOÀN/NHIỆM VỤ/OUTPUT; `_call_structured` L58 `temperature=0.1` + `response_mime_type` + `response_schema` |
| §5.2 | Tổng hợp multi-pass: chỉ evidence verified | ✅ Đạt | [prompts.py:109-134](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/prompts.py#L109-L134) — không gửi lại raw samples |
| §5.3 | Interview patch qua Gemini + review trước khi áp dụng | ✅ Đạt | `propose_interview_patch` → `apply_interview_patch(confirmed=True)` — raises ValueError if `confirmed=False` |
| §5.4 | A/B: `variant_amplified`/`restrained`, `temperature=0.6`, no bias | ✅ Đạt | [calibration.py:63](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/calibration.py#L63) `temperature=0.6`, [calibration.py:106-111](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/calibration.py#L106-L111) random shuffle |
| §6.1 | Chọn dimension yếu, max 3/vòng | ✅ Đạt | [interview_routing.py:46,68](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/interview_routing.py#L46) — `min(max_questions, 3)` |
| §6.2 | `CalibrationSession` lưu `shuffle_mapping` | ✅ Đạt | [models.py:113-121](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L113-L121) — đầy đủ 7 trường + `__iter__` compat |
| §6.2 | `apply_calibration_selection` cập nhật strength/examples/history | ⚠️ Sai lệch nhẹ | [calibration.py:121-162](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/calibration.py#L121-L162) — cập nhật profile đúng nhưng **không tự gọi `compile_style`**. Plan yêu cầu "rồi compile lại đúng các agent bị ảnh hưởng". Thực tế caller (UI) phải tự compile — chấp nhận được kiến trúc nhưng lệch literal plan |
| §7.1 | Bỏ `_load_base_skill` duyệt `iterdir()` | ✅ Đạt | [compiler.py:110-121](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L110-L121) — đường dẫn xác định `skills/{mode}/{base_style_slug}/{filename}` |
| §7.2 | Canonical IR full-template overlay, deep-copy, giữ invariant | ✅ Đạt | [compiler.py:246](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L246) `copy.deepcopy(base)`, invariant check L261-263; `prompt`/`style_rules` đã xóa; `extra="forbid"` qua `StrictModel` |
| §7.3 | Phát hiện xung đột `do`∩`avoid`, overlay sửa invariant | ✅ Đạt | [compiler.py:155-162](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L155-L162), L261-263 |
| §7.4 | Overrides: bỏ `resolve_conflict_with_llm`, `MergeResult` explicit | ✅ Đạt | [overrides.py](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/overrides.py) — `IR_LEVEL_INVARIANTS`, three-way merge, `MergeConflict` |
| §8.1 | Migration: `dna=None`, `analysis_status="incomplete_legacy_data"` | ✅ Đạt | [migration.py:53-54](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/migration.py#L53-L54), L118-120, L173 — không còn `VoiceDNA()` rỗng |
| §8.2 | Archive: `schema_version=2`, v1 migration, reject future, checksum | ✅ Đạt | [archive.py:50](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/archive.py#L50), L83-87, L92-98, path traversal L17-19 |
| §8.3 | Publish Safety Pipeline: staging→validate→backup→atomic→rollback | ✅ Đạt | [publisher.py:162-231](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L162-L231) — tombstone pattern, rollback on exception |
| §8.3 | Profile chưa `confirmed`/`complete` bị chặn | ✅ Đạt | [publisher.py:43-46](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L43-L46) |
| §8.3 | Protected style không bị ghi đè | ✅ Đạt | [publisher.py:183-188](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L183-L188) |
| §2.3 | `gemini_client.py`: `response_mime_type`/`response_schema` SDK+REST | ✅ Đạt | [gemini_client.py:149-221](file:///D:/Nghiên cứu AI/write_blog/engine/gemini_client.py#L149-L221) — cả SDK lẫn REST path |
| §2.3 | Không retry chồng tại analyzer | ✅ Đạt | `_call_structured` gọi 1 lần; test xác nhận `calls["count"]==1` |
| §12 | Không có OpenAI/Antigravity import trong voice_lab | ✅ Đạt | grep xác nhận 0 match cả hai pattern |
| §10 | Test bao phủ đầy đủ 11 category | ✅ Đạt | [test_voice_lab.py](file:///D:/Nghiên cứu AI/write_blog/tests/test_voice_lab.py) — 44 test functions, 0 API thật, 0 ghi `runs/` |
| §10.5 | Regression: deep + moment mode compile/publish | ✅ Đạt | `test_moment_mode_compiles_and_publishes_all_required_agents` |
| §9 GĐ6 | Cập nhật `current_architecture.md` | ⚠️ Thiếu sót | File đã cập nhật `prompts.py`, `parser.py`, `publisher.py` nhưng **thiếu 3 sub-module** (`interview_routing.py`, `profile_patch.py`, `calibration.py`) + **thiếu 7 workflow module** (`workflow_contracts.py`, `workflow_execution.py`, `workflow_persistence.py`, `workflow_context.py`, `workflow_resolution.py`, `workflow_artifacts.py`, `workflow_learning.py`) + **thiếu `style_contracts.py`, `style_repository.py`** |

**Tổng kết:** 30/32 task **Đạt**, 1 **Sai lệch nhẹ** (chấp nhận được), 1 **Thiếu sót** (docs chưa phản ánh kiến trúc mới đầy đủ).

### 15.2. ⚡ TỐI ƯU HÓA WORKFLOW & KIẾN TRÚC

- **Lỗi crash / bảo mật nghiêm trọng:** Không phát hiện.
  - Gemini lỗi → `AnalysisError` có `retryable` flag.
  - Path traversal → chặn bằng `_safe_member()` (archive) + `validate_slug()` (publisher).
  - Prompt injection → JSON serialize + security block trong prompt.
  - API key không leak qua log hoặc error message.
  - Quota guardrail: reject `input_too_large` trước khi gọi API ([analyzer.py:61-72](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/analyzer.py#L61-L72)).

- **Lệch pha Data Contract:**
  - `CanonicalIR.output_contract`, `handoff_contract`, `context_policy` dùng `Optional[Dict[str, Any]]` — **đã sửa** từ `Any` theo audit trước. Legacy scalar được normalize qua `_contract_object()` ([compiler.py:197-203](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L197-L203)). Chấp nhận được.
  - `prompt` và `style_rules` dư thừa trong `CanonicalIR` — **đã xóa**. `effective_skill` là nguồn duy nhất. ✅
  - Tất cả strict model dùng `extra="forbid"` qua `StrictModel` base class. ✅

- **Trùng lặp / Thừa thãi:**
  - ~~`_profile_confidence()` trùng giữa `analyzer.py` và `interview.py`~~ → **ĐÃ SỬA**: gom vào `compute_profile_confidence()` tại [models.py:160-170](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L160-L170), dùng chung bởi `analyzer.py`, `calibration.py`, `profile_patch.py`. ✅
  - ~~`sanitize_sample()` dead code~~ → **ĐÃ XÓA**: grep = 0 match. ✅
  - ~~`INVARIANT_FIELDS` khai báo 2 lần tên giống~~ → **ĐÃ SỬA**: đổi thành `SKILL_LEVEL_INVARIANTS` ([compiler.py:86](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L86)) và `IR_LEVEL_INVARIANTS` ([overrides.py:8](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/overrides.py#L8)). ✅
  - ~~Unreachable `else` clause trong migration.py~~ → **ĐÃ SỬA**: audit xác nhận tất cả branch đều reachable. ✅
  - **Còn lại:** `current_architecture.md` chưa liệt kê đủ module mới (xem task §9 GĐ6 ở trên).

### 15.3. 🛠️ VECTOR TINH CHỈNH CODEBASE (REFACTOR VECTORS)

---

**Vị trí:** [current_architecture.md](file:///D:/Nghiên cứu AI/write_blog/docs/current_architecture.md) — directory tree L33-44  
**Vấn đề:** Thiếu 12 module mới: `interview_routing.py`, `profile_patch.py`, `calibration.py` (voice_lab) + `workflow_contracts.py`, `workflow_execution.py`, `workflow_persistence.py`, `workflow_context.py`, `workflow_resolution.py`, `workflow_artifacts.py`, `workflow_learning.py`, `style_contracts.py`, `style_repository.py` (engine). Tài liệu không phản ánh kiến trúc thực tế → agent kế tiếp sẽ làm việc dựa trên bản đồ sai.  
**Giải pháp Refactor gọn:**
```diff
 │       ├── interview.py      # Interview patch + Blind A/B có shuffle mapping
+│       ├── interview_routing.py  # Chọn dimension yếu, sinh câu hỏi (max 3/vòng)
+│       ├── profile_patch.py      # Propose & apply interview patch có xác nhận
+│       ├── calibration.py        # Blind A/B session + apply selection
 │       ├── compiler.py       # Full-template overlay qua Adjacency Matrix
```

---

**Vị trí:** [compiler.py:110-115](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L110-L115) — `_load_base_skill` legacy fallback  
**Vấn đề:** Khi `mode == "deep"`, nếu `skills/{mode}/{slug}/{file}` không tồn tại thì fallback sang `skills/{slug}/{file}` (đường dẫn cũ). Plan §7.1 nói "fail-fast" khi thiếu base. Fallback này âm thầm load file từ thư mục không chuẩn, có thể gây nhầm lẫn khi migrate skill layout.  
**Giải pháp Refactor gọn:**
```python
# Thêm warning log khi dùng legacy path:
import logging
_log = logging.getLogger(__name__)
if not candidate.exists() and mode == "deep":
    legacy = resolve_path(f"skills/{base_style_slug}/{filename}")
    if legacy.exists():
        _log.warning("Legacy skill path %s; nên migrate sang skills/%s/%s/", legacy, mode, base_style_slug)
        candidate = legacy
```

---

**Vị trí:** [calibration.py:141](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/calibration.py#L141) — `apply_calibration_selection`  
**Vấn đề:** Sau khi user chọn A/B, `dimension.confidence` bị set cứng `max(current, 0.95)` bất kể evidence gốc có bao nhiêu. Plan §4.3 nói calibration "có thể nâng tối đa 0.95, nhưng phải lưu provenance". Hàm luôn nâng lên 0.95 thay vì nâng từ giá trị hiện tại một khoảng hợp lý. Nếu evidence gốc chỉ có confidence 0.3, một lần chọn A/B không nên nhảy thẳng lên 0.95.  
**Giải pháp Refactor gọn:**
```python
# Nâng confidence tối đa 0.2 mỗi lần, ceil 0.95:
calibration_boost = 0.20
dimension.confidence = min(0.95, dimension.confidence + calibration_boost)
```

---

**Vị trí:** [analyzer.py:35-37](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/analyzer.py#L35-L37) — `estimate_tokens`  
**Vấn đề:** Token estimator dùng `len(text) // 4` — heuristic phù hợp cho Latin text nhưng **quá thấp** cho tiếng Việt (UTF-8 multi-byte, mỗi từ ~2-4 token BPE, mỗi ký tự UTF-8 ~2-3 bytes). Ước lượng thấp → routing sai (chọn single-pass khi thực tế vượt budget).  
**Giải pháp Refactor gọn:**
```python
def estimate_tokens(text: str) -> int:
    """Conservative estimate cho Vietnamese text (UTF-8 heavy)."""
    byte_len = len(text.encode("utf-8"))
    return max(1, (byte_len + 2) // 3)  # ~3 bytes/token thay vì 4 chars
```

---

**Vị trí:** [publisher.py:213-220](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L213-L220) — rollback exception handler  
**Vấn đề:** Nếu `os.replace(staging_dir, runtime_dir)` raise OSError nhưng `runtime_dir` đã bị xóa (tombstone đã swap), handler cố `shutil.rmtree(runtime_dir)` trước khi restore tombstone. Nếu `runtime_dir` không tồn tại ở thời điểm đó, `shutil.rmtree` dùng `ignore_errors=True` nên không crash, nhưng logic ưu tiên sai: nên restore tombstone **trước** rồi mới cleanup.  
**Giải pháp Refactor gọn:**
```python
except Exception:
    # Restore trước, cleanup sau:
    if runtime_moved and tombstone.exists():
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir, ignore_errors=True)
        os.replace(tombstone, runtime_dir)
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    raise
```

---

> [!IMPORTANT]
> **Ưu tiên sửa:** (1) `current_architecture.md` — ảnh hưởng mọi agent kế tiếp, (2) `estimate_tokens` — ảnh hưởng routing cho Vietnamese text, (3) `calibration confidence jump` — ảnh hưởng chất lượng profile. Các vector còn lại là cải thiện phòng vệ (defense-in-depth), không chặn workflow hiện tại.

---

## 16. Kết quả triển khai phản biện GPT-5.6 Sol

**Ngày:** 2026-07-28  
**Trạng thái:** Hoàn tất

- Đồng bộ `current_architecture.md` với toàn bộ module engine, Voice Lab và UI đã tách.
- Xóa legacy compiler fallback; base skill chỉ được đọc từ `skills/<mode>/<style>/`.
- Thay token heuristic bằng estimator Unicode bảo thủ; chunk tuân thủ estimated budget.
- Giữ confidence `0.95` cho xác nhận A/B trực tiếp theo plan, đồng thời lưu before/after và provenance.
- Giữ rollback chính hiện hành; nếu restore thứ cấp thất bại, bảo toàn tombstone và trả `PublishRollbackError`.
- Kiểm chứng: **124/124 test pass**, 4 parser subtest pass; không API thật; `runs/` bất biến.
