# Tóm tắt RULES, SKILL và kế hoạch refactor 3 module trọng điểm

**Ngày:** 27/07/2026  
**Mục đích:** Tài liệu ngắn để tham vấn chuyên gia trước khi triển khai refactor tiếp theo.

## 1. RULES và SKILL đã tạo

- Đã thiết lập bộ quy chuẩn vận hành agentic trong `.agents/AGENTS.md`.
- Đã tạo skill kiến trúc `agentic-workflow-architect` để dùng khi sửa workflow, orchestrator, prompt contract, schema, provider/routing, persistence, publish và UI liên quan.
- Trục chính của RULES:
  - `runs/` là dữ liệu nghiệp vụ của người dùng, không dùng làm thư mục tạm cho test/dry-run.
  - Test/dry-run/smoke/UI validation phải cô lập vào `tmp_path` hoặc output root tạm.
  - Voice Lab hiện chỉ dùng Gemini API; không tự ý thêm OpenAI hay Antigravity Bridge.
  - Run metadata phải phân biệt rõ `run_source`, `persisted`, `api_called`.
  - Entrypoint/orchestrator chỉ điều phối; không ôm prompt, parser, formatter, persistence hay logic domain chi tiết.
  - Khi sửa workflow/agent/schema/prompt/router/publisher, phải đọc `docs/current_architecture.md`, `docs/workflow_analysis.md` và skill kiến trúc tương ứng.

## 2. Ý nghĩa thực tế của RULES và SKILL

- Chặn tái diễn lỗi artifact test/dry-run chui vào `runs/`.
- Giữ contract rõ ràng giữa UI, engine và prompt.
- Ép refactor theo hướng tách trách nhiệm, có thể kiểm thử, có backward compatibility khi cần.
- Giảm nguy cơ “logic ngầm” nằm lẫn trong UI hoặc module orchestrator.

## 3. Kế hoạch refactor 3 module trọng điểm

### 3.1. `ui/app.py` — P0

- Vấn đề chính: module quá nhiều trách nhiệm.
  - Bootstrap UI.
  - Quản lý session state.
  - Điều khiển 5 bước Voice Lab.
  - CRUD, editor, workbench, publish, preview.
  - Có luồng dry-run từng ghi input tạm vào `runs/`.
- Hướng refactor:
  - Tách `ui/state.py` cho state chuẩn hóa.
  - Tách controller/use case riêng cho Voice Lab.
  - Tách renderer cho từng tab/bảng điều khiển.
  - Đổi workbench sang luồng preview in-memory, không viết file tạm vào `runs/`.
  - Giữ UI/flow hiện tại, chưa redesign lớn.
- Điểm cần giữ:
  - AppTest vẫn phải chạy.
  - Không phá tương thích hành vi cũ nếu chưa có lý do nghiệp vụ.

### 3.2. `engine/workflow.py` — P0

- Vấn đề chính: gom quá nhiều mảng vào một file.
  - Execution.
  - Persistence.
  - Context assembly.
  - Run logging.
  - Dry-run handling.
  - Workflow/skill resolution.
- Hướng refactor:
  - Giữ `engine/workflow.py` làm compatibility facade.
  - Tách thành các khối rõ ràng:
    - contracts
    - context assembly
    - execution
    - persistence
  - Bổ sung request/result model rõ ràng cho run/predict/preview.
  - Tách preview khỏi path tạo run thật.
  - Làm sạch semantics của dry-run: không API, không persist, không đụng `runs/`.
- Điểm cần giữ:
  - API cũ vẫn hoạt động để giảm rủi ro tích hợp.
  - Metadata phải nói thật về việc có gọi API hay không.

### 3.3. `engine/voice_lab/interview.py` — P1

- Vấn đề chính: module đang ôm đồng thời:
  - routing phỏng vấn,
  - patch áp vào profile,
  - A/B calibration,
  - và một phần glue gọi Gemini.
