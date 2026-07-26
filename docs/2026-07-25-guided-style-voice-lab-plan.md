# Kế hoạch Guided Style Voice Lab

> **Ngày:** 2026-07-25  
> **Trạng thái:** Kế hoạch đề xuất  
> **Phạm vi:** Local UI, một người dùng, hai writing mode `deep` và `moment`  
> **Mục tiêu:** Giúp người dùng định hình, kiểm chứng và chỉnh sửa phong cách bằng ngôn ngữ tự nhiên cùng bài viết mẫu, thay vì phải thao tác trực tiếp trên 13 file YAML.

---

## 1. Bối cảnh và vấn đề

Hệ thống hiện đã hỗ trợ:

- quản lý style riêng theo `deep` và `moment`;
- tạo style mới bằng cách clone style có sẵn;
- đổi tên, chỉnh sửa và xóa custom style;
- chỉnh trực tiếp YAML của từng agent;
- kiểm tra hợp đồng file và routing bằng dry-run.

Khoảng trống còn lại nằm ở trải nghiệm **định hình phong cách**:

- Người dùng phải biết chính xác nên sửa agent và trường YAML nào.
- Mô tả trong `style_meta.yaml` chưa tự chuyển thành hành vi của agents.
- Clone có thể chỉ tạo một style mới về tên, trong khi toàn bộ YAML vẫn giống style nguồn.
- Một phong cách cá nhân thường có phần giọng viết dùng chung, nhưng cần biểu hiện khác nhau trong Deep và Moment mode.
- Việc sinh lại YAML có nguy cơ ghi đè các tinh chỉnh thủ công đã thực hiện trước đó.

Guided Style Voice Lab bổ sung một lớp mô hình thân thiện nằm trên YAML:

```text
Bài viết mẫu của người dùng
        ↓
Voice DNA dùng chung
        ↓
Deep Profile + Moment Profile
        ↓
Generated Agent YAML + Agent Overrides
        ↓
skills/deep/<slug>/ và skills/moment/<slug>/
```

---

## 2. Mục tiêu và phạm vi

### 2.1. Mục tiêu V1

1. Cho phép người dùng cung cấp các bài viết của chính mình để hệ thống phân tích giọng viết.
2. Tạo một hồ sơ phong cách có dẫn chứng, độ tin cậy và khả năng chỉnh sửa.
3. Phân tách rõ:
   - `Voice DNA` dùng chung;
   - `Deep Profile`;
   - `Moment Profile`.
4. Dùng phỏng vấn có hướng dẫn và lựa chọn A/B để bổ sung dữ liệu còn thiếu.
5. Sinh cấu hình đầy đủ cho 7 Deep agents và 6 Moment agents.
6. Yêu cầu người dùng duyệt profile và diff trước khi ghi vào `skills/`.
7. Bảo toàn các tinh chỉnh riêng từng agent qua cơ chế override.
8. Giữ YAML Editor làm chế độ nâng cao, không bắt người dùng phổ thông phải hiểu YAML.

### 2.2. Ngoài phạm vi V1

- Không có đăng nhập, user ID hoặc phân quyền.
- Không tự động học sau mỗi lần người dùng sửa bài production.
- Không tự động cập nhật style mà không có bước duyệt.
- Không phân tích bài của tác giả khác làm nguồn mô phỏng phong cách.
- Không thay đổi flow, thứ tự agents hoặc Artifact/Handoff contract.
- Không dùng dry-run để đánh giá chất lượng văn phong; dry-run chỉ kiểm tra routing và hợp đồng I/O.

---

## 3. Các quyết định thiết kế

### 3.1. Một Style Family, hai biến thể mode

Một phong cách được quản lý như một **Style Family**:

```text
Style Family
├── Voice DNA
├── Deep Profile
├── Moment Profile
└── Agent Overrides
```

Ví dụ, style “Minh hóm hỉnh” có thể dùng chung:

- văn nói tự nhiên;
- slang và emoji;
- nhịp câu nhanh;
- sự hài hước nhẹ;
- quan hệ gần gũi với độc giả.

Deep Profile bổ sung:

- cấu trúc câu chuyện;
- chiều sâu phản tư;
- mức độ chuyển hóa;
- cách kết luận;
- mức thách thức người đọc.

Moment Profile bổ sung:

- mật độ chi tiết giác quan;
- năng lượng hiện tại;
- giới hạn diễn giải;
- độ ngắn;
- mức tiết chế tín hiệu trực giác.

### 3.2. Style Profile là nguồn chuẩn

- Người dùng chỉnh Style Profile bằng ngôn ngữ tự nhiên.
- YAML được sinh từ Style Profile.
- Generated YAML không phải nơi lưu tinh chỉnh thủ công lâu dài.
- Tinh chỉnh riêng từng agent được lưu dưới dạng override.

### 3.3. Người dùng phải duyệt trước khi publish

Hệ thống không được tự động ghi đè style đang hoạt động. Quy trình bắt buộc:

1. Phân tích hoặc chỉnh profile.
2. Sinh bản nháp cấu hình.
3. Validate.
4. Hiển thị semantic diff và YAML diff.
5. Người dùng xác nhận.
6. Publish atomic vào `skills/`.

### 3.4. Chỉ dùng bài của chính người dùng

- Bài mẫu phải do người dùng cung cấp và xác nhận quyền sử dụng.
- Mỗi bài được gắn nhãn `deep`, `moment` hoặc `general`.
- Hệ thống phân tích đặc điểm lặp lại, không sao chép nguyên văn bài mẫu vào generated prompts.

---

## 4. Mô hình Style Profile

### 4.1. Voice DNA dùng chung

Voice DNA cần mô tả tối thiểu:

