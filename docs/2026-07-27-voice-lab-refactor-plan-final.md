# Kế hoạch refactor logic và prompt Voice Lab — Final

**Ngày:** 27/07/2026  
**Trạng thái:** Đã phê duyệt và triển khai

## 1. Mục tiêu và quyết định đã chốt

- Nâng độ tin cậy của phân tích phong cách; không tạo Voice DNA giả khi Gemini hoặc parser lỗi.
- Biến kết quả phân tích thành chỉ dẫn viết có thể kiểm chứng: `do`, `avoid`, ví dụ và bằng chứng nguyên văn.
- Giữ nguyên năng lực, workflow và contract của từng agent khi compile style.
- Đọc được dữ liệu v1, chỉ ghi mới theo schema v2.
- Voice Lab chỉ gọi trực tiếp **Gemini API** qua `engine/gemini_client.py`.
- Không dùng Antigravity Bridge; chưa thêm OpenAI API, provider router hoặc abstraction đa model.
- Giữ UI 5 bước hiện tại; chỉ refactor adapter và Publish Safety Pipeline, không redesign lớn.

## 2. Phạm vi thay đổi

### 2.1. Module chính

- `engine/voice_lab/models.py`
- `engine/voice_lab/analyzer.py`
- `engine/voice_lab/interview.py`
- `engine/voice_lab/compiler.py`
- `engine/voice_lab/overrides.py`
- `engine/voice_lab/migration.py`
- `engine/voice_lab/archive.py`
- `ui/app.py`
- `tests/test_voice_lab.py`

### 2.2. Module mới nên tách

- `engine/voice_lab/prompts.py`: prompt builder và JSON schema cho Gemini.
- `engine/voice_lab/parser.py`: parse, validate evidence, chuẩn hóa lỗi.
- `engine/voice_lab/publisher.py`: staging, validate, backup, atomic replace, rollback.

### 2.3. Thay đổi tối thiểu ngoài Voice Lab

- `engine/gemini_client.py`: thực thi đúng tham số `config` hiện đang có nhưng chưa được áp dụng, tối thiểu gồm `response_mime_type` và `response_schema` cho SDK/REST.
- Không thêm retry tại `analyzer.py`; dùng retry, backoff và key rotation sẵn có của `gemini_client`.

## 3. Thiết kế dữ liệu schema v2

### 3.1. Tách phiên bản schema và phiên bản nội dung

- `schema_version: Literal[2] = 2`: phiên bản cấu trúc dữ liệu.
- `revision: int = 1`: tăng khi profile được người dùng sửa/xác nhận.
- Reader chấp nhận v1; writer và archive chỉ xuất v2.
- `profile_version` cũ được ánh xạ sang `revision` khi migrate.

### 3.2. `DimensionProfile`

Mỗi chiều phong cách không còn là một chuỗi phẳng:

```python
class DimensionProfile(BaseModel):
    description: str = ""
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    do: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source: Literal["analysis", "interview", "calibration", "legacy"] = "analysis"
```

- `strength` đo cường độ đặc tính; `confidence` đo độ chắc chắn. Không dùng lẫn hai khái niệm.
- `VoiceDNA` vẫn khai báo rõ 12 chiều hiện có, nhưng mỗi trường có kiểu `DimensionProfile`.
- Validator v1 chuyển chuỗi cũ thành `DimensionProfile(description=<chuỗi>, source="legacy", confidence=0)`.

### 3.3. `EvidenceClaim`

```python
class EvidenceClaim(BaseModel):
    id: str
    sample_id: str
    dimension: str
    claim: str
    exact_quote: str
    quote_start: int | None = None
    quote_end: int | None = None
    stance: Literal["support", "contradict"] = "support"
    status: Literal["active", "rejected"] = "active"
    rejection_reason: str | None = None
```

- Quote chỉ hợp lệ khi khớp nguyên văn với sample tương ứng sau khi chuẩn hóa duy nhất `CRLF -> LF`.
- Không xóa HTML/XML, thay từ `System:` hoặc sửa nội dung sample trước khi đối chiếu quote.
- Claim có quote sai vẫn được lưu ở trạng thái `rejected` để audit, nhưng không được dùng tổng hợp.

### 3.4. `StyleProfile`

Bổ sung:

- `analysis_status`: `complete | partial | failed | incomplete_legacy_data`.
- `analysis_warnings: list[str]`.
- `interview_history: list[InterviewRecord]`.
- `calibration_history: list[CalibrationRecord]`.
- `base_style_slug: str = "reflective"`.
- `created_at`, `updated_at`.

Quy tắc:

- `dna=None` khi chưa đủ dữ liệu; không tạo 12 chiều rỗng để giả lập kết quả hợp lệ.
- Profile `partial`, `failed` hoặc `incomplete_legacy_data` luôn là draft và không được auto-publish.

### 3.5. Kết quả nghiệp vụ và lỗi

- `AnalysisResult(profile, rejected_evidence, warnings, routing_mode, usage)`.
- `AnalysisError(code, user_message, retryable, detail)` với các mã tối thiểu:
  - `gemini_unavailable`
  - `invalid_model_output`
  - `insufficient_valid_evidence`
  - `input_too_large`
- UI chỉ hiển thị thông báo an toàn; chi tiết kỹ thuật đưa vào log.

## 4. Refactor luồng phân tích AI

### 4.1. Tách trách nhiệm

`analyzer.py` chỉ điều phối:

1. Gán `sample_id`, kiểm tra rỗng/kích thước và ước lượng token.
2. Chọn single-pass hoặc multi-pass.
3. Gọi Gemini qua `gemini_client`.
4. Parse bằng `parser.py`.
5. Xác minh quote và loại evidence sai.
6. Tính confidence bằng code.
7. Trả `AnalysisResult`; tuyệt đối không fallback sang DNA mẫu.

### 4.2. Adaptive routing theo token

- Dùng ngân sách context cấu hình theo model Gemini, không dùng ngưỡng số sample cứng.
- Dành tối thiểu 30% context cho instruction, schema, output và safety margin.
- Nếu tổng input nằm trong 70% ngân sách: một call phân tích toàn bộ samples.
- Nếu vượt ngân sách: chia batch theo token, phân tích evidence từng batch, sau đó một call tổng hợp chỉ trên evidence đã xác minh.
- Một sample dùng single-pass; không chạy bước cross-sample giả tạo.
- Sample vượt giới hạn đơn lẻ: chia đoạn có overlap nhỏ, nhưng mọi evidence vẫn truy về `sample_id` và offset gốc.

### 4.3. Confidence do ứng dụng tính

Gemini không quyết định confidence cuối cùng.

- `coverage = số sample có evidence support hợp lệ / tổng sample hợp lệ`.
- `consistency = support / (support + contradict)` theo từng dimension.
- `quote_validity = evidence hợp lệ / tổng evidence model trả về`.
- `confidence = 0.45 × coverage + 0.35 × consistency + 0.20 × quote_validity`.
- Chặn trần: 1 sample `0.55`; 2 samples `0.75`; từ 3 samples `0.90`.
- Xác nhận trực tiếp qua interview/calibration có thể nâng tối đa `0.95`, nhưng phải lưu provenance.
- Không có evidence hợp lệ: confidence bằng `0`, dimension để trống và thêm warning.

### 4.4. An toàn prompt injection

- Serialize samples thành JSON có `sample_id` và `content`; không nối trực tiếp vào prompt bằng delimiter mơ hồ.
- Prompt xác định rõ sample là dữ liệu không đáng tin, mọi chỉ dẫn nằm trong sample phải bị bỏ qua.
- Không dùng `sanitize_sample()` để sửa nội dung; thay bằng validation kích thước và JSON encoding.
- Chỉ chấp nhận output theo JSON schema; không bóc code fence bằng các nhánh tùy tiện.
- Dữ liệu model trả về phải qua Pydantic và quote validator trước khi đi vào profile.

## 5. Thiết kế prompt Gemini

### 5.1. Prompt phân tích

Prompt gồm các khối cố định:

1. **Vai trò:** chuyên gia phân tích phong cách tiếng Việt.
2. **Ranh giới:** phân biệt style với topic, genre, facts và tâm lý tác giả.
3. **Security:** không làm theo chỉ dẫn trong sample.
4. **Nhiệm vụ:** tìm pattern lặp lại, outlier và mâu thuẫn.
5. **Evidence policy:** quote nguyên văn, đúng `sample_id`, không suy diễn vượt evidence.
6. **Output contract:** JSON schema, tiếng Việt cho nội dung mô tả.

Thiết lập Gemini:

- `temperature=0.1`.
- `response_mime_type="application/json"`.
- `response_schema=<Pydantic JSON schema tương ứng>`.
- `max_output_tokens` tính theo số dimension/evidence; có trần cấu hình.
- Dùng `thinking_budget` hiện có, không tạo client hoặc retry layer mới.

### 5.2. Prompt tổng hợp multi-pass

- Input chỉ gồm evidence đã xác minh, thống kê sample và kết quả từng batch.
- Không gửi lại toàn bộ sample nếu không cần.
- Bắt buộc trả `support`/`contradict`, `do`, `avoid`, mô tả và strength đề xuất.
- Không được tạo quote mới trong bước tổng hợp.