- Hướng refactor:
  - Tách routing interview, patch application và calibration thành các lớp/module riêng.
  - Tách trạng thái “đang chờ user chọn” khỏi trạng thái “đã áp dụng”.
  - Dùng boundary inject Gemini callable thay vì để low-level module tự ôm cứng client.
  - Giữ cơ chế blind mapping A/B nhưng làm rõ lưu vết và provenance.
- Điểm cần giữ:
  - Public facade cũ nên còn, để test/consumer hiện tại không vỡ ngay.
  - Chỉ Gemini-only trong phạm vi Voice Lab hiện tại.

## 4. Thứ tự triển khai đề xuất

1. Chốt guardrail cho dry-run/test để chặn ghi nhầm vào `runs/`.
2. Tách `workflow.py` theo facade + submodules.
3. Tách `interview.py` theo routing/patch/calibration.
4. Tách `ui/app.py` theo state/controller/tab renderer.
5. Cập nhật docs và regression tests sau mỗi mốc.

## 5. Điểm cần chuyên gia soi kỹ

- Có nên giữ public API cũ bao lâu trước khi cắt bỏ?
- Preview/dry-run nên trả về model nào để UI và CLI dùng chung mà không phải viết file tạm?
- `interview.py` nên tách thành 2 hay 3 module con để đủ sạch nhưng chưa quá vụn?
- Ranh giới nào nên đặt giữa controller UI và workflow facade để tránh lặp logic?

## 6. Đánh giá mở rộng codebase workflow viết blog

### 6.1. P0 — Dry-run/test vẫn ghi vào dữ liệu nghiệp vụ

**Bằng chứng**

- `run_workflow()` tạo `run_dir`, ghi `input.md` và `metadata.json` trước khi xử lý nhánh `dry_run`.
- `run_learning_loop()` vẫn tạo thư mục `learning/<mode>/<timestamp>` và ghi báo cáo khi `dry_run=True`.
- `tests/test_moment_blog_mode.py` dùng trực tiếp `engine/config.example.yaml`, trong đó `workflow.log_dir: runs`.

**Cần sửa**

- Thêm contract thực thi rõ ràng: `RunRequest(output_root, persist, run_source, dry_run)`.
- `dry_run=True` mặc định phải đồng nghĩa: `api_called=False`, `persisted=False`.
- Test dùng `tmp_path`/`TemporaryDirectory` và config tạm; thêm regression test xác nhận `runs/` không đổi.
- Tách `preview_workflow()` trả kết quả in-memory khỏi `run_workflow()` có persistence.

### 6.2. P0 — Contract Flow–Skill–Artifact chưa có một nguồn chân lý

**Bằng chứng**

- Flow khai báo `step.output`; Skill YAML đồng thời khai báo `output.name`.
- `derive_artifact_file_contents()` tự suy diễn tên/section; nếu tên Flow không có trong kết quả, `run_workflow()` ghi thêm một bản artifact thay vì báo lệch contract.
- Tên file từ Flow/Skill được nối trực tiếp vào `run_dir` nhưng chưa có validator bảo đảm là đường dẫn con an toàn.
- `validate_style_contract()` nuốt lỗi ngoài `ValueError`, nên YAML/contract hỏng có thể bị bỏ qua.

**Cần sửa**

- Chọn Flow làm nguồn chân lý về stage/order/context/output filename; Skill chỉ định schema nội dung.
- Tạo `WorkflowDefinition`/`StepDefinition` fail-closed và validator trước execution.
- Bắt buộc `step.output == skill.output.name` nếu vẫn giữ cả hai trường trong giai đoạn chuyển tiếp.
- Chặn absolute path, `..`, trùng output/handoff và stage ID trùng.
- Bỏ các `except Exception: pass` tại cửa contract; trả lỗi có ngữ cảnh.

### 6.3. P0 — Run ID và metadata chưa đúng RULES

**Bằng chứng**

- `build_run_dir()` chỉ dùng timestamp đến giây; hai run cùng input/mode/style có thể trùng và ghi đè.
- Metadata chưa có `run_source`, `persisted`, `api_called`.
- `provider="routing_client"` không phản ánh provider thực tế theo từng stage.
- Model/endpoint luôn đọc qua `get_openai_options()` kể cả khi router chọn Gemini/Antigravity.