| Nhóm | Nội dung |
| --- | --- |
| Giọng kể | ngôi kể, khoảng cách với độc giả, mức thân mật |
| Nhịp điệu | độ dài câu/đoạn, xen kẽ nhịp nhanh-chậm |
| Từ vựng | văn nói/văn viết, slang, thuật ngữ, emoji |
| Trực diện | nói thẳng hay gợi mở, mức hedging |
| Hài hước | loại hài hước, tần suất, giới hạn |
| Hình ảnh | mức dùng ẩn dụ, so sánh và chi tiết cụ thể |
| Cảm xúc | cường độ, độ dễ tổn thương, cách tự bộc lộ |
| Quan hệ độc giả | trò chuyện, đồng hành, thách thức hay hướng dẫn |
| Mở bài | cảnh, câu hỏi, tuyên bố, đối thoại hoặc hồi tưởng |
| Kết bài | kết luận, câu hỏi mở, dư âm hoặc lời mời hành động |
| Always do | các hành vi luôn cần giữ |
| Avoid | từ ngữ, cấu trúc và hành vi tuyệt đối tránh |

Mỗi nhận định trích xuất phải có:

- `value`;
- `confidence`;
- `evidence_ids`;
- `status`: `suggested`, `accepted`, `edited`, `rejected`.

### 4.2. Deep Profile

Deep Profile gồm:

- `reflection_depth`;
- `story_arc`;
- `transformation_explicitness`;
- `vulnerability_level`;
- `reader_challenge_level`;
- `philosophy_density`;
- `conclusion_strength`;
- `preferred_length`;
- `deep_always_do`;
- `deep_avoid`.

### 4.3. Moment Profile

Moment Profile gồm:

- `sensory_density`;
- `present_moment_strength`;
- `sentence_breath`;
- `interpretation_restraint`;
- `signal_strength`;
- `humor_in_moment`;
- `ending_resonance`;
- `preferred_length`;
- `moment_always_do`;
- `moment_avoid`.

### 4.4. Thang giá trị

Các thuộc tính định lượng sử dụng thang 1–5, nhưng UI phải hiển thị nhãn có nghĩa thay vì chỉ hiện số.

Ví dụ:

```text
Độ trực diện
1 — Rất gợi mở
2 — Thiên về gợi ý
3 — Cân bằng
4 — Khá thẳng
5 — Rất trực diện
```

---

## 5. Cấu trúc lưu trữ

Nguồn chuẩn của Voice Lab được lưu tách khỏi runtime skills:

```text
style_profiles/
└── <family_slug>/
    ├── style_profile.yaml
    ├── evidence.yaml
    ├── generation_manifest.yaml
    ├── samples/
    │   ├── sample-001.md
    │   └── sample-002.md
    ├── generated/
    │   ├── deep/
    │   │   └── <agent>.yaml
    │   └── moment/
    │       └── <agent>.yaml
    └── overrides/
        ├── deep/
        │   └── <agent>.patch.yaml
        └── moment/
            └── <agent>.patch.yaml
```

Quy tắc:

- `samples/` chứa dữ liệu cá nhân và phải được thêm vào `.gitignore`.
- `style_profile.yaml` là nguồn chuẩn do người dùng duyệt.
- `generated/` lưu base YAML gần nhất do compiler tạo.
- `overrides/` chỉ lưu thay đổi thủ công so với generated base.
- Runtime tiếp tục đọc:
  - `skills/deep/<slug>/`;
  - `skills/moment/<slug>/`.

`style_meta.yaml` của mỗi mode bổ sung:

```yaml
family_slug: minh-hom-hinh
profile_version: 3
generation_status: published
last_generated_at: "2026-07-25T14:00:00Z"
```

Slug của system style vẫn bất biến. Tên hiển thị có thể sửa.

---

## 6. Luồng trải nghiệm người dùng

### Bước 1: Khởi tạo Style Family

Người dùng nhập:

- tên hiển thị;
- slug;
- mô tả ngắn;
- mode muốn tạo trước: Deep, Moment hoặc cả hai;
- base style cho từng mode, mặc định `reflective`.

### Bước 2: Cung cấp bài mẫu

- Khuyến nghị 3–5 bài.
- Cho phép dán văn bản hoặc tải `.md`/`.txt`.
- Người dùng gắn nhãn từng bài.
- Hệ thống hiển thị số từ và cảnh báo nếu dữ liệu quá ít hoặc quá giống nhau.

V1 cho phép tiếp tục với ít nhất một bài, nhưng phải hiển thị độ tin cậy thấp.

### Bước 3: Phân tích Evidence

AI tạo các nhận định cho Voice DNA và Mode Profile.

Mỗi nhận định hiển thị:

- mô tả dễ hiểu;
- một hoặc vài đoạn dẫn chứng ngắn;
- độ tin cậy;
- nút Chấp nhận, Sửa, Loại bỏ.

Không có nhận định nào được đưa vào profile nếu chưa được người dùng duyệt.

### Bước 4: Guided Interview

Hệ thống chỉ hỏi những chiều:

- chưa có evidence;
- có evidence mâu thuẫn;
- có confidence thấp;
- có ảnh hưởng lớn tới nhiều agents.

Giới hạn 6–8 câu cho một vòng.

Câu hỏi phải dùng ví dụ cụ thể, không dùng thuật ngữ prompt engineering.

### Bước 5: A/B Calibration

- Tối đa ba vòng.
- Mỗi vòng tập trung vào một hoặc hai chiều chưa chắc chắn.
- Hai phiên bản dùng cùng nội dung và chỉ khác thuộc tính đang kiểm tra.
- Người dùng chọn A, B, “kết hợp cả hai” hoặc “không bản nào”.
- Lựa chọn chỉ cập nhật Style Profile, chưa ghi YAML.

### Bước 6: Profile Review

Hiển thị:

- Voice DNA;
- Deep Profile;
- Moment Profile;
- evidence và confidence;
- các thuộc tính chưa đủ dữ liệu;
- agent nào sẽ bị ảnh hưởng.

### Bước 7: Generate và Preview

Compiler sinh YAML tuần tự theo mode và agent.

UI hiển thị:

- tiến độ;
- validation status;
- retry status;
- semantic diff;
- YAML diff;
- override conflicts.

### Bước 8: Publish

Chỉ cho phép publish khi:

