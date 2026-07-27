# Kế hoạch triển khai RULES & SKILL Refactor

**Ngày:** 27/07/2026
**Trạng thái:** Sẵn sàng triển khai
**Nguồn:** `.agents/AGENTS.md`, skill `agentic-workflow-architect`, phản biện Gemini 3.1 Pro, Claude Opus 4.6 và GPT-5.6 Sol.

## 1. Mục tiêu

- Mọi test/dry-run/preview không gọi API và không ghi vào `runs/`.
- Flow là nguồn chân lý cho stage, thứ tự, context policy và output filename.
- Orchestrator chỉ điều phối; contract, context, execution và persistence tách biệt.
- Run ID chống va chạm; metadata phản ánh đúng persistence, API và trạng thái.
- Voice Lab giữ Gemini-only, prompt/parser fail-closed, publish nguyên tử.
- `interview.py` tách routing, patch và calibration; trạng thái pending/applied rõ ràng.
- `ui/app.py` tách state/controller/renderer mà không redesign luồng nghiệp vụ.
- Giữ facade tương thích cho các public API hiện tại trong giai đoạn chuyển tiếp.

## 2. Nguồn chân lý và ranh giới

| Contract | Nguồn chân lý | Consumer |
|---|---|---|
| Workflow runtime | `WorkflowDefinition` đọc từ `flow/*.yaml` | execution, learning, router, publisher |
| Voice DNA | `StyleProfile` schema v2 | interview, calibration, compiler |
| Artifact biên dịch | `CanonicalIR` | overrides, publisher, UI preview |
| Run lifecycle | `RunRequest`, `RunResult`, `RunMetadata` | CLI, UI, repository |
| Provider telemetry | descriptor tại router boundary | execution, metadata |

Quy tắc:

- Skill YAML mô tả nhiệm vụ/nội dung; không định nghĩa lại output filename trái Flow.
- Compiler bảo toàn invariant từng artifact, gồm `workflow_order` và `context_policy`.
- Publisher đối chiếu tập file/tham chiếu Flow và invariant snapshot trước atomic replace.
- Full compile mới được publish; incremental compile chỉ dùng preview/audit.

## 3. Phạm vi refactor

### 3.1. Workflow engine — P0/P1

Tạo:

- `engine/workflow_contracts.py`: Pydantic/dataclass contract cho Flow, Step, RunRequest, RunResult, StageResult, metadata.
- `engine/workflow_context.py`: prompt/context assembly thuần.
- `engine/workflow_execution.py`: thực thi stage, failure semantics và telemetry.
- `engine/workflow_persistence.py`: Run ID, safe path, atomic metadata/checkpoint và repository.

Giữ:

- `engine/workflow.py` là compatibility facade cho `run_workflow()`, `preview_workflow()`, `run_learning_loop()` và helper công khai cũ.

Thay đổi bắt buộc:

- `dry_run=True` mặc định `persist=False`, `api_called=False`.
- `preview_workflow()` trả kết quả in-memory, không tạo run directory.
- Run thật dùng timestamp microsecond + UUID ngắn, `exist_ok=False`.
- Metadata tối thiểu: `run_source`, `persisted`, `api_called`, `status`, telemetry từng stage.
- Validate trước execution: mode, stage ID duy nhất, output/handoff path an toàn và duy nhất, context reference hợp lệ, Flow output khớp Skill output.
- Stage lỗi có `status=failed`; không chuyển lỗi thành artifact hợp lệ cho downstream.
- Checkpoint `step_outputs.json` và metadata được ghi atomic sau mỗi stage thành công.
- Parser production strict; compatibility fallback chỉ khi gọi tường minh và phải trả warning/status.

### 3.2. Router/provider — P1

- Validate fallback client kể cả khi không có `--client-map`.
- Validate stage trong client map sau khi load Flow.
- Gắn descriptor `provider/model/api_capable` tại router boundary.
- Execution ghi telemetry thực tế theo stage; không suy đoán provider từ `__name__`.
- Không dùng `get_openai_options()` làm nguồn model chung cho provider khác.

### 3.3. Voice Lab compiler/publisher/prompt — P0/P1

- Audit `prompts.py`, `parser.py`, `publisher.py` theo ma trận:
  - contract/schema parity;
  - error path explicit;
  - happy + malformed tests;
  - I/O/path/version constants có nguồn tập trung.
- Prompt phải cô lập sample không tin cậy, giữ quote provenance và kiểm soát token.
- Publisher yêu cầu full compile có đúng tập file Flow; không chấp nhận artifact dư.
- Invariant bắt buộc phải hiện diện và khớp; xóa key cũng là lỗi.
- Snapshot/base hash được kiểm tra trước replace.
- Path safety và rollback là P0.

### 3.4. Voice Lab interview — P1

Tạo:

- `engine/voice_lab/interview_routing.py`: chọn dimension/câu hỏi.
- `engine/voice_lab/profile_patch.py`: tạo, xác nhận và áp patch.
- `engine/voice_lab/calibration.py`: sinh phiên A/B, hidden mapping và áp lựa chọn.

Giữ:

- `engine/voice_lab/interview.py` là facade tương thích.

Contract:

- Proposal/pending không được làm đổi `StyleProfile`.
- Chỉ hành động confirmed/applied mới tăng revision và ghi history/provenance.
- Gemini callable được inject tại boundary; không thêm OpenAI/Antigravity.

### 3.5. UI — P1

Tạo:

- `ui/state.py`: khóa, mặc định và transition của session state.
- `ui/controllers/workflow_controller.py`: preview/run use case.
- `ui/controllers/voice_lab_controller.py`: analyze/interview/calibrate/compile/publish use case.
- `ui/views/`: renderer theo tab.