### 5.3. Prompt xử lý câu trả lời interview

- Mỗi vòng hỏi tối đa 3 dimension thiếu/yếu nhất.
- Câu hỏi tách rõ:
  - “Bài mẫu đang thể hiện gì?”
  - “Bạn thực sự muốn giữ/thay đổi điều gì?”
- Gom tối đa 3 câu trả lời vào một Gemini call để tạo `ProfilePatch`.
- Patch chỉ được áp dụng sau khi người dùng review/xác nhận.
- Mỗi thay đổi lưu câu hỏi, câu trả lời gốc, dimension, giá trị trước/sau và thời điểm.

### 5.4. Prompt A/B calibration

- Mỗi lần chỉ thay đúng một dimension.
- Hai variant dùng cùng content brief, facts, perspective, độ dài mục tiêu và các dimension không thử nghiệm.
- Output JSON gồm `variant_amplified`, `variant_restrained`; UI đổi ngẫu nhiên thành A/B.
- Không hiển thị nhãn “đậm”, “tiết chế” hoặc gợi ý đáp án.
- `temperature=0.6` để văn bản tự nhiên nhưng vẫn giữ constraint.
- Nếu Gemini không tạo được hai variant đạt constraint: báo lỗi và cho thử lại; không dùng đoạn mẫu hard-coded.

## 6. Interview và A/B phải cập nhật profile thật

### 6.1. Chọn câu hỏi

- Xếp hạng dimension theo: thiếu mô tả, confidence thấp, evidence mâu thuẫn, chưa được người dùng xác nhận.
- Chọn tối đa 3 dimension mỗi vòng.
- Không hỏi lại dimension đã xác nhận nếu không có evidence mới gây mâu thuẫn.

### 6.2. Blind mapping

`CalibrationSession` phải lưu:

- `session_id`
- `dimension`
- `content_brief`
- `variant_a`, `variant_b`
- `shuffle_mapping`: A/B -> `amplified | restrained`
- `selected`
- `created_at`

Khi người dùng chọn:

- Tra mapping để biết hướng thực.
- Cập nhật `strength` theo hướng đã chọn.
- Lưu đoạn được chọn vào `examples`.
- Tăng `revision`, ghi `CalibrationRecord`, rồi compile lại đúng các agent bị ảnh hưởng.

## 7. Refactor compiler và overrides

### 7.1. Compiler xác định base rõ ràng

- Bỏ `_load_base_skill()` duyệt `iterdir()` và lấy thư mục đầu tiên.
- `compile_style()` nhận `base_style_slug`; mặc định lấy từ profile (`reflective`).
- Đọc chính xác `skills/{mode}/{base_style_slug}/{filename}`.
- Thiếu base file hoặc agent bắt buộc phải fail-fast; không sinh prompt mặc định giả.

Interface mục tiêu:

```python
def compile_style(
    profile: StyleProfile,
    mode: str,
    changed_dimensions: list[str] | None = None,
) -> CompileResult:
    ...
```

### 7.2. Canonical IR và full-template overlay

- Không rút skill thành `prompt + style_rules`.
- Canonical IR lưu:
  - ID/version/base hash.
  - `agent_id`, filename và workflow order.
  - snapshot Invariant Contract.
  - style overlays theo dimension.
  - effective skill đầy đủ sau overlay.
- Deep-copy toàn bộ base skill; chỉ sửa vùng style được định nghĩa.
- Giữ nguyên role, tasks, input/output contract, handoff, workflow, context policy và mọi field chưa biết.
- `DIMENSION_AGENTS`, `AGENT_FILENAME_MAP`, `REQUIRED_AGENTS` là contract tĩnh, có test bao phủ 100%.
- Output được sắp xếp ổn định để cùng input luôn tạo cùng kết quả.

### 7.3. Phát hiện xung đột

- Báo lỗi nếu một rule xuất hiện đồng thời trong `do` và `avoid`.
- Báo lỗi nếu overlay cố sửa invariant.
- Warning cho dimension không map tới agent; không âm thầm bỏ.
- Compile chỉ thành công khi không còn conflict mức error.

### 7.4. Overrides

- Xóa `resolve_conflict_with_llm()` giả và comment “LLM resolved”.
- Three-way diff trả `MergeResult(merged_ir, conflicts)`.
- Invariant bị sửa: từ chối ngay.
- Thay đổi một phía: merge tự động.
- Hai phía sửa khác nhau: tạo `MergeConflict` để UI/người dùng chọn; không tự nối chuỗi hoặc tự gọi Gemini.
- Sau resolve phải chạy lại schema validation, invariant diff và compile validation.