- đủ 7/6 agent files;
- toàn bộ YAML parse được;
- mọi invariant còn nguyên;
- không còn unresolved conflict;
- `validate_style_contract` thành công.

---

## 7. Compiler và Agent Overrides

### 7.1. Invariant không được thay đổi

Style compiler không được thay đổi:

- agent ID;
- tên file agent;
- số lượng agents;
- `output`/`handoff` contract;
- tên Artifact/Handoff;
- workflow order;
- context policy;
- các giới hạn bảo vệ cốt lõi của từng mode.

### 7.2. Pipeline sinh YAML

Cho mỗi agent:

1. Đọc base style.
2. Chọn các phần Voice DNA liên quan.
3. Chọn Deep hoặc Moment Profile.
4. Sinh candidate YAML.
5. Parse và validate.
6. Nếu lỗi, gửi lỗi cụ thể cho model và retry tối đa hai lần.
7. Lưu candidate vào `generated/`.
8. Áp dụng Agent Overrides.
9. Validate effective YAML.
10. Ghi trạng thái vào generation manifest.

Nếu vẫn lỗi sau hai lần retry:

- không fallback âm thầm về `reflective`;
- giữ bản generated cũ;
- đánh dấu agent thất bại;
- chặn publish mode đó.

### 7.3. Override format

Override dùng các phép toán:

```yaml
operations:
  - op: replace
    path: /style_rules/1
    value: preserve_slang_and_emoji
  - op: add
    path: /style_rules/-
    value: alternate_short_and_medium_paragraphs
  - op: remove
    path: /forbidden_actions/2
```

Hỗ trợ:

- `add`;
- `replace`;
- `remove`.

Khi generated base thay đổi, hệ thống áp lại patch:

- thành công: giữ override;
- path không tồn tại hoặc sai kiểu: tạo conflict;
- conflict phải được người dùng xử lý trước khi publish.

YAML Editor nâng cao hiển thị:

- Generated Base;
- Effective YAML;
- Override Operations;
- Diff.

Khi người dùng lưu Effective YAML, hệ thống tính patch so với Generated Base thay vì ghi đè nguồn chuẩn.

---

## 8. Backend và API

Tạo lớp backend riêng, không làm phình `style_manager.py`.

Các interface chính:

```python
analyze_samples(family_slug, samples, client) -> AnalysisResult
save_style_profile(profile) -> ValidationReport
generate_interview(profile, evidence) -> list[InterviewQuestion]
apply_interview_answers(profile, answers) -> StyleProfile
generate_calibration_pairs(profile, dimensions, client) -> CalibrationRound
apply_calibration_choice(profile, round_id, choice) -> StyleProfile
import_existing_style(mode, slug) -> ImportResult
compile_style_family(family_slug, modes, client, progress_callback) -> GenerationManifest
preview_publish_diff(family_slug, modes) -> PublishPreview
publish_style_family(family_slug, modes) -> PublishResult
save_agent_override(family_slug, mode, agent, effective_yaml) -> OverrideResult
```

Các kiểu dữ liệu tối thiểu:

- `StyleProfile`;
- `EvidenceClaim`;
- `InterviewQuestion`;
- `CalibrationRound`;
- `ValidationIssue`;
- `ValidationReport`;
- `GenerationManifest`;
- `PublishPreview`;
- `PublishResult`.

API phải trả dữ liệu có cấu trúc, không dùng tuple boolean/message cho workflow mới.

---

## 9. Tích hợp Local UI

Style Studio có hai lựa chọn:

1. **Quick Clone** — giữ nguyên tính năng hiện có.
2. **Guided Voice Lab** — luồng tạo style có hướng dẫn.

Guided Voice Lab gồm năm màn hình:

1. Samples
2. Evidence Review
3. Guided Interview
4. A/B Calibration
5. Review & Publish

Style Gallery hiển thị trạng thái theo từng mode:

- `not_generated`;
- `draft`;
- `valid`;
- `conflict`;
- `published`;
- `outdated`.

Trang chỉnh style có ba mức:

- **Cơ bản:** các thuộc tính chính và ví dụ.
- **Chi tiết:** toàn bộ Voice DNA và Mode Profile.
- **Nâng cao:** generated YAML, effective YAML và overrides.

Style chưa có Profile được hiển thị nút:

> Tạo Style Profile từ YAML hiện tại

Quá trình import chỉ tạo bản nháp profile; không regenerate hoặc publish tự động.

---

## 10. An toàn dữ liệu và xử lý lỗi

- Mọi thao tác publish phải dùng thư mục staging.
- Validate toàn bộ mode trước khi thay thế runtime folder.
- Tạo backup trước khi publish.
- Dùng atomic replace khi cùng filesystem.
- Nếu bất kỳ bước nào thất bại, rollback toàn bộ mode tương ứng.
- Không để trạng thái một phần: ví dụ 4/7 agents mới và 3/7 agents cũ.
- Không xóa generated base hoặc overrides khi publish thất bại.
- Không ghi log toàn văn bài mẫu vào run log.
- Không gửi bài mẫu tới provider nếu người dùng chưa xác nhận thao tác phân tích.
- UI phải cảnh báo rõ việc phân tích và A/B calibration có thể dùng API/local model quota.

---

## 11. Kế hoạch triển khai

### Phase 1: Profile Foundation

- Thêm schema và storage cho Style Family.
- Thêm CRUD cho Style Profile và Evidence.
- Thêm import từ style hiện có.
- Thêm validation và versioning.

### Phase 2: Discovery Workflow

- Thêm upload/paste samples.
- Thêm AI sample analysis.
- Thêm Evidence Review.
- Thêm Guided Interview.

### Phase 3: Calibration và Compiler

- Thêm A/B Calibration.
- Thêm compiler theo mode/agent.
- Thêm retry, checkpoint và generation manifest.
- Thêm invariant validation.

### Phase 4: Overrides và Publish

- Thêm patch operations.
- Thêm conflict detection.
- Thêm semantic/YAML diff.
- Thêm staging, backup, atomic publish và rollback.

### Phase 5: UI Integration và Documentation