**Cần sửa**

- Dùng timestamp microsecond + UUID ngắn; tạo thư mục với `exist_ok=False`.
- Lưu `run_source`, `persisted`, `api_called`, `status`.
- Lưu telemetry từng stage: provider, model, API có gọi, duration, lỗi; tổng hợp sau run.
- Tạo `ClientDescriptor`/`ClientResult` tại router boundary; bỏ suy đoán provider từ `__name__`.
- Tách cấu hình model chung hoặc theo provider; không dùng helper OpenAI làm contract toàn hệ thống.

### 6.4. P1 — Failure semantics và checkpoint chưa an toàn

**Bằng chứng**

- Khi `stop_on_error=False`, lỗi được biến thành artifact/handoff bình thường và có thể truyền xuống stage sau.
- `step_outputs.json` chỉ ghi cuối workflow; run lỗi giữa chừng thiếu trạng thái có cấu trúc.
- Thiếu trạng thái run `running/completed/failed`.

**Cần sửa**

- Kết quả stage phải có `status`; downstream chỉ chạy khi dependency hợp lệ hoặc policy cho phép.
- Ghi checkpoint atomic sau từng stage hoàn tất.
- Cập nhật metadata cuối theo transaction; lỗi phải giữ bằng chứng nhưng không giả làm artifact hợp lệ.
- Định nghĩa resume policy riêng; chưa tự động resume khi chưa có contract.

### 6.5. P1 — Learning loop trùng nguồn chân lý và tốn context

**Bằng chứng**

- Danh sách stage deep/moment bị hardcode nhiều lần trong `learning.py`, trùng với Flow.
- Prompt learning gửi đồng thời toàn bộ Flow, toàn bộ Skill, input, mọi artifact, final và production.
- Offline learning chủ yếu dùng metrics/diff và tên stage; nội dung `step_outputs` gần như không được phân tích nhưng báo cáo vẫn mang tên “learning”.

**Cần sửa**

- Sinh stage list và context từ `WorkflowDefinition`.
- Tách `learning_evidence_builder`, `learning_prompt_builder`, `learning_executor`.
- Đo token trước gọi API; dùng diff + artifact liên quan theo stage, chunk/synthesis khi vượt budget.
- Đổi offline mode thành “diagnostic report” hoặc làm rõ giới hạn; không trình bày các gợi ý cố định như kết luận đã học từ dữ liệu.
- Giữ full artifact để audit, nhưng không mặc định nhồi toàn bộ vào một request.

### 6.6. P1 — `style_manager.py` cần transaction và schema hóa

**Bằng chứng**

- Module 364 dòng đang gộp discovery, alias, validation, CRUD và filesystem transaction.
- `rename_style()` đổi tên thư mục trước rồi mới ghi metadata; ghi metadata lỗi không rollback tên thư mục.
- `save_style_file()` cập nhật skill và metadata bằng hai lần ghi rời; lỗi metadata bị nuốt.
- Metadata lỗi có thể bị bỏ qua và thay bằng default, làm style hỏng trông như hợp lệ.

**Cần sửa**

- Tách `style_registry`, `style_contract`, `style_repository`, `style_service`.
- Schema hóa `style_meta.yaml`; phân biệt style hợp lệ và style lỗi thay vì ẩn lỗi.
- Rename/save theo staging → validate → replace → rollback.
- `delete_style()` nên chuyển vào trash/backup có khả năng khôi phục; publisher và CRUD dùng chung primitive transaction.

### 6.7. P2 — Router, parser và test coverage còn lỗ hổng

**Bằng chứng**

- `build_client_map()` không validate fallback và không phát hiện stage ID gõ sai.
- `parse_stage_response()` tự tạo handoff từ artifact khi model thiếu contract.
- Test hiện chủ yếu kiểm tra happy path; chưa khóa các invariant mới.

**Cần sửa**