## 8. Migration, archive và publish

### 8.1. Migration

- Sửa lỗi indentation/syntax hiện có trong `migration.py` trước các thay đổi khác.
- `import_existing_style()` không trả `VoiceDNA()` rỗng như kết quả thật.
- Legacy YAML không đủ evidence trả:
  - `dna=None`
  - `analysis_status="incomplete_legacy_data"`
  - `confidence=0`
  - `is_draft=True`
  - warning yêu cầu phân tích/xác nhận lại.
- Reader v1 -> v2 là pure function, idempotent và có unit test.

### 8.2. Archive

- Manifest dùng `schema_version: 2`.
- Export gồm tối thiểu `profile.json`, manifest và các effective YAML của style.
- Import kiểm checksum và path traversal trước khi ghi/extract.
- Archive v1 được migrate trong bộ nhớ sang v2 rồi mới cho review/publish.
- Archive có version lớn hơn version hỗ trợ phải bị từ chối rõ ràng.
- Không publish trực tiếp trong thao tác import.

### 8.3. Publish Safety Pipeline

Tách khỏi `ui/app.py` sang `publisher.py`:

1. Tạo staging riêng cùng filesystem với runtime.
2. Ghi full effective skills, `style_meta.yaml` và profile v2.
3. Validate schema, required agent files, workflow references, invariant diff và compile status.
4. Backup immutable runtime hiện có.
5. Đổi runtime cũ sang tombstone, staging sang runtime.
6. Nếu lỗi, rollback tombstone; chỉ xóa tombstone sau khi toàn bộ bước thành công.

Yêu cầu:

- UI chỉ gọi service và hiển thị kết quả; không tự thao tác file.
- Không làm mất field IR/template khi serialize YAML.
- Profile chưa xác nhận, còn conflict hoặc status khác `complete` không được publish.
- Thao tác phải an toàn khi tên slug trùng, validation lỗi hoặc rename thất bại.

## 9. Thứ tự triển khai

### Giai đoạn 0 — Khôi phục baseline

- Sửa `migration.py`.
- Chụp test baseline; bổ sung fixture profile/archive v1.

### Giai đoạn 1 — Schema v2 và compatibility

- Tạo nested models, result/error models và v1 reader.
- Cập nhật archive v2.
- Chuyển toàn bộ code đọc/ghi profile sang API mới.

### Giai đoạn 2 — Analyzer, parser và prompts

- Bổ sung structured JSON config tối thiểu cho Gemini client.
- Tách prompt builder/parser/validator.
- Triển khai adaptive routing, evidence verification và confidence deterministic.
- Xóa mọi fallback DNA/claim/variant hard-coded.

### Giai đoạn 3 — Interview và calibration

- Chọn tối đa 3 dimension yếu.
- Áp dụng `ProfilePatch` có xác nhận/provenance.
- Lưu blind mapping và cập nhật profile thật sau lựa chọn.

### Giai đoạn 4 — Compiler và overrides

- Chuyển sang base explicit + full-template overlay.
- Giữ Invariant Contract và Adjacency Matrix.
- Thay conflict giả bằng `MergeResult` có conflict explicit.

### Giai đoạn 5 — Publisher và UI adapter

- Tách Publish Safety Pipeline thành service.
- Nối profile/interview/calibration mới vào wizard.
- Giữ layout và luồng 5 bước hiện có.

### Giai đoạn 6 — Regression và tài liệu

- Chạy toàn bộ test Voice Lab và workflow.
- Cập nhật `current_architecture.md`, changelog và hướng dẫn dữ liệu v1/v2 sau khi code hoàn tất.

## 10. Kế hoạch kiểm thử

### 10.1. Models, migration, archive

- Đọc VoiceDNA v1 dạng chuỗi và chuyển đúng sang nested v2.
- Migrate lặp lại không làm biến đổi thêm dữ liệu.
- Legacy thiếu dữ liệu luôn ở trạng thái draft/incomplete.
- Archive v1 migrate được; v2 round-trip giữ nguyên profile.
- Reject checksum sai, path traversal và schema tương lai.

### 10.2. Analyzer và prompt

- Sample chứa prompt injection không thay đổi nhiệm vụ.
- Output sai JSON/schema tạo `AnalysisError`, không tạo profile giả.
- Quote sai sample hoặc sai nguyên văn bị reject.
- Một sample không gọi synthesis; input lớn đi đúng multi-pass.
- Confidence đúng công thức và đúng trần 1/2/3 samples.
- Gemini 429/5xx dùng retry của client; analyzer không retry chồng.