- Tích hợp wizard vào Style Studio.
- Nâng cấp Gallery và Advanced Editor.
- Cập nhật README, kiến trúc, changelog và hướng dẫn sử dụng.
- Bổ sung dependency manifest và lệnh khởi chạy.

---

## 12. Kế hoạch kiểm thử

### 12.1. Unit tests

- Validate schema và profile version.
- Slug và mode validation.
- Evidence accept/edit/reject.
- Interview chỉ hỏi dimensions còn thiếu.
- A/B choice cập nhật đúng thuộc tính.
- Compiler sinh đúng 7 Deep và 6 Moment files.
- Agent ID, filename và output contract không thay đổi.
- Self-correction retry dừng đúng giới hạn.
- Override còn hiệu lực sau regeneration.
- Add/replace/remove hoạt động đúng.
- Conflict được phát hiện khi path biến mất hoặc đổi kiểu.
- Import style cũ không làm thay đổi runtime YAML.
- Protected slug không thể đổi.

### 12.2. Integration tests

Kịch bản chuẩn:

1. Tạo một family từ ba bài mẫu.
2. Duyệt evidence.
3. Trả lời interview.
4. Hoàn thành một vòng A/B.
5. Compile cả hai mode.
6. Publish.
7. Xác nhận `validate_style_contract` vượt qua.
8. Chạy dry-run Deep và Moment.
9. Chỉnh một agent override.
10. Thay đổi profile và regenerate.
11. Xác nhận override vẫn được giữ.

### 12.3. UI tests

Dùng Streamlit AppTest kiểm tra:

- điều hướng wizard;
- upload/paste samples;
- trạng thái evidence;
- profile editor;
- progress và retry display;
- diff confirmation;
- conflict resolution;
- publish success/failure;
- resume draft sau khi Streamlit rerun.

### 12.4. Regression

Chạy toàn bộ test hiện tại:

```powershell
python -m unittest discover -s tests
```

Quick Clone, CRUD style, CLI, learning loop và dry-run hiện tại phải tiếp tục hoạt động.

---

## 13. Tiêu chí nghiệm thu

V1 được nghiệm thu khi:

1. Người dùng có thể tạo Style Family từ bài viết của chính mình mà không mở YAML.
2. Mọi nhận định AI đều có evidence, confidence và bước duyệt.
3. Một Voice DNA có thể tạo hai biến thể Deep/Moment khác nhau.
4. Cả hai mode sinh đủ file và vượt qua flow contract.
5. Không có thay đổi nào được publish khi chưa có xác nhận.
6. Chỉnh Profile rồi regenerate không làm mất Agent Overrides.
7. Publish lỗi không để lại runtime style ở trạng thái một phần.
8. Existing styles vẫn hoạt động và có thể được import vào Voice Lab.
9. YAML Editor nâng cao vẫn dùng được.
10. Người dùng có thể hiểu style đang làm gì và agent nào bị ảnh hưởng bằng giao diện ngôn ngữ tự nhiên.

---

## 14. Roadmap sau V1

- Học có kiểm duyệt từ chênh lệch giữa AI draft và production blog.
- Đề xuất cập nhật Voice DNA hoặc Mode Profile sau nhiều lần chỉnh sửa.
- Đo style drift theo thời gian.
- So sánh hiệu quả giữa các phiên bản profile.
- Cho phép rollback profile/published style theo version.
- Real-run calibration với một workflow rút gọn và kiểm soát quota.

---

## 15. Giả định

- Hệ thống chạy local cho một người dùng.
- Người dùng chỉ đưa bài viết của chính mình làm dữ liệu phân tích.
- Style Profile là nguồn chuẩn; YAML là output triển khai.
- Một Style Family dùng chung Voice DNA nhưng có hai Mode Profile.
- Mọi thay đổi generated YAML đều phải được duyệt trước khi publish.
- Continuous learning được trì hoãn sang giai đoạn sau.
- Client gọi AI tái sử dụng cơ chế OpenAI/Antigravity hiện có.

---



---

## 16. Phụ lục 1: Kế hoạch triển khai chi tiết (Gemini 3.1 Pro - Cập nhật sau Grill-me)

Kế hoạch này dựa trên tài liệu đề xuất của GPT-5.6 Sol và các quyết định đã được chốt qua phiên `/grill-me`. Mục tiêu là xây dựng luồng định hình phong cách bằng ngôn ngữ tự nhiên (Voice DNA, Mode Profile) và tự động sinh YAML cấu hình thay vì bắt người dùng sửa file trực tiếp.

### 16.1. Cảnh báo & Lưu ý hệ thống

- **Semantic Merge Cost:** Việc dùng AI để merge Overrides thông minh (Semantic Merge) sẽ an toàn hơn JSON Patch, nhưng đồng nghĩa tốn thêm API Call mỗi khi Compile lại YAML. Bạn vui lòng xác nhận mức đánh đổi Quota này là chấp nhận được để có UX tốt nhất.
- **Incremental Compilation Logic:** Nếu Voice DNA thay đổi (VD: Giọng kể), hầu hết các Agent đều bị ảnh hưởng và phải sinh lại toàn bộ. Tính năng Incremental Compilation sẽ chỉ thực sự phát huy tác dụng tiết kiệm Quota khi người dùng thay đổi Mode Profile đặc thù (VD: chỉ sửa `sensory_density` của Moment Mode sẽ chỉ sinh lại một số agent của Moment).

### 16.2. Thay đổi Cấu trúc Backend: Khởi tạo package `engine/voice_lab/`

Tạo package mới để chứa toàn bộ logic xử lý phong cách (tránh làm phình `style_manager.py`).