- Validate provider và stage map sau khi load Flow; unknown stage phải fail-fast.
- Production mặc định strict với output thiếu `Artifact/Handoff`; fallback chỉ dành cho legacy/dry-run và phải ghi warning/status.
- Bổ sung test: run collision, path traversal, Flow–Skill mismatch, invalid YAML, router typo, partial failure, atomic rollback, metadata truthfulness và `runs/` bất biến.

## 7. Lộ trình refactor đã điều chỉnh

1. **Contract & guardrail:** model hóa request/result, Flow/Step, metadata; khóa test không ghi `runs/`.
2. **Execution & persistence:** tách preview, execution, checkpoint, run repository; sửa ID và failure semantics.
3. **Provider boundary:** descriptor/telemetry theo stage; bỏ coupling `get_openai_options()` khỏi orchestrator.
4. **Flow–Skill validation:** một nguồn chân lý, path safety, strict parser.
5. **Learning loop:** evidence builder, token budget, stage list lấy từ Flow.
6. **Style service:** schema + transaction + rollback.
7. **Voice Lab interview và UI:** thực hiện theo kế hoạch tại Mục 3 sau khi contract engine ổn định.
8. **Regression/audit:** fake API, temp output, AppTest, kiểm tra import chết và xác nhận `runs/` không đổi.

## 8. Phạm vi nên hoãn

- Chưa thêm provider mới cho Voice Lab; Voice Lab tiếp tục Gemini-only.
- Chưa redesign UI trong đợt sửa contract nền tảng.
- Chưa tạo abstraction chung giữa workflow blog và Voice Lab nếu chưa có ít nhất hai consumer thực tế.
- Chưa tự động áp dụng gợi ý learning vào Skill YAML; mọi thay đổi prompt vẫn cần người dùng duyệt.

---

## 9. Đánh giá & Phản biện kế hoạch Voice Lab của GPT-5.6 Sol (Gemini 3.1 Pro)

### 9.1. Những điểm hiệu quả, hợp lý của GPT-5.6 Sol
- **Tuân thủ nguyên tắc Fail-closed & Contract-first:** Loại bỏ triệt để fallback giả (mock data), cấm model tự bịa profile khi parse lỗi, đáp ứng đúng quy tắc "Fail-closed khi contract sai; không silent fallback" của SKILL kiến trúc.
- **Vệ sinh kiến trúc Orchestrator:** Yêu cầu tách `analyzer.py` thành các khối riêng (prompt builder, call layer, parser/validator), không để orchestrator ôm logic parse hay prompt tĩnh.
- **Khóa phạm vi Gemini-only:** Chốt loại bỏ các giả định về Antigravity Bridge/OpenAI API trong Voice Lab, tuân thủ chính xác quy tắc số 4 của `AGENTS.md`.

### 9.2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu của GPT-5.6 Sol
- **Bỏ qua quy chuẩn bảo vệ dữ liệu (`runs/`):** Kế hoạch không có ranh giới I/O để ngăn artifact từ test, dry-run hoặc preview compile ghi vào dữ liệu nghiệp vụ `runs/`, vi phạm quy tắc số 2 & 3 của `AGENTS.md`.
- **Thiếu cơ chế Publish Transactional:** Adapter UI (§8) chỉ đề xuất "refresh compiled output" và "đẩy vào profile", chưa áp dụng luồng xuất bản nguyên tử 4 bước (`Staging -> Validate -> Backup -> Atomic Replace / Rollback`).
- **Bỏ sót kiểm chứng giao diện qua AppTest:** Tiêu chí nghiệm thu (§11) chỉ tập trung vào unit test cho backend AI, không yêu cầu Streamlit AppTest để kiểm chứng adapter UI, vi phạm quy tắc 12 của `AGENTS.md`.
- **Chưa chuẩn hóa nguồn chân lý Flow–Skill:** Chưa chỉ rõ cách kiểm soát xung đột contract giữa Workflow YAML và Canonical IR trong `compiler.py`.