### 10.3. Interview và calibration

- Mỗi vòng không quá 3 câu hỏi và chọn đúng dimension yếu nhất.
- Answer chưa xác nhận không làm đổi profile.
- `shuffle_mapping` truy ngược đúng A/B.
- A/B chỉ thay dimension mục tiêu.
- Lựa chọn cập nhật strength/examples/history và chỉ recompile agent liên quan.

### 10.4. Compiler, overrides, publish

- Cùng input tạo output deterministic.
- Không mất field/capability của base skill.
- Invariant Contract không đổi.
- Adjacency Matrix bao phủ đủ 12 dimension và 13 agent.
- Incremental compile chỉ tác động agent được map.
- Conflict hai phía không bị tự merge giả.
- Publish validation lỗi không thay runtime.
- Rename lỗi rollback được; backup và runtime cuối cùng hợp lệ.

### 10.5. Regression

- Wizard hoàn tất luồng: samples -> evidence -> interview -> A/B -> review -> publish.
- Deep mode và Moment mode đều compile/publish đủ required agents.
- Các workflow hiện có vẫn đọc được style mới.
- Không có call tới Antigravity hoặc OpenAI trong Voice Lab.

## 11. Tiêu chí nghiệm thu

- Không còn bất kỳ DNA, evidence hoặc A/B variant giả khi AI lỗi.
- 100% evidence active truy được về quote nguyên văn và sample.
- Confidence được tính bằng code, có provenance và giới hạn rõ ràng.
- Interview/A-B thực sự cập nhật profile và compiled output.
- Compiler dùng base xác định, giữ nguyên toàn bộ capability và invariant.
- Import v1 tương thích; mọi dữ liệu ghi mới dùng v2.
- Publish không để lại runtime dở dang và rollback được khi lỗi.
- Toàn bộ test mới và test hiện có đều pass.
- Voice Lab chỉ phụ thuộc Gemini API trong phạm vi bản refactor này.

## 12. Ngoài phạm vi

- Antigravity Bridge và local model.
- OpenAI API hoặc multi-provider router.
- Redesign UI/UX lớn.
- Thay đổi workflow nghiệp vụ Deep/Moment.
- Tự động dùng LLM để giải quyết conflict override.
- Thay đổi các style runtime hiện có trước khi migration/validation hoàn tất.

---

# Báo cáo Audit Triển khai (Claude Opus 4.6)