- **`models.py`:** Định nghĩa các Pydantic/Dataclass: `StyleProfile`, `VoiceDNA`, `EvidenceClaim`, `InterviewQuestion`, v.v.
- **`analyzer.py`:** Logic phân tích bài mẫu (Samples) để chiết xuất Evidence và dự thảo Voice DNA.
- **`interview.py`:** Cơ chế Guided Interview và A/B Calibration để điền các thuộc tính còn thiếu (Low Confidence) trong Profile.
- **`compiler.py`:** Sinh cấu hình YAML từ Profile. Tích hợp tính năng **Incremental Compilation**: chỉ sinh lại các file bị ảnh hưởng bởi những chiều (dimension) vừa thay đổi.
- **`overrides.py`:** Quản lý Agent Overrides. Dùng **Semantic Merge** qua LLM để áp các overrides cũ vào file YAML vừa được sinh mới, chống gãy vỡ (brittle) so với JSON Patch.

### 16.3. UI Integration & Data Storage

- **Tích hợp UI (`app.py`):** Mở rộng `ui/app.py` để hỗ trợ Wizard gồm 5 bước của Guided Voice Lab. Tích hợp Guided Voice Lab vào Tab 2 (Style Studio). Mở rộng Tab 3 (YAML Editor) để hỗ trợ 3 lớp hiển thị: Generated Base, Overrides, và Effective YAML.
- **Lưu trữ (`style_profiles/`):** Cấu trúc lưu trữ tách biệt hoàn toàn nguồn chuẩn (Profiles) và Output chạy runtime (Skills). Thư mục lưu trữ nguồn chuẩn gồm: `style_profile.yaml`, `evidence.yaml`, thư mục con `samples/` (bỏ qua bởi git), và `overrides/`. Output publish cuối cùng mới được atomic replace sang `skills/`.

## 17. Phụ lục 2: Phản biện và Góp ý (Claude Opus 4.6 & Gemini 3.1 Pro)

### 17.1. Những điểm đồng ý là hợp lý, hiệu quả

**GPT-5.6 Sol:**
- Tách Voice DNA (dùng chung) vs Mode Profile (riêng) — đúng bản chất: giọng viết là hằng số, biểu hiện theo mode là biến số.
- Style Profile là nguồn chuẩn, YAML là output — đảo ngược đúng chiều kiểm soát, người dùng không cần hiểu YAML.
- Bắt buộc duyệt trước khi publish + atomic staging + rollback — nhất quán với ADR-2 đã chốt.
- Evidence trích xuất phải có `confidence`, `evidence_ids`, `status` — tạo audit trail, không phải black-box.
- Invariant contract (agent ID, filename, output, handoff) không được compiler thay đổi — bảo vệ runtime stability.
- Giới hạn interview 6-8 câu/vòng — tránh UX fatigue.

**Gemini 3.1 Pro:**
- Package `engine/voice_lab/` tách module rõ ràng — đúng hướng Clean Architecture.
- Incremental Compilation — tiết kiệm quota thực tế khi chỉ sửa Mode Profile.
- Semantic Merge thay JSON Patch — giải quyết đúng điểm giòn vỡ index-based patching.

### 17.2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu

**GPT-5.6 Sol:**
- **Thiếu dependency map giữa Profile dimensions → Agents.** Kế hoạch nói "incremental" nhưng không định nghĩa bảng ánh xạ chiều nào ảnh hưởng agent nào. Không có bảng này thì compiler không biết sinh lại file nào → buộc phải sinh lại toàn bộ, Incremental Compilation vô nghĩa.
- **Override format dùng JSON Patch (`/style_rules/1`) trên YAML** — sai paradigm. YAML list không có key ổn định; index thay đổi sau mỗi lần regenerate. Kế hoạch thừa nhận rủi ro nhưng giải pháp chỉ là "tạo conflict" → đẩy gánh nặng cho user.
- **Thiếu versioning strategy cho `style_profile.yaml`.** Chỉ có `profile_version` tăng dần, không có diff giữa các version → không rollback profile được, mâu thuẫn với roadmap sau V1 ("rollback profile theo version").
- **A/B Calibration sinh 2 bản văn khác nhau** nhưng không nói rõ dùng prompt nào, input nào, độ dài bao nhiêu. Nếu sinh đoạn văn quá ngắn hoặc quá giống nhau → user không phân biệt được → dữ liệu calibration vô giá trị.
- **`samples/` trong `.gitignore`** nhưng không có cơ chế backup. Mất máy = mất toàn bộ evidence gốc. Cần ít nhất export/import.

**Gemini 3.1 Pro:**
- **Kế hoạch quá sơ lược.** Chỉ liệt kê tên file mới, không mô tả schema, không có API signature, không có data contract giữa các module. So với bản GPT-5.6 Sol có 13 API signatures rõ ràng → Gemini thiếu chiều sâu kỹ thuật đáng kể.
- **Không đề cập Evidence Review UI.** Đây là bước quan trọng nhất (user duyệt từng nhận định AI), nhưng kế hoạch chỉ ghi "Wizard 5 bước" mà không mô tả UI state machine hay interaction flow.
- **Semantic Merge tốn thêm 1 API call/agent mỗi lần compile** nhưng không có fallback khi LLM merge sai (hallucinate thêm field, xóa nhầm rule). Cần validation sau merge + diff cho user duyệt.
- **Thiếu hoàn toàn Bước 6 (Profile Review)** — bước tổng hợp toàn bộ Voice DNA + 2 Mode Profile + confidence map trước khi compile. Không có bước này, user bấm Generate mà không biết hệ thống hiểu mình thế nào.
- **Không đề cập import style cũ** (`import_existing_style`). Các style `reflective`, `provocative` hiện tại không có profile → cần cơ chế reverse-engineer YAML → Profile để tích hợp vào Voice Lab mà không phá vỡ hệ thống đang chạy.

### 17.3. Đề xuất cải tiến

