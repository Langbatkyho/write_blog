# Kế hoạch refactor logic và prompt Voice Lab

## 1. Mục tiêu

- Sửa lại logic và prompt của Voice Lab để phân tích phong cách viết đáng tin hơn, ít nhiễu hơn, và dễ mở rộng hơn.
- Giữ nguyên Gemini trực tiếp, không thêm lớp client trung gian.
- Đọc dữ liệu cũ, ghi theo schema v2.
- Tập trung vào backend AI: models, prompt, parse, compiler.
- UI chỉ thêm adapter tối thiểu để thực sự đẩy dữ liệu từ interview và A/B vào profile.

## 2. Phạm vi refactor

- `engine/voice_lab/models.py`
- `engine/voice_lab/analyzer.py`
- `engine/voice_lab/interview.py`
- `engine/voice_lab/compiler.py`
- `engine/voice_lab/overrides.py`
- `engine/voice_lab/migration.py`
- `engine/voice_lab/ui/app.py` ở mức adapter tối thiểu

## 3. Thiết kế dữ liệu v2

### 3.1 Style profile

- Thêm `schema_version = 2`.
- Mỗi chiều phong cách cần có:
  - `description`
  - `strength`
  - `confidence`
  - `do`
  - `avoid`
  - `examples`
  - `evidence_ids`
- Thêm:
  - `analysis_warnings`
  - `interview_history`
  - `calibration_history`

### 3.2 Evidence

- Mỗi evidence phải có:
  - `sample_id`
  - `dimension`
  - `exact_quote`
  - `confidence`
  - `status`
- Chỉ chấp nhận quote trích nguyên văn, không suy diễn lại ý.

## 4. Refactor logic AI

### 4.1 Analyzer

- Tách rõ 3 phần:
  - dựng prompt
  - gọi Gemini
  - validate/parse kết quả
- Không còn fallback giả kiểu hard-coded DNA khi lỗi.
- Nếu parse lỗi hoặc quote không hợp lệ thì fail closed, trả lỗi/đánh dấu thiếu dữ liệu thay vì bịa profile.
- Prompt phải coi sample là dữ liệu không đáng tin:
  - chống prompt injection
  - không để nội dung bài viết điều khiển hệ thống
  - chỉ dùng trích dẫn nguyên văn để làm evidence

### 4.2 Luồng phân tích hai tầng

- Tầng 1: kiểm tra sample, nhận diện các chiều style, quote evidence, lọc nhiễu.
- Tầng 2: tổng hợp across samples, gom pattern lặp lại, phát hiện mâu thuẫn, xác định outlier.
- Giới hạn xử lý theo quota batch để tránh prompt quá dài.
- Chỉ tổng hợp trên evidence hợp lệ.

### 4.3 Quy tắc confidence

- Không để confidence do model tự khai hoàn toàn.
- Confidence nên được tính từ:
  - mức phủ mẫu
  - độ nhất quán giữa samples
  - chất lượng quote
- Nếu chỉ có một sample hoặc quote yếu, confidence phải bị chặn trần thấp hơn.

## 5. Refactor prompt

### 5.1 Prompt phân tích

- Prompt cần tách rõ:
  - style vs topic
  - style vs genre
  - style vs content facts
- Bắt buộc xuất:
  - do / avoid
  - evidence quote
  - confidence
  - warning khi thiếu dữ liệu
- Không cho phép model tự bịa quote.
- Không cho phép kết luận vượt quá evidence.

### 5.2 Prompt interview

- Chuyển từ câu hỏi chung sang câu hỏi theo chiều phong cách cụ thể.
- Chỉ hỏi tối đa 3 chiều yếu nhất mỗi vòng.
- Câu hỏi phải phân biệt:
  - người viết muốn gì
  - bài viết thực sự đang làm gì
- Câu trả lời interview chỉ được áp vào profile khi đi kèm provenance rõ ràng.

### 5.3 Prompt calibration A/B