### 9.3. Đề xuất
- **Bảo vệ I/O & Cô lập Test:** Bắt buộc mọi luồng compile preview, phỏng vấn, A/B calibration và test trong Voice Lab phải chạy in-memory hoặc dùng `tmp_path`, tuyệt đối không chạm vào `runs/`.
- **Chuẩn hóa Publish Safety Pipeline:** Đưa quy trình giao dịch nguyên tử (có staging, validate yaml/invariant, backup và rollback) vào tiêu chí bắt buộc khi publish style từ Voice Lab.
- **Kiểm chứng UI bằng Streamlit AppTest:** Viết regression test bằng AppTest trong môi trường tạm để xác nhận tương tác phỏng vấn và A/B thực sự cập nhật profile mà không gây tác dụng phụ.
- **Thực thi SKILL `agentic-workflow-architect`:** Bắt buộc áp dụng skill kiến trúc khi triển khai; chốt Pydantic schema v2 và Canonical IR làm nguồn chân lý duy nhất trước khi sửa đổi engine và adapter UI.

---

## 10. Đánh giá & Phản biện kế hoạch Voice Lab của GPT-5.6 Sol và Gemini 3.1 Pro (Claude Opus 4.6)

### 10.1. Điểm hiệu quả, hợp lý

**GPT-5.6 Sol:**
- Đề xuất `DimensionProfile` nested thay `VoiceDNA` flat-string đã được triển khai thành công trong codebase V6.0 — chứng tỏ hướng thiết kế đúng từ đầu.
- Luồng 2 tầng (per-sample → cross-sample synthesis) đã được hiện thực hóa bằng adaptive routing dựa trên token budget thay vì ngưỡng cứng số sample — cho thấy ý tưởng gốc hợp lý, chỉ thiếu metric.
- Yêu cầu `shuffle_mapping` cho A/B đã trở thành `CalibrationSession.shuffle_mapping` trong code — xác nhận đây là lỗ hổng thật cần vá.

**Gemini 3.1 Pro (lần 2 — phản biện theo RULES & SKILL):**
- Đúng khi chỉ ra Sol bỏ sót ranh giới I/O cho `runs/` — AGENTS.md §2-3 bắt buộc cô lập test/dry-run; kế hoạch Sol không có constraint nào về output path.
- Đúng khi yêu cầu AppTest cho UI adapter — AGENTS.md §12 cấm báo hoàn tất UI chỉ dựa trên unit test; Sol §11 chỉ liệt kê test backend.
- Đề xuất chốt Pydantic schema v2 + Canonical IR làm nguồn chân lý duy nhất trước khi sửa engine — phù hợp SKILL §5 ("contract → engine → prompt → integration → verification").

### 10.2. Điểm chưa hiệu quả, chưa hợp lý, còn thiếu

**GPT-5.6 Sol:**
- **Kế hoạch §2 liệt kê `engine/voice_lab/ui/app.py` — file này không tồn tại.** UI thật nằm tại `ui/app.py` (ngang hàng `engine/`). Sai đường dẫn trong phạm vi refactor là rủi ro cao: agent triển khai có thể tạo file mới ở sai vị trí hoặc bỏ qua file đúng.
- **Schema v2 §3.2 thiết kế `confidence` ở level evidence** nhưng code triển khai (`DimensionProfile`) đã chuyển confidence lên level dimension và bỏ hoàn toàn `confidence` khỏi `EvidenceClaim` — kế hoạch gốc và kết quả triển khai lệch pha, cho thấy plan thiếu phân tích vị trí đặt confidence đúng.
- **§6 refactor compiler nói "bỏ `_load_base_skill` lấy style gốc tùy ý"** nhưng không nói thay bằng gì — thiếu quyết định thiết kế: explicit `base_style_slug` trong profile hay dựa vào config? Code triển khai cuối dùng `profile.base_style_slug` nhưng Sol không đặt requirement này.
- **§7 chưa có tiêu chí phân biệt "legacy incomplete" và "migration lỗi thật"** — `migration.py` cần phân biệt: (a) style cũ không có profile_dna.json (bình thường, trả `incomplete_legacy_data`), (b) file tồn tại nhưng parse fail (lỗi thật, cần warning khác). Sol gộp cả hai thành "trả trạng thái thiếu".