> **Reviewer:** Claude Opus 4.6 | **Ngày:** 2026-07-27  
> **Plan:** [2026-07-27-voice-lab-refactor-plan-final.md](file:///D:/Nghiên cứu AI/write_blog/docs/2026-07-27-voice-lab-refactor-plan-final.md)

---

### 1. 🔍 ĐỐI CHIẾU SỰ TUÂN THỦ (PLAN VS IMPLEMENTATION)

| Mã Task | Tên Task (Trong PLAN) | Trạng thái | Ghi chú kỹ thuật nhanh |
| :--- | :--- | :--- | :--- |
| §3.2 | `DimensionProfile` nested model | ✅ Đạt | [models.py:31-39](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L31-L39) — đúng 8 trường, v1 validator tại L56-65 |
| §3.3 | `EvidenceClaim` v2 (`exact_quote`, `stance`, `rejection_reason`) | ✅ Đạt | [models.py:75-105](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L75-L105) — có migrate v1 `quote`→`exact_quote` |
| §3.4 | `StyleProfile` bổ sung (`analysis_status`, history, `base_style_slug`) | ✅ Đạt | [models.py:150-194](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L150-L194) — `enforce_publish_state` validator đúng |
| §3.5 | `AnalysisResult` / `AnalysisError` với mã lỗi | ✅ Đạt | [models.py:196-228](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L196-L228) — đủ 4 error code |
| §3.1 | `schema_version=2`, `revision`, reader v1→v2 | ✅ Đạt | `migrate_v1_profile` L172-185, `profile_version`→`revision` |
| §2.2 | Tách `prompts.py`, `parser.py`, `publisher.py` | ✅ Đạt | 3 file mới tồn tại, đúng trách nhiệm |
| §4.1 | Tách analyzer thành orchestrator thuần | ✅ Đạt | [analyzer.py](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/analyzer.py) gọi `prompts` + `parser`, không parse trực tiếp |
| §4.2 | Adaptive routing theo token (không ngưỡng cứng) | ✅ Đạt | L28-30 dùng `DEFAULT_CONTEXT_TOKENS` + env var, L215 so sánh `total_tokens <= input_budget` |
| §4.3 | Confidence tính bằng code, đúng công thức, đúng trần | ✅ Đạt | [parser.py:86-104](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/parser.py#L86-L104) — `0.45*cov+0.35*cons+0.20*qv`, cap 0.55/0.75/0.90 |
| §4.4 | An toàn prompt injection: JSON serialize, không `sanitize_sample` | ✅ Đạt | [prompts.py:70-99](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/prompts.py#L70-L99) — `json.dumps(samples)`, AN TOÀN block rõ ràng |
| §5.1 | Prompt phân tích 6 khối + `temperature=0.1` + structured output | ✅ Đạt | Prompt đủ VAI TRÒ / AN TOÀN / NHIỆM VỤ / OUTPUT; `_call_structured` dùng `response_mime_type` + `response_schema` |
| §5.2 | Prompt tổng hợp: chỉ dùng evidence verified, không gửi lại sample | ✅ Đạt | [prompts.py:102-125](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/prompts.py#L102-L125) |
| §5.3 | Interview patch qua Gemini + review trước khi áp dụng | ✅ Đạt | `propose_interview_patch` → `apply_interview_patch(confirmed=True)` |
| §5.4 | A/B: `variant_amplified`/`restrained`, `temperature=0.6`, no bias label | ✅ Đạt | [prompts.py:152-172](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/prompts.py#L152-L172), [interview.py:249](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/interview.py#L249) |
| §6.1 | Bỏ `_load_base_skill` duyệt `iterdir()`, dùng base explicit | ✅ Đạt | [compiler.py:110-121](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L110-L121) — đường dẫn xác định `skills/{mode}/{base_style_slug}/{filename}` |
| §6.2 | Canonical IR full-template overlay, deep-copy, giữ invariant | ✅ Đạt | [compiler.py:217-261](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L217-L261) — `copy.deepcopy(base)`, invariant check L232-234 |
| §6.3 | Phát hiện xung đột `do`∩`avoid`, overlay sửa invariant | ✅ Đạt | [compiler.py:137-144](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L137-L144), L232-234 |
| §6.4 | Overrides: bỏ `resolve_conflict_with_llm` giả, `MergeResult` explicit | ✅ Đạt | [overrides.py](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/overrides.py) — `MergeConflict` thay vì tự nối chuỗi |
| §6.2 | `CalibrationSession` lưu `shuffle_mapping` | ✅ Đạt | [models.py:134-148](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L134-L148) |
| §6.2 | `apply_calibration_selection` cập nhật strength/examples/history + recompile | ⚠️ Sai lệch | [interview.py:302-339](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/interview.py#L302-L339) — cập nhật profile đúng, nhưng **không tự gọi `compile_style`**. Plan §6.2 L231: "rồi compile lại đúng các agent bị ảnh hưởng". Caller (UI) phải tự compile — chấp nhận được nếu UI đã làm, nhưng lệch contract |
| §7.1 | Migration: sửa indentation bug, `dna=None`, `analysis_status="incomplete_legacy_data"` | ✅ Đạt | [migration.py:59-69](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/migration.py#L59-L69) — không còn `VoiceDNA()` rỗng |
| §7.2 | Archive: `schema_version=2`, v1 migration, reject future version, skill export | ✅ Đạt | [archive.py:50](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/archive.py#L50), L83-87 reject future, L100-107 migrate |
| §8.3 | Publish Safety Pipeline: staging→validate→backup→atomic replace→rollback | ✅ Đạt | [publisher.py:105-174](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L105-L174) — tombstone pattern, rollback on exception |
| §8.3 | Profile chưa `confirmed`/`complete` bị chặn publish | ✅ Đạt | [publisher.py:32-35](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L32-L35) |
| §8.3 | Protected style không bị ghi đè | ✅ Đạt | [publisher.py:127-131](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/publisher.py#L127-L131) |
| §2.3 | `gemini_client.py`: thực thi `response_mime_type`/`response_schema` | ✅ Đạt | [gemini_client.py:124-148](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/../gemini_client.py#L124-L148) — cả SDK lẫn REST path |
| §2.3 | Không thêm retry tại analyzer; dùng retry của client | ✅ Đạt | `_call_structured` gọi 1 lần, test L221 xác nhận `calls["count"]==1` |
| §12 | Không có Antigravity / OpenAI import trong voice_lab | ✅ Đạt | grep xác nhận 0 match |
| §9 Giai đoạn 6 | Cập nhật `current_architecture.md` | ❌ Sót | File [current_architecture.md](file:///D:/Nghiên cứu AI/write_blog/docs/current_architecture.md) vẫn còn mô tả cũ: `archive.py` chưa có, `prompts.py`/`parser.py`/`publisher.py` chưa được liệt kê, mô tả module cũ |
| §10 | Test bao phủ: injection, malformed, quote sai, confidence, round-trip, rollback | ✅ Đạt | [test_voice_lab.py](file:///D:/Nghiên cứu AI/write_blog/tests/test_voice_lab.py) — 661 dòng, 27 test cases |
| §10.5 | Regression: deep + moment mode compile/publish | ✅ Đạt | `test_moment_mode_compiles_and_publishes_all_required_agents` L610 |

**Tổng kết:** 28/30 task **Đạt**, 1 **Sai lệch nhẹ**, 1 **Sót**.

---

### 2. ⚡ TỐI ƯU HÓA WORKFLOW & KIẾN TRÚC

- **Lỗi crash / bảo mật nghiêm trọng:** Không phát hiện. Các trường hợp Gemini lỗi đều chuyển thành `AnalysisError` có `retryable` flag. Path traversal trong archive/publisher được chặn. Prompt injection được xử lý đúng (JSON serialize + security block trong prompt). API key không bị leak qua log.

- **Lệch pha Data Contract:**
  - `EvidenceClaim` bỏ trường `confidence` (L98 `data.pop("confidence", None)`) — đúng Plan vì confidence giờ thuộc `DimensionProfile`. Nhưng `CanonicalIR` vẫn giữ trường `prompt` và `style_rules` dạng flat ([models.py:244-245](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L244-L245)) dù Plan §7.2 nói "Không rút skill thành `prompt + style_rules`". Hai trường này **dư thừa** so với `effective_skill` — chúng tồn tại vì backward-compat với UI cũ nhưng không phải contract chính thức.
  - `CanonicalIR.output_contract` / `handoff_contract` / `context_policy` dùng `Any = None` — Plan §7.2 nói lưu "snapshot Invariant Contract" nhưng kiểu `Any` không enforce cấu trúc, tạo rủi ro khi diff.

- **Trùng lặp / Thừa thãi:**
  - `INVARIANT_FIELDS` khai báo 2 lần: [overrides.py:8-17](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/overrides.py#L8-L17) và [compiler.py:86-97](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L86-L97) (`INVARIANT_SKILL_FIELDS`). Hai set **không giống nhau** — overrides bảo vệ IR-level fields, compiler bảo vệ skill-level fields — nhưng tên gần giống gây nhầm lẫn và sai sót khi bổ sung field mới.
  - `_profile_confidence()` trùng logic giữa [interview.py:342-348](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/interview.py#L342-L348) và [analyzer.py:168-173](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/analyzer.py#L168-L173) — cùng tính mean confidence của non-empty dimensions.
  - `sanitize_sample()` vẫn còn trong [models.py](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py) nhưng không còn được import/sử dụng ở bất kỳ file nào — dead code.

---

### 3. 🛠️ VECTOR TINH CHỈNH CODEBASE (REFACTOR VECTORS)

---

**Vị trí:** [models.py](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py) — hàm `sanitize_sample` (nếu còn từ v1)  
**Vấn đề:** Dead code. Plan §4.4 xác nhận "Không dùng `sanitize_sample()`" — grep xác nhận 0 caller.  
**Giải pháp Refactor gọn:**
```python
# Xóa toàn bộ hàm sanitize_sample và import re ở đầu file
# (nếu re không còn dùng cho mục đích khác)
```

---

**Vị trí:** [interview.py:276-285](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/interview.py#L276-L285) — `calibrate_ab` — validate 100-150 từ  
**Vấn đề:** Nếu Gemini trả variant 99 hoặc 151 từ, hàm raise `AnalysisError` bắt user thử lại, nhưng **không retry Gemini tự động**. Trên thực tế LLM rất thường lệch ±5 từ so với constraint. Đây là đoạn dễ gây frustration nhất trên UI.  
**Giải pháp Refactor gọn:**
```python
# Nới tolerance ±10% thay vì exact 100-150:
MIN_WORDS, MAX_WORDS = 90, 165
if any(length < MIN_WORDS or length > MAX_WORDS for length in lengths):
```

---

**Vị trí:** [analyzer.py:168-173](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/analyzer.py#L168-L173) + [interview.py:342-348](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/interview.py#L342-L348)  
**Vấn đề:** Logic tính profile-level confidence bị duplicate giữa 2 file.  
**Giải pháp Refactor gọn:**
```python
# Thêm vào models.py hoặc StyleProfile:
def compute_profile_confidence(profile: StyleProfile) -> float:
    if not profile.dna: return 0.0
    dims = list(profile.dna.non_empty_dimensions().values())
    return round(sum(d.confidence for d in dims) / max(len(dims), 1), 4)
```

---

**Vị trí:** [compiler.py:86-97](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/compiler.py#L86-L97) + [overrides.py:8-17](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/overrides.py#L8-L17)  
**Vấn đề:** Hai constant set "invariant" riêng biệt (`INVARIANT_SKILL_FIELDS` vs `INVARIANT_FIELDS`) dùng cho 2 tầng khác nhau nhưng tên gần giống, dễ nhầm khi maintain.  
**Giải pháp Refactor gọn:**
```python
# Rename rõ nghĩa trong overrides.py:
IR_LEVEL_INVARIANTS = {"id", "schema_version", "agent_id", ...}
# Rename rõ nghĩa trong compiler.py:
SKILL_LEVEL_INVARIANTS = ("name", "mode", "purpose", ...)
```

---

**Vị trí:** [migration.py:42-44](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/migration.py#L42-L44) — khối `try/except/else`  
**Vấn đề:** `else` clause tại L43-44 (`warning = ""`) chỉ chạy nếu `try` thành công — nhưng khi try thành công, hàm đã `return` tại L40. Dòng L43-44 **unreachable dead code**.  
**Giải pháp Refactor gọn:**
```python
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            warning = f"Không thể đọc profile cũ: {exc}"
    # Xóa block else: vì return đã thoát hàm ở L40
    else:
```

---

**Vị trí:** [models.py:236-238](file:///D:/Nghiên cứu AI/write_blog/engine/voice_lab/models.py#L236-L238) — `CanonicalIR` invariant fields dùng `Any`  
**Vấn đề:** `output_contract`, `handoff_contract`, `context_policy` kiểu `Any = None` — không enforce contract khi diff/merge. Plan §7.2 yêu cầu "snapshot Invariant Contract" nhưng `Any` không đảm bảo serializability nhất quán.  
**Giải pháp Refactor gọn:**
```python
# Thay bằng Dict hoặc Optional[Dict] để ensure JSON-safe:
output_contract: Optional[Dict[str, Any]] = None
handoff_contract: Optional[Dict[str, Any]] = None
context_policy: Optional[Dict[str, Any]] = None
```

---

**Vị trí:** [docs/current_architecture.md](file:///D:/Nghiên cứu AI/write_blog/docs/current_architecture.md)  
**Vấn đề:** Plan §9 Giai đoạn 6 yêu cầu "Cập nhật `current_architecture.md`" — file vẫn liệt kê cấu trúc cũ: thiếu `prompts.py`, `parser.py`, `publisher.py`; mô tả `archive.py` chưa cập nhật; `models.py` mô tả không phản ánh `DimensionProfile`/`AnalysisResult`/`CompileResult`.  
**Giải pháp:** Cập nhật directory tree và mô tả module trong `current_architecture.md` theo codebase mới.

---

## Kết quả xử lý Audit Claude Opus 4.6

**Ngày xử lý:** 27/07/2026  
**Trạng thái:** Hoàn tất

- Nới validation A/B từ biên cứng `100–150` sang dung sai `90–165`; prompt vẫn nhắm mục tiêu `100–150`.
- Gom logic confidence cấp profile vào `compute_profile_confidence()` dùng chung.
- Đổi tên rõ tầng: `SKILL_LEVEL_INVARIANTS` và `IR_LEVEL_INVARIANTS`.
- Xóa nhánh `try/except/else` không thể chạy trong migration.
- Chuẩn hóa ba contract của `CanonicalIR` thành `Optional[Dict[str, Any]]`; scalar legacy được bọc thành `{"reference": ...}`.
- Xóa `prompt` và `style_rules` dư thừa khỏi Canonical IR; `effective_skill` là nguồn đầy đủ duy nhất.
- Bật `extra="forbid"` cho Canonical IR để ngăn field ngoài contract bị bỏ qua âm thầm.
- `sanitize_sample()` đã không còn trong code tại thời điểm audit; không có thay đổi bổ sung.
- `current_architecture.md` đã được cập nhật trước thời điểm nhận báo cáo và đã có đủ `prompts.py`, `parser.py`, `archive.py`, `publisher.py`.
- UI vẫn compile sau khi áp dụng A/B; lần compile đầu tiên cần đủ toàn bộ agent để phục vụ publish, nên không tạo dependency ngược từ `interview.py` sang compiler.
- Bổ sung regression test cho tolerance A/B, helper confidence dùng chung, contract scalar normalization và Canonical IR mới.