| # | Đề xuất | Ảnh hưởng |
|:--|:--------|:----------|
| 1 | **Tạo `dimension_agent_map.yaml`** — bảng ánh xạ tường minh: mỗi dimension trong Voice DNA/Mode Profile ảnh hưởng agent nào. Compiler đọc bảng này để quyết định sinh lại file nào (Incremental thực sự). | Compiler, Quota |
| 2 | **Bỏ JSON Patch, dùng Semantic Merge + Post-Merge Validation.** Sau khi LLM merge, bắt buộc chạy `validate_style_yaml` + diff so với bản trước. Nếu validator fail hoặc diff bất thường → chặn và hiển thị cho user. | Overrides, Safety |
| 3 | **Thêm `profile_history/` lưu snapshot** mỗi version của `style_profile.yaml` (dạng `v001.yaml`, `v002.yaml`). Chi phí storage không đáng kể, nhưng cho phép rollback profile ngay trong V1. | Versioning |
| 4 | **Mô tả chi tiết A/B Calibration prompt template**: quy định rõ input là đoạn mở bài 150-200 từ, chỉ thay đổi đúng 1-2 dimension đang test, đính kèm label rõ ràng "Bản A nhấn mạnh X, Bản B nhấn mạnh Y". | UX, Data Quality |
| 5 | **Bổ sung `import_existing_style(mode, slug)`** ngay Phase 1 để system styles hiện tại (`reflective`, `provocative`) có thể được dùng làm baseline trong Voice Lab mà không cần user tạo lại từ đầu. | Migration, UX |
| 6 | **Gemini cần bổ sung Implementation Plan** với: (a) Data contract/schema cho `StyleProfile`, `EvidenceClaim`; (b) UI state machine cho wizard 5 bước; (c) Error handling matrix cho từng bước (phân tích thất bại, compile thất bại, merge conflict). | Plan Completeness |

---

## 18. Phụ lục 3: Phản biện độc lập

### 1. Những điểm bạn đồng ý là hợp lý, hiệu quả của Gemini 3.1 Pro và của Claude Opus 4.6 

**Gemini 3.1 Pro**

- Tách `engine/voice_lab/` đúng hướng; tránh làm phình `style_manager.py`.
- Incremental Compilation có giá trị khi thay đổi chỉ ảnh hưởng một mode hoặc nhóm agent.
- Tách Profile khỏi runtime Skills và giữ publish atomic là hợp lý.

**Claude Opus 4.6**

- Chỉ đúng các thiếu hụt quan trọng: impact map, profile history, Evidence Review, Profile Review, import style cũ và validation sau merge.
- Yêu cầu đặc tả A/B, schema, state machine và error matrix là cần thiết để kế hoạch có thể triển khai.

### 2. Những điểm bạn thấy chưa hiệu quả, chưa hợp lý, còn thiếu của Gemini 3.1 Pro và của Claude Opus 4.6

**Gemini 3.1 Pro**

- Semantic Merge bằng LLM không mặc nhiên an toàn hơn JSON Patch: tốn quota, không xác định và có thể tự ý sửa/xóa rule.
- Incremental Compilation chưa có impact model, cache key, invalidation rule hoặc kiểm thử chống bỏ sót agent.
- Thiếu schema, API contract, wizard state persistence, import legacy và cơ chế resume sau Streamlit rerun.

**Claude Opus 4.6**

- Đề xuất bỏ hoàn toàn JSON Patch để dùng Semantic Merge vẫn đặt LLM vào đường ghi dữ liệu quan trọng.
- `dimension_agent_map.yaml` tĩnh dễ lệch khỏi schema/compiler nếu không version hóa và kiểm thử.
- A/B có nhãn “A nhấn mạnh X/B nhấn mạnh Y” gây thiên kiến lựa chọn; phải blind và randomize.
- Snapshot version chưa đủ: thiếu manifest, migration schema và atomic rollback.
- Import YAML cũ không tạo được evidence thật; không nên coi profile suy diễn là đã được xác nhận.

**Cả hai**

- Chưa khóa transaction khi publish đồng thời hai mode, xử lý slug collision, job idempotency/concurrency, quyền riêng tư/export mẫu và tiêu chí đo độ trung thành phong cách.

### 3. Đề xuất

1. Dùng merge xác định theo schema với stable IDs và three-way diff; LLM chỉ đề xuất xử lý conflict, người dùng duyệt.
2. Version hóa impact map cùng Profile schema; Voice DNA mặc định ảnh hưởng toàn mode, dimension riêng khai báo agent phụ thuộc và có contract test.
3. A/B blind, thứ tự ngẫu nhiên, cùng input 150–200 từ, mỗi vòng chỉ thay 1–2 dimensions; chỉ công bố khác biệt sau khi chọn.
4. Lưu immutable profile snapshots + manifest `current_version`; có schema migration và export/import bundle gồm profile, evidence, overrides, tùy chọn samples.
5. Persist wizard/job state; compile có checkpoint, resume, idempotency key và publish cả hai mode theo transaction all-or-nothing.
6. Import style cũ thành draft với provenance `inferred_from_yaml`, confidence thấp, không evidence và không tự publish.
7. Bổ sung fidelity tests: generated YAML phải khác baseline đúng dimensions, không đổi invariants và tạo output đạt rubric Voice DNA/Mode Profile.

---

## 19. Phản biện lần 2 (Claude Opus 4.6 phản hồi GPT-5.6 Sol — Mục 18)

### 1. Những điểm đồng ý là hợp lý, hiệu quả của GPT-5.6

- **Merge xác định theo schema + stable IDs + three-way diff** — đúng trọng tâm. JSON Patch index-based giòn, LLM merge không xác định; three-way diff trên stable IDs là giải pháp cân bằng tốt nhất giữa tính xác định và tính linh hoạt. LLM chỉ xử lý conflict, user duyệt — đồng ý hoàn toàn.
- **A/B blind + randomize** — chỉ ra đúng lỗ hổng thiên kiến trong đề xuất của tôi. Nếu gắn nhãn "A nhấn mạnh X", user chọn theo nhãn chứ không chọn theo cảm nhận thực tế. Blind là bắt buộc.
- **Import style cũ thành draft với `provenance: inferred_from_yaml`, confidence thấp** — thực tế hơn đề xuất ban đầu của tôi. Reverse-engineer YAML → Profile không bao giờ cho evidence thật; gắn `inferred` + chặn auto-publish là đúng.
- **Persist wizard/job state + checkpoint + resume + idempotency key** — đúng điểm mù của cả hai bên trước đó. Streamlit rerun mất state là rủi ro thực tế, cần giải quyết ngay Phase 1.
- **Version hóa impact map cùng Profile schema + contract test** — giải quyết đúng nhược điểm `dimension_agent_map.yaml` tĩnh mà GPT-5.6 chỉ ra.
- **Publish transaction all-or-nothing cho cả hai mode** — tôi đã bỏ sót hoàn toàn kịch bản publish Deep thành công nhưng Moment fail, dẫn tới inconsistency. Đồng ý cần atomic cross-mode.