- A/B phải chỉ thay đổi đúng một chiều tại một lần.
- Không dùng label gây thiên lệch như “đậm chất” hay “mềm hơn” nếu làm lộ đáp án.
- Hai variant phải giữ nguyên:
  - topic
  - facts
  - độ dài
  - các chiều không mục tiêu
- Kết quả lựa chọn phải cập nhật lại profile, không chỉ lưu log.

## 6. Refactor compiler

### 6.1 Điểm cần làm lại

- Bỏ cơ chế `_load_base_skill` lấy style gốc tùy ý theo thứ tự thư mục.
- Không ghép prompt từ các chuỗi rời rạc kiểu “Tone: ...” nếu mục tiêu là sinh skill đầy đủ.
- Không biến style content thành một bản rút gọn mất khả năng của agent.

### 6.2 Hướng refactor

- Dùng template skill full để compile ra bản hoàn chỉnh.
- Overlay style rules lên template sẵn có theo mode/agent.
- Giữ nguyên:
  - role
  - tasks
  - input
  - output
  - workflow/invariants
- Chỉ thay phần style-specific.

### 6.3 IR trung gian

- IR nên versioned rõ ràng.
- IR cần ghi:
  - template mode
  - style overlays
  - invariants
  - ordering rules
- Compiler phải detect xung đột giữa các rule trước khi ghi file.

## 7. Refactor migration và overrides

- `migration.py` không nên tạo DNA rỗng low-confidence như một kết quả thật.
- Nếu không đủ dữ liệu thì trả trạng thái thiếu, không giả lập style.
- `overrides.py` cần bỏ cơ chế merge giả bằng comment mô phỏng.
- Nếu chưa triển khai override thật thì đánh dấu rõ là chưa hỗ trợ.

## 8. Adapter UI tối thiểu

- `ui/app.py` chỉ cần:
  - nhận answers interview
  - nhận lựa chọn A/B
  - đẩy vào profile thật
  - refresh compiled output
- Không cần redesign UI.
- Evidence review nên chỉ cho phép lọc/loại evidence xấu nếu backend hỗ trợ.

## 9. Các chỗ cần refactor mạnh nhất

1. `engine/voice_lab/analyzer.py`
   - tách prompt builder, call layer, parser, validator
   - bỏ fallback giả
   - thêm kiểm soát evidence và confidence

2. `engine/voice_lab/compiler.py`
   - bỏ load base style ngẫu nhiên
   - compile từ template đầy đủ
   - giữ agent capability, không rút gọn thành prompt thô

3. `engine/voice_lab/interview.py`
   - chuyển sang câu hỏi theo chiều yếu
   - giới hạn tối đa 3 chiều
   - map answer vào profile có provenance

4. `engine/voice_lab/models.py`
   - nâng schema v2
   - chuẩn hóa evidence/profile fields
   - thêm history/warning/state

5. `engine/voice_lab/ui/app.py`
   - adapter tối thiểu để interview và A/B thật sự tác động tới profile

## 10. Thứ tự triển khai khuyến nghị

1. Chốt schema v2 trong `models.py`.
2. Refactor analyzer + prompt + parser.
3. Refactor interview và calibration.
4. Refactor compiler để dùng full template.
5. Sửa migration và overrides theo hướng fail-safe.
6. Nối adapter UI tối thiểu.
7. Thêm test cho injection, malformed output, quote sai, và round-trip compile.

## 11. Tiêu chí chấp nhận

- Không còn DNA giả khi lỗi LLM.
- Evidence có quote nguyên văn và truy vết được.
- Interview và A/B thật sự cập nhật profile.
- Compiler không làm mất capability của agent.
- Schema v2 đọc được dữ liệu cũ và ghi ra dữ liệu mới.
- Test bao phủ các case lỗi chính:
  - prompt injection
  - output sai schema
  - quote không khớp
  - conflict giữa samples

## 12. Giả định