**Gemini 3.1 Pro (cả 2 lần):**
- **Nhận xét "Antigravity Bridge / Local Model" (lần 1 §2 bullet 3) đã bị bác bỏ đúng** bởi Sol và chính Gemini lần 2 — nhưng lần 2 vẫn không tự nhận lỗi lần 1, tạo ấn tượng hai ý kiến độc lập trong khi thực chất là self-correction.
- **Đề xuất "Chuẩn hóa nguồn chân lý Flow–Skill" (lần 2 §2 bullet 4) quá rộng cho phạm vi Voice Lab:** Flow–Skill contract là vấn đề toàn hệ thống (xem summary §6.2), không phải của riêng compiler Voice Lab. Đưa nó vào kế hoạch refactor Voice Lab sẽ phình scope và vi phạm SKILL §6 ("thay đổi nhỏ nhất đáp ứng contract").
- **Cả hai lần Gemini đều không phát hiện rằng `current_architecture.md` đã liệt kê `prompts.py`, `parser.py`, `publisher.py`** trong cây thư mục (L36-44) — nghĩa là V6.0 đã triển khai xong 3 module mới mà Sol không đề cập trong kế hoạch ban đầu. Phản biện nên chỉ ra kế hoạch Sol thiếu nhận thức về trạng thái code đã triển khai.

### 10.3. Đề xuất

- **Sửa đường dẫn UI:** Thay `engine/voice_lab/ui/app.py` trong §2 thành `ui/app.py` — hoặc tách rõ: "sửa import/adapter trong `ui/app.py`" thay vì liệt kê như module Voice Lab.
- **Chốt vị trí confidence:** Confidence thuộc `DimensionProfile` (tính bằng code deterministic), không thuộc `EvidenceClaim`. Cập nhật §3.2 để phản ánh đúng: evidence chỉ có `stance` (support/contradict), không có `confidence`.
- **Bổ sung `base_style_slug` vào §3.1:** Mỗi `StyleProfile` phải khai báo explicit base style để compiler biết load template nào — không dựa vào `iterdir()` cũng không dựa vào config ngầm.
- **Tách phạm vi Flow–Skill validation ra khỏi kế hoạch Voice Lab:** Xử lý trong kế hoạch refactor `workflow.py` (summary §3.2) thay vì nhồi vào Voice Lab compiler.
- **Cập nhật §2 phạm vi để bao gồm 3 file mới:** `prompts.py`, `parser.py`, `publisher.py` đã tồn tại trong codebase; kế hoạch refactor phải ghi nhận chúng thay vì chỉ liệt kê 7 file gốc.

---

## 11. Phản biện bổ sung của GPT-5.6 Sol

### 11.1. Những điểm hiệu quả, hợp lý của Gemini 3.1 Pro và của Claude Opus 4.6
 - Gemini 3.1 Pro
Đúng về cô lập runs/, AppTest và thứ tự contract → engine → UI.
Đúng khi giữ Voice Lab Gemini-only và yêu cầu publish nguyên tử.
Đúng khi nhấn mạnh fail-closed, Pydantic schema và Canonical IR.


 - Claude Opus 4.6
Phát hiện chính xác sai đường dẫn UI: phải là ui/app.py.
Đúng khi đặt confidence tại DimensionProfile, không tại EvidenceClaim.
Đúng khi yêu cầu base_style_slug tường minh.
Đúng khi phân biệt legacy thiếu profile với profile tồn tại nhưng parse lỗi.
Đúng khi cảnh báo không kéo toàn bộ refactor Flow–Skill vào phạm vi Voice Lab.

### 11.2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu của Gemini 3.1 Pro và của Claude Opus 4.6

 - Gemini 3.1 Pro