### 2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu của GPT-5.6

- **Three-way diff yêu cầu stable IDs trên mọi list item YAML.** GPT-5.6 nói "stable IDs" nhưng không giải thích cách gán. YAML hiện tại dùng list thuần (`style_rules: [rule1, rule2]`), không có key. Chuyển toàn bộ list sang keyed-map (`style_rules: {sr-001: rule1, sr-002: rule2}`) sẽ phá vỡ backward compatibility với tất cả runtime code đang đọc list. Cần migration plan cụ thể hoặc chấp nhận list vẫn dùng content-based matching (so sánh nội dung) thay vì ID-based.
- **"Voice DNA mặc định ảnh hưởng toàn mode"** — đúng về nguyên tắc nhưng quá bảo thủ. Nếu user chỉ sửa `humor` trong Voice DNA, sinh lại toàn bộ 13 agent là lãng phí. Cần ít nhất 2 tầng: (a) dimension ảnh hưởng rộng (VD: `giọng_kể`, `nhịp_điệu`) → sinh lại toàn bộ; (b) dimension ảnh hưởng hẹp (VD: `humor`, `emoji`) → chỉ sinh lại agent có liên quan. Impact map vẫn cần, nhưng phải chia theo mức ảnh hưởng.
- **Fidelity tests "generated YAML phải đạt rubric"** — khái niệm đúng nhưng chưa khả thi trong V1. Đánh giá "output đạt rubric Voice DNA" đòi hỏi chạy full workflow + human evaluation hoặc LLM-as-judge. Chi phí quá cao cho mỗi lần compile. Nên giới hạn V1 ở structural fidelity (invariant check + diff coverage) và trì hoãn semantic fidelity sang V2.
- **Export/import bundle "gồm profile, evidence, overrides, tùy chọn samples"** — đúng hướng nhưng chưa nói format. Cần chốt: ZIP archive đơn giản hay structured format (VD: tarball với manifest.json)? Cần quy ước rõ để tránh mỗi phase tự chế format riêng.
- **Thiếu quota budget estimation.** Cả hai bên đều nói "tốn quota" nhưng không ai ước lượng. Cần con số cụ thể: phân tích 3 bài ~3K tokens/bài → ~15K input tokens; sinh 13 agents ~2K tokens/agent → ~26K output tokens; A/B 3 vòng × 2 bản × 200 từ → ~4K tokens. Tổng ước lượng ~50-60K tokens/lần tạo style mới. User cần thấy con số này trước khi bấm Start.

### 3. Đề xuất

| # | Đề xuất | Lý do |
|:--|:--------|:------|
| 1 | **List items dùng content-based matching** cho three-way diff thay vì gán stable IDs. So sánh bằng nội dung chuỗi (fuzzy match nếu cần) để tránh phá vỡ backward compatibility của YAML schema hiện tại. Chỉ chuyển sang keyed-map nếu V2 yêu cầu. | Backward compat |
| 2 | **Impact map 2 tầng**: `global_dimensions` (sinh lại toàn bộ mode) và `scoped_dimensions` (sinh lại danh sách agent cụ thể). Contract test kiểm tra mọi dimension đều có mapping. | Quota, Precision |
| 3 | **Trì hoãn semantic fidelity test sang V2.** V1 chỉ kiểm: (a) invariant contract nguyên vẹn; (b) diff coverage đúng dimensions đã thay đổi; (c) YAML parse + validate pass. | Scope, Feasibility |
| 4 | **Export/import dùng ZIP** với `manifest.json` (version, slug, modes, file list). Samples là optional flag khi export. | Standardization |
| 5 | **Hiển thị Quota Estimate trên UI** trước khi user bấm "Phân tích" hoặc "Generate". Ước lượng dựa trên số bài mẫu × token trung bình + số agent × token trung bình. | UX, Transparency |
| 6 | **Chốt Merge Strategy cuối cùng:** Three-way diff + content-based matching cho list. LLM chỉ được gọi khi phát hiện conflict không tự giải được. Post-merge luôn chạy `validate_style_yaml`. User duyệt diff trước publish. | Consensus |

---

## 20. Phản biện lần 2 độc lập

### 1. Những điểm bạn đồng ý là hợp lý, hiệu quả của Claude Opus 4.6  

- Chỉ đúng khoảng trống về stable IDs, phạm vi ảnh hưởng dimension và chi phí quota.
- Impact map phân biệt ảnh hưởng rộng/hẹp hợp lý hơn regenerate toàn bộ.
- ZIP + manifest, post-merge validation và user duyệt diff là cần thiết.
- Không nên chạy full workflow semantic evaluation sau mỗi compile.

### 2. Những điểm bạn thấy chưa hiệu quả, chưa hợp lý, còn thiếu của Claude Opus 4.6 

- Content/fuzzy matching không an toàn với phần tử trùng, gần nghĩa hoặc bị LLM diễn đạt lại; có thể áp override nhầm mà không báo conflict.
- Stable IDs không bắt buộc đổi runtime list thành keyed-map: có thể tồn tại trong canonical IR/sidecar rồi render lại list cũ.
- Impact map hai tầng vẫn thô; dimensions có thể ảnh hưởng gián tiếp qua nhiều agent.
- Hoãn toàn bộ semantic fidelity sang V2 khiến V1 chỉ chứng minh YAML hợp lệ, không chứng minh style phản ánh Profile.
- Ước lượng 50–60K tokens chỉ là giả định; phụ thuộc độ dài mẫu, model, prompt, retry và context thực tế.
- ZIP import còn thiếu chống path traversal, checksum, giới hạn kích thước và schema migration.
- Chưa đề cập prompt injection trong bài mẫu và transaction riêng khi người dùng chỉ publish một mode.