- Không đổi kiến trúc tổng thể của Voice Lab.
- Không thay Gemini bằng model khác.
- Không làm lại UI theo hướng lớn.
- Workflow system/styles hiện có vẫn giữ nguyên, chỉ refactor cách Voice Lab phân tích và compile.

---

## Đánh giá & Phản biện (Gemini 3.1 Pro)

### 1. Những điểm hiệu quả, hợp lý của GPT-5.6 Sol
- **Nhận diện chính xác technical debt:** Chỉ ra đúng các điểm yếu code hiện tại như fallback giả (`mock data`) trong `analyzer.py`, nối chuỗi rule thô sơ trong `compiler.py`, comment giả lập merge trong `overrides.py`, và tạo DNA rỗng trong `migration.py`.
- **Chuẩn hóa cơ chế fail-safe / fail-closed:** Loại bỏ hoàn toàn việc model tự bịa profile khi lỗi parse/lỗi LLM, đảm bảo tính xác thực của `exact_quote` và confidence.
- **Nâng cấp Schema v2 và IR:** Thêm lịch sử phỏng vấn, A/B calibration, cảnh báo dữ liệu (`analysis_warnings`), chuyển `compiler.py` sang Full Template Overlay giúp giữ nguyên capability của agent.
- **Tối ưu trải nghiệm phỏng vấn:** Giới hạn hỏi tối đa 3 chiều yếu nhất kèm provenance rõ ràng.

### 2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu của GPT-5.6 Sol
- **Thiếu liên kết với Invariant Contract & Adjacency Matrix:** Không đề cập việc duy trì ma trận kề (`DIMENSION_AGENTS`), ánh xạ file (`AGENT_FILENAME_MAP`), và các trường bất biến (`agent_id`, `output_contract`...) theo Clean Architecture đã chốt trong V6.0.
- **Bỏ qua Publish Safety Pipeline (4 bước):** Adapter UI mới chỉ ghi nhận "refresh compiled output", thiếu cơ chế xuất bản an toàn nguyên tử (`Staging -> Validate -> Backup -> Atomic Replace / Rollback`).
- **Nguy cơ lãng phí Quota với luồng phân tích 2 tầng:** Việc chia tầng (từng sample -> cross-sample) làm tăng số lượng API call và token, xung đột với mục tiêu tiết kiệm Quota / hỗ trợ Local Model qua Antigravity Bridge.
- **Chưa rõ cơ chế xử lý conflict trong Override:** Đề xuất bỏ comment mô phỏng nhưng chưa đưa ra giải pháp thay thế cụ thể khi diff 3 chiều gặp xung đột không tự phân giải được.

### 3. Đề xuất
- **Đồng bộ Kiến trúc V6.0:** Bổ sung ràng buộc bắt buộc tuân thủ **Invariant Contract** và **Adjacency Matrix** vào specification của Schema v2 và Compiler Refactor.
- **Tối ưu Luồng phân tích theo Batching:** Chuyển sang luồng phân tích linh hoạt (chỉ kích hoạt 2 tầng khi có >3 samples hoặc mẫu quá dài) để đảm bảo tối ưu Quota Estimator và tương thích Local Model.
- **Tích hợp Publish Safety Pipeline:** Định nghĩa rõ task "Nối adapter UI" trong Lộ trình triển khai phải bao gồm luồng 4 bước xuất bản nguyên tử và rollback tự động.
- **Chuẩn hóa Fail-fast cho Legacy Data:** Tại `migration.py` và `overrides.py`, trả về status lỗi explicit (`incomplete_legacy_data` / `unresolved_conflict`) để UI trigger workflow manual resolve thay vì tạo mock data.

---

## Đánh giá & Phản biện (Claude Opus 4.6)

### 1. Điểm hiệu quả, hợp lý