Thay đổi trước:

- Xóa `runs/temp_dry_run_input.md`.
- Workbench dùng `preview_workflow()` in-memory.
- UI chỉ gọi controller; không tự xây path, transaction hoặc sửa profile domain.
- Giữ layout 4 tab và wizard 5 bước.

### 3.6. Learning/style service — P1/P2

- Learning lấy stage list từ `WorkflowDefinition`.
- Đổi offline output thành diagnostic, không trình bày như kết luận AI đã học.
- Thêm evidence builder và token budget trước online call.
- Tách style registry/contract/repository/service.
- Rename/save theo staging → validate → replace → rollback.
- Không tự động xóa style; delete dùng backup/trash có khả năng phục hồi.

## 4. Thứ tự triển khai

### Giai đoạn 0 — Baseline và guardrail

1. Ghi snapshot chỉ đọc của `runs/`.
2. Sửa test workflow dùng `tmp_path`/`TemporaryDirectory`.
3. Thêm test bất biến `runs/` và fake API.

### Giai đoạn 1 — Contract

1. Tạo `WorkflowDefinition`, `StepDefinition`.
2. Tạo `RunRequest`, `RunResult`, `StageResult`, metadata schema.
3. Thêm validator path/reference/duplicate/Flow–Skill.
4. Thêm strict parser mode.

### Giai đoạn 2 — Persistence và execution

1. Tạo run repository và ID chống va chạm.
2. Tách preview khỏi persisted run.
3. Tách execution/context assembly.
4. Thêm atomic checkpoint, lifecycle và failure semantics.
5. Giữ `run_workflow()` facade.

### Giai đoạn 3 — Provider và learning

1. Descriptor/telemetry theo stage.
2. Validate client map bằng stage registry.
3. Learning đọc Flow contract và đo context.
4. Chuẩn hóa offline diagnostic.

### Giai đoạn 4 — Voice Lab

1. Siết compiler/publisher invariant và full-compile contract.
2. Audit prompt/parser.
3. Tách interview routing/patch/calibration.
4. Bổ sung migration và malformed-output tests.

### Giai đoạn 5 — UI và style service

1. Thay workbench bằng preview in-memory.
2. Tách state/controller rồi mới tách renderer.
3. Transaction hóa rename/save style.
4. Chạy AppTest và kiểm tra trực quan.

### Giai đoạn 6 — Regression và tài liệu

1. Test nhỏ theo module, sau đó toàn bộ suite.
2. `compileall`, import/dead-code audit, `git diff --check`.
3. So sánh snapshot `runs/`; xác nhận không gọi API.
4. Cập nhật README, architecture, changelog, git diff và agent activities.

## 5. Ưu tiên kiểm thử

### P0

- `runs/` bất biến khi test/dry-run/preview.
- Path traversal/absolute path/duplicate output bị từ chối.
- Run ID không va chạm, không ghi đè.
- Metadata đúng `persisted/api_called/status`.
- Publish rollback; invariant thiếu hoặc sai bị từ chối.
- Full compile phải đúng tập file Flow.

### P1

- Legacy thiếu profile khác profile corrupt.
- Pending khác applied cho interview/calibration.
- Stage failure không truyền artifact giả xuống downstream.
- Flow–Skill mismatch và client-map stage typo fail-fast.
- Malformed prompt response fail-closed.

### P2

- Provider/model/duration telemetry.
- Token budget learning và offline diagnostic wording.
- UI visual regression ngoài AppTest smoke.

## 6. Backward compatibility

- `run_workflow()` vẫn trả `Path` khi persist; dry-run cũ muốn artifact phải truyền output root tạm hoặc dùng API preview mới.
- Các helper đang được import từ `engine.workflow` tiếp tục re-export.
- `interview.py` tiếp tục re-export public functions.
- Không duy trì fallback parser im lặng cho production; compatibility phải opt-in và có warning.
- Không đổi Flow nghiệp vụ Deep/Moment hoặc nội dung style người dùng trong refactor nền tảng.

## 7. Rủi ro và kiểm soát

- **Dirty worktree:** không sửa các style/example đang có thay đổi của người dùng.
- **Run data:** chỉ đọc snapshot; không cleanup hoặc sửa run cũ.
- **Scope lớn:** merge theo từng contract có test, tránh big-bang.
- **UI state drift:** controller được đưa vào trước renderer; AppTest sau từng mốc.
- **Circular dependency:** contract không import UI/provider; publisher không import workflow execution.
- **Gemini quota:** toàn bộ test dùng fake/stub; không gọi API thật.

## 8. Tiêu chí nghiệm thu

- Tất cả mục P0 và P1 có test chứng minh.
- `workflow.py`, `interview.py`, `ui/app.py` trở thành facade/composition root, không còn logic domain chính.
- Test/dry-run/preview không tạo artifact trong `runs/`.
- Không API ngoài dự kiến; Voice Lab vẫn Gemini-only.
- Publish và style transaction rollback đúng.
- Không dead architecture, duplicate source of truth hoặc import không dùng do refactor tạo ra.
- Toàn bộ regression pass; AppTest pass; tài liệu đồng bộ với code.

## 9. Ngoài phạm vi

- Thêm OpenAI API cho Voice Lab.
- Dùng Antigravity Bridge trong Voice Lab.
- Redesign UI/UX lớn.
- Thay đổi vai trò hoặc số lượng agent Deep/Moment.
- Tự động áp dụng learning suggestion vào Skill YAML.
- Sửa nội dung style/example đang có thay đổi ngoài tác vụ.