### 3. Đề xuất

1. Dùng canonical IR `{id, text}` cho list; runtime vẫn render list chuỗi tương thích cũ. Override tham chiếu `id`, không fuzzy match.
2. Thay map hai tầng bằng dependency graph có `affects`, transitive invalidation và contract test bao phủ mọi dimension.
3. V1 giữ semantic smoke test rẻ: kiểm tra Profile→prompt/YAML coverage và vài calibration probes; full workflow/LLM judge là tùy chọn.
4. Chuẩn hóa `.voice-style.zip`: `manifest.json`, schema version, SHA-256, path/size allowlist và optional samples.
5. Tính token/cost động theo provider, model và prompt thực; hiển thị khoảng min–max từng phase và đối soát usage sau chạy.
6. Xử lý samples như dữ liệu không tin cậy; cô lập instruction, dùng structured output và validate.
7. “Publish cả hai” dùng all-or-nothing; publish một mode dùng transaction độc lập có trạng thái version rõ ràng.

---

## 21. Phản biện lần 3 (Claude Opus 4.6 phản hồi GPT-5.6 Sol — Mục 20)

### 1. Những điểm đồng ý là hợp lý, hiệu quả của GPT-5.6

- **Canonical IR `{id, text}` + render list cũ** — giải quyết triệt để tranh luận stable IDs vs backward compat. IR là lớp nội bộ, runtime vẫn nhận list thuần. Override tham chiếu `id` thay vì fuzzy match — an toàn hơn đề xuất content-based của tôi. Rút lại đề xuất fuzzy matching.
- **Dependency graph thay impact map 2 tầng** — đúng, graph với `affects` + transitive invalidation chính xác hơn phân loại cứng global/scoped. Một dimension có thể ảnh hưởng gián tiếp (VD: `nhịp_điệu` → `writing_agent` → `editor_agent` phải điều chỉnh theo). Map 2 tầng không bắt được chuỗi phụ thuộc này.
- **Semantic smoke test rẻ trong V1** — điểm cân bằng tốt giữa "hoãn toàn bộ" (đề xuất cũ của tôi) và "full rubric evaluation" (quá đắt). Kiểm tra Profile→prompt coverage + vài calibration probes đủ để phát hiện compiler bỏ sót dimension mà không cần chạy workflow.
- **`.voice-style.zip` chuẩn hóa với SHA-256 + path/size allowlist** — bổ sung đúng các lỗ hổng bảo mật tôi bỏ sót (path traversal, file quá lớn).
- **Token/cost động theo provider + hiển thị min–max + đối soát usage** — chính xác hơn ước lượng tĩnh 50-60K. Model khác nhau, prompt khác nhau, retry khác nhau → con số tĩnh vô nghĩa.
- **Samples là dữ liệu không tin cậy → cô lập instruction + structured output** — đúng lỗ hổng nghiêm trọng mà cả 3 bên trước đó đều bỏ qua. Bài mẫu có thể chứa prompt injection ("Ignore previous instructions..."). Phải xử lý như untrusted input.
- **Publish một mode dùng transaction độc lập** — thực tế hơn all-or-nothing cứng. User có thể chỉ muốn publish Deep trước, Moment sau.

### 2. Những điểm chưa hiệu quả, chưa hợp lý, còn thiếu của GPT-5.6

- **Dependency graph + transitive invalidation phức tạp hóa V1 không cần thiết.** Với 12 dimensions × 13 agents, graph nhỏ đủ để hardcode. Xây hệ thống graph engine với transitive traversal cho V1 là over-engineering. Đề xuất: V1 dùng **adjacency matrix tĩnh** (dict of sets), contract test kiểm tra coverage. V2 mới nâng cấp thành graph engine nếu schema phức tạp hơn.
- **Canonical IR thêm lớp trung gian** giữa Profile → Generated YAML → Runtime YAML. Tổng cộng hệ thống sẽ có 4 lớp biểu diễn: Profile → IR → Generated YAML → Effective YAML (sau override). Debug khi có lỗi sẽ phải trace qua 4 lớp. Cần tooling hiển thị rõ "giá trị này đến từ lớp nào" ngay trong UI, không chỉ trong log.
- **Smoke test "calibration probes"** chưa định nghĩa rõ. Probe là gì? Sinh 1 đoạn văn ngắn từ agent rồi kiểm tra keyword? Hay so sánh embedding? Cần spec cụ thể để triển khai được, không nên để mơ hồ.

### 3. Đề xuất

| # | Đề xuất | Lý do |
|:--|:--------|:------|
| 1 | **V1 dùng adjacency matrix tĩnh** (`DIMENSION_AGENTS: dict[str, set[str]]`) thay vì graph engine. Contract test đảm bảo mọi dimension có mapping và mọi agent được ít nhất 1 dimension reference. Đủ cho 12×13. | Simplicity, V1 scope |
| 2 | **UI "Layer Inspector"** trong Tab Editor Nâng cao: dropdown chọn xem Profile → IR → Generated → Effective. Mỗi field gắn badge nguồn gốc (`from_profile`, `from_override`, `from_default`). | Debuggability |
| 3 | **Định nghĩa smoke test cụ thể:** Với mỗi agent YAML vừa sinh, kiểm tra (a) mọi dimension đã thay đổi xuất hiện ít nhất 1 lần trong prompt/rules/style_rules dưới dạng keyword hoặc synonym; (b) invariant fields không đổi so với base. Không cần gọi LLM, chỉ cần text search. | Testability, Zero-cost |
| 4 | **Chốt consensus 3 bên** — Sau 3 vòng phản biện, các điểm đã hội tụ đủ để viết Final Spec. Đề xuất tạo `docs/2026-07-26-guided-style-voice-lab-plan-final.md` tổng hợp tất cả quyết định đã chốt từ Mục 16→21. | Closure |
