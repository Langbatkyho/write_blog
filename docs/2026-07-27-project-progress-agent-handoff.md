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