**GPT-5.6 Sol:**
- Đúng khi yêu cầu tách `analyzer.py` thành 3 layer (prompt builder / call / parser) — code hiện tại gộp cả 3 vào một hàm 66 dòng, vi phạm SRP.
- Schema v2 bổ sung `do`/`avoid`/`evidence_ids` cho mỗi chiều là thiết kế actionable — `VoiceDNA` hiện tại chỉ lưu chuỗi mô tả thô, compiler không có gì để overlay ngoài `f"{dim}: {val}"`.
- Yêu cầu confidence tính từ heuristic (phủ mẫu + nhất quán) thay vì để LLM tự khai — giải quyết đúng lỗ hổng tại `analyzer.py:15` (`confidence: float` do model trả tùy ý).
- Nhận ra `_load_base_skill` (`compiler.py:73-82`) duyệt `iterdir()` lấy style đầu tiên tìm được là non-deterministic nguy hiểm.

**Gemini 3.1 Pro:**
- Đúng khi chỉ ra Sol bỏ quên Invariant Contract — `CanonicalIR` đã có 6 trường bất biến (`agent_id`, `filename`, `output_contract`, `handoff_contract`, `workflow_order`, `context_policy`) mà Sol không nhắc giữ nguyên trong quá trình refactor compiler.
- Đúng khi yêu cầu adapter UI phải bao gồm Publish Safety Pipeline 4 bước — code hiện tại ở `ui/app.py` đã có pipeline này, Sol chỉ nói "refresh compiled output" là hạ cấp so với V6.0.

### 2. Điểm chưa hiệu quả, chưa hợp lý, còn thiếu

**GPT-5.6 Sol:**
- **Bỏ sót `archive.py` hoàn toàn:** Phạm vi refactor (§2) liệt kê 7 file nhưng thiếu `archive.py` — file này đang hardcode `schema_version: "1.0"` (`archive.py:34`), nếu nâng schema v2 mà không sửa archive thì export/import sẽ tạo gói không tương thích.
- **Schema v2 thiếu backward-compatible reader:** Nói "đọc dữ liệu cũ, ghi schema v2" (§1) nhưng không thiết kế migration path cụ thể — `StyleProfile` hiện không có trường `schema_version`, không có logic đọc v1 rồi convert.
- **Luồng 2 tầng thiếu fallback khi chỉ 1 sample:** §4.2 mô tả cross-sample synthesis ở tầng 2 nhưng không nói tầng 2 làm gì khi user chỉ nạp 1 bài mẫu — hiện tại `analyze_samples` nhận `list[str]` và xử lý đồng nhất.
- **A/B Calibration không tracking shuffle order:** §5.3 yêu cầu blind + randomize nhưng `interview.py:112` dùng `random.shuffle` rồi trả `variants[0], variants[1]` mà không ghi lại mapping nào là "đậm" nào là "tiết chế" — khi user chọn, hệ thống không biết user chọn bản nào để cập nhật profile đúng chiều.
- **Thiếu retry / circuit-breaker cho Gemini call:** Bỏ fallback giả là đúng, nhưng không đề xuất retry có backoff hoặc circuit-breaker — nếu Gemini 503 liên tục thì toàn bộ wizard sẽ chết cứng.

**Gemini 3.1 Pro:**
- **Nhận xét "lãng phí Quota 2 tầng" chưa chính xác:** Luồng 2 tầng của Sol dùng batch per-sample rồi tổng hợp — đây là pattern chuẩn khi context window không đủ chứa tất cả samples cùng lúc (mỗi sample 10K chars × 5 samples = 50K chars). Vấn đề thật không phải là tốn quota mà là **thiếu adaptive routing**: nên single-pass khi tổng token < context limit, multi-pass khi vượt.
- **Đề xuất "Batching linh hoạt >3 samples" thiếu metric cụ thể:** Dùng ngưỡng số sample cứng (>3) là heuristic yếu — nên dùng token count thực tế so với context window limit.
- **Bỏ sót lỗi cấu trúc trong `migration.py`:** `migration.py:31-32` có khối `try` mở nhưng `except` ở sai indentation level (L32 thụt về ngang `if yaml_path` thay vì ngang `try`), tạo syntax error tiềm ẩn. Cả Sol lẫn Gemini đều không nhận ra.
- **Không phản biện cấu trúc `VoiceDNA` flat-string:** Gemini đồng ý Sol nâng schema v2 nhưng không chỉ ra vấn đề gốc — `VoiceDNA` dùng 12 trường `str` phẳng không có metadata, muốn thêm `strength`/`confidence`/`do`/`avoid` thì phải chuyển mỗi chiều từ `str` sang nested model (breaking change lớn), không đơn giản là "thêm field".