Một số đề xuất đã tồn tại: publisher.py, staging/rollback, prompts.py, parser.py; cần audit thay vì đề xuất xây mới.
Nhầm ranh giới nguồn chân lý: StyleProfile quản lý Voice DNA; Canonical IR là artifact biên dịch; Flow quản lý runtime workflow.
“Flow–Skill xung đột với Canonical IR” diễn đạt quá rộng, dễ phình scope.
Chưa phản biện metadata sai, Run ID va chạm, checkpoint, learning context và transaction của style_manager.py.


 - Claude Opus 4.6
Việc module đã tồn tại không chứng minh V6.0 đã hoàn tất hoặc đúng contract.
Tách Flow–Skill hoàn toàn khỏi Voice Lab là quá mạnh: compiler/publisher vẫn phải kiểm chứng filename và invariant tương thích Flow.
Chưa đánh giá interview.py về pending/applied state, provenance và dependency injection.
Chưa xét dry-run persistence, parser fallback, router typo, provider telemetry và test làm bẩn runs/.
Chưa chỉ ra offline learning đang tạo gợi ý cố định nhưng trình bày như kết quả học từ dữ liệu.

### 11.3. Đề xuất

 - Giữ ba nguồn chân lý độc lập:
Flow: stage, context policy, output filename.
StyleProfile: Voice DNA và provenance.
Canonical IR: artifact biên dịch đã khóa invariant.

 - Ưu tiên P0: cô lập dry-run/test; ID chống va chạm; metadata trung thực; validator Flow–Skill fail-closed.
 - Audit, không xây lại prompts.py, parser.py, publisher.py.
 - Voice Lab chỉ kiểm chứng khả năng tương thích Flow; refactor Flow–Skill đặt tại workflow engine.
 - Bổ sung test: legacy-vs-corrupt migration, pending-vs-applied calibration, publish rollback, path safety, provider telemetry và runs/ bất biến.

---

## 12. Phản biện lần 2 (Claude Opus 4.6)

### 12.1. Điểm hiệu quả, hợp lý của GPT-5.6 Sol (§11)
- **Ba nguồn chân lý độc lập (Flow / StyleProfile / Canonical IR):** Phân định chính xác — Flow sở hữu runtime contract, StyleProfile sở hữu Voice DNA, Canonical IR là artifact biên dịch đã khóa. Giải quyết triệt để nhầm lẫn "ai là source of truth" mà cả Gemini lẫn tôi đều diễn đạt thiếu rõ.
- **Đúng khi phản bác tôi về "tách Flow–Skill hoàn toàn khỏi Voice Lab":** Compiler/publisher Voice Lab vẫn phải validate filename và invariant tương thích Flow — tách hoàn toàn sẽ để lỗ hổng contract. Tôi đã nói quá mạnh.
- **Đúng khi chỉ ra "module tồn tại ≠ hoàn tất contract":** `prompts.py`, `parser.py`, `publisher.py` cần audit chất lượng, không phải chỉ ghi nhận vào §2 là xong.
- **Bổ sung đúng các điểm mù của tôi:** `interview.py` pending/applied state, dry-run persistence, offline learning trình bày sai bản chất — tất cả là lỗ hổng thật mà tôi bỏ sót.

### 12.2. Điểm chưa hiệu quả, chưa hợp lý, còn thiếu của GPT-5.6 Sol (§11)
- **"Audit, không xây lại" chưa đủ cụ thể:** Audit `prompts.py`/`parser.py`/`publisher.py` cần tiêu chí rõ: kiểm gì (contract compliance, error handling, test coverage), output gì (pass/fail/refactor needed), ai quyết định hành động tiếp theo. Không có tiêu chí thì audit chỉ là đọc code rồi bỏ.
- **Danh sách test §11.3 thiếu thứ tự ưu tiên:** Liệt kê 6 loại test nhưng không phân P0/P1 — `runs/` bất biến và legacy-vs-corrupt migration rõ ràng là P0 (bảo vệ dữ liệu), trong khi provider telemetry là P2. Thiếu ưu tiên sẽ khiến agent triển khai viết test telemetry trước test bảo vệ dữ liệu.
- **Chưa chốt ranh giới "Voice Lab chỉ kiểm chứng khả năng tương thích Flow":** Cụ thể compiler phải validate những gì — chỉ filename + required agents, hay cả workflow_order + context_policy? `current_architecture.md` L91 nói Canonical IR lưu `invariant snapshot` — compiler phải đọc snapshot này để validate, hay chỉ ghi?
- **§11.2 phê Gemini "nhầm ranh giới nguồn chân lý" nhưng Sol §3.1-3.2 ban đầu cũng không phân định:** Kế hoạch gốc chỉ nói "schema v2" mà không nói schema đó thuộc model nào — phân biệt Flow/StyleProfile/IR là insight mới từ §11, không phải điều Sol đã có từ đầu.