### 3. Đề xuất

- **Bổ sung `archive.py` vào phạm vi refactor:** Cập nhật `schema_version` trong manifest, thêm logic detect version khi import để auto-migrate v1→v2.
- **Thiết kế `DimensionProfile` model mới:**
  ```python
  class DimensionProfile(BaseModel):
      description: str
      strength: float  # 0.0-1.0
      confidence: float
      do: list[str]
      avoid: list[str]
      evidence_ids: list[str]
  ```
  Thay `VoiceDNA` 12×str bằng `dna: dict[str, DimensionProfile]` — vừa backward-compatible (deserialize str cũ vào `description`), vừa extensible.
- **Ghi `shuffle_mapping` trong A/B:** Sau `random.shuffle`, lưu `{"position_0": "amplified"|"subdued", "position_1": ...}` vào session state để khi user chọn, hệ thống biết cập nhật profile theo hướng nào.
- **Thêm retry 2 lần + exponential backoff cho `call_gemini`:** Thay thế fallback giả bằng retry có giới hạn, chỉ raise `AnalysisError` sau khi retry hết — UI hiển thị thông báo lỗi rõ ràng thay vì trả profile giả.
- **Sửa bug `migration.py:32`:** `except` phải thụt cùng level với `try` (L25), hiện tại code sẽ raise `IndentationError` khi chạy thực tế với file YAML hợp lệ.

---

## Phản biện đối ứng (GPT-5.6 Sol, cập nhật theo làm rõ Gemini-only)

### 1. Điểm giữ nguyên trong kế hoạch
- `archive.py` phải vào phạm vi refactor; bỏ qua là thiếu sót thật.
- `VoiceDNA` flat `str` là cấu trúc yếu, nên chuyển sang model lồng nhau có metadata.
- `migration.py` cần sửa lỗi cấu trúc trước mọi refactor cao hơn.
- `shuffle_mapping` trong A/B là bắt buộc nếu muốn cập nhật profile đúng chiều.
- Adaptive routing phải dựa trên token/context, không dựa cứng vào số sample.

### 2. Điểm cần bác lại từ các phản biện trước
- **Antigravity Bridge không thuộc Voice Lab này.** Mọi nhận xét về hỗ trợ local model qua bridge đều ngoài phạm vi, vì Voice Lab chỉ gọi Gemini API.
- **OpenAI API chỉ là hướng thử sau.** Không được đưa vào refactor hiện tại như một nhánh runtime hay router song song.
- **Không cần thêm một lớp retry mới nếu đã có retry ở client.** Ưu tiên dùng lại `gemini_client` hiện có, rồi bổ sung phân loại lỗi/telemetry nếu cần.
- **Publish Safety Pipeline không phải feature mới.** Nó đã tồn tại ở UI; việc đúng là giữ nguyên và refactor để an toàn hơn, không phải thêm từ đầu.

### 3. Chốt cập nhật
- Giữ các ràng buộc kiến trúc cốt lõi: Invariant Contract, Adjacency Matrix, publish an toàn, fail-closed.
- Sửa các điểm kỹ thuật gốc: parser/prompt, schema v2 nested, migration, A/B mapping, archive/versioning.
- Loại bỏ hoàn toàn mọi giả định về Antigravity trong kế hoạch Voice Lab này.