### 12.3. Đề xuất
- **Bổ sung tiêu chí audit cho 3 module:** Mỗi module cần checklist: (1) JSON schema output khớp `models.py`, (2) error path trả explicit status thay vì nuốt exception, (3) có ≥1 test cho happy path và ≥1 test cho malformed input, (4) không hardcode version hay path.
- **Phân ưu tiên test:** P0: `runs/` bất biến, legacy-vs-corrupt migration, publish rollback. P1: pending-vs-applied calibration, path safety. P2: provider telemetry.
- **Chốt ranh giới validate của compiler:** Compiler Voice Lab validate `filename ∈ AGENT_FILENAME_MAP[mode]` và `required_agents ⊆ compiled_agents`. Canonical IR ghi invariant snapshot; publisher validate snapshot khớp trước atomic replace. Compiler không validate workflow_order hay context_policy — đó là trách nhiệm của workflow engine.
- **Cập nhật kế hoạch gốc Sol §3 để ghi nhận 3 nguồn chân lý:** Tránh lặp lại nhầm lẫn khi agent mới đọc kế hoạch mà không đọc chuỗi phản biện.

---

## 13. Phản biện lần 2 của GPT-5.6 Sol

###1. Những điểm hiệu quả, hợp lý của Claude Opus 4.6
- Đúng khi thừa nhận ba nguồn chân lý và Voice Lab vẫn phải kiểm chứng tương thích Flow.
- Đúng khi yêu cầu audit có tiêu chí, trạng thái kết luận và test lỗi.
- Đúng khi phân tầng test thay vì triển khai đồng hạng.
- Đúng khi yêu cầu đưa phân định Flow/StyleProfile/Canonical IR vào kế hoạch gốc.

###2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu của Claude Opus 4.6
- Xếp `legacy-vs-corrupt migration` vào P0 “bảo vệ dữ liệu” chưa thuyết phục; đây chủ yếu là P1 tương thích/quan sát lỗi. Ngược lại, `path safety` phải là P0.
- Ranh giới compiler quá hẹp: compiler đang tạo và khóa `workflow_order`, `context_policy`; không thể tuyên bố không validate chúng.
- `required_agents ⊆ compiled_agents` chưa phân biệt full compile để publish với incremental compile để preview.
- Checklist “không hardcode version/path” quá tuyệt đối; schema version, filename map tập trung là contract hợp lệ.
- Thiếu kiểm tra prompt: schema parity, chống prompt injection từ sample, quote provenance và token budget.
- Chưa phát hiện publisher chỉ so invariant khi key còn tồn tại; xóa key invariant có thể lọt qua.

###3. Đề xuất
- P0: `runs/` bất biến, path safety, publish rollback, invariant bắt buộc hiện diện và khớp, full compile đủ đúng tập file Flow.
- P1: legacy-vs-corrupt, pending-vs-applied, malformed prompt/response; P2: provider telemetry.
- Compiler bảo toàn invariant từng artifact; publisher đối chiếu tập file/tham chiếu Flow và snapshot trước atomic replace; workflow engine sở hữu runtime order/context semantics.
- Tách contract: full compile mới được publish; incremental compile chỉ preview/audit.
- Audit `prompts.py`, `parser.py`, `publisher.py` theo ma trận `contract/error/test/I-O`, kết luận `pass | refactor | block` kèm bằng chứng test.

