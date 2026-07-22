# Kế Hoạch Nâng Cấp `mindful_writing_os` Thành Hệ Hai Writing Modes
Ngày: 2026-07-22

## 1. Mục tiêu

Nâng cấp `mindful_writing_os` từ một workflow viết phản tư đơn sang một hệ hai chế độ:

- `deep_blog_mode`: viết dài, phản tư, chuyển hóa, phù hợp các bài trải nghiệm kiểu BREAK.
- `moment_blog_mode`: viết ngắn, hiện tại, trực giác, giữ tín hiệu của khoảnh khắc.

Mục tiêu của nhánh mới là:

- giữ bài dưới 600 từ;
- ưu tiên cảm giác, cảnh vật, tín hiệu;
- giảm triết lý sâu;
- giữ được giọng viết giàu cảm nhận nhưng không bị kéo sang bài phản tư dài.

## 2. Đánh giá kiến trúc hiện tại

Cấu trúc hiện tại của `mindful_writing_os` đã rất phù hợp để mở rộng vì có các nền tảng tốt sau:

- mỗi agent giữ một câu hỏi rõ ràng;
- artifact và handoff đã tách;
- context policy đã được khai báo theo flow;
- learning loop dựa trên bản cuối do người viết chọn;
- hệ thống đã quen với tư duy “nhà xuất bản mini”.

Điểm cần bổ sung là:

- thêm mode router;
- tách flow theo mode;
- tạo cụm agent riêng cho `moment_blog_mode`;
- tách learning theo mode;
- ngăn chặn việc moment mode bị kéo sang chiều sâu kiểu deep blog.

## 3. Kiến trúc đích

### 3.1 Hai writing modes

```yaml
mindful_writing_os:
  modes:
    deep_blog_mode:
      purpose: "Viết để hiểu và chuyển hóa trải nghiệm"
      target_length: "1000-1500 words"
      depth: "high"
      philosophy_density: "medium-high"

    moment_blog_mode:
      purpose: "Viết để nghe một khoảnh khắc đang sống"
      target_length: "300-600 words"
      depth: "light"
      philosophy_density: "low"
```

### 3.2 Nguyên tắc chia mode

`deep_blog_mode` dùng khi:

- trải nghiệm đã qua;
- cần hành trình nội tâm;
- có chuyển hóa rõ;
- cần cầu nối mạnh với người đọc.

`moment_blog_mode` dùng khi:

- khoảnh khắc còn tươi;
- cảm giác hiện tại rõ;
- có tín hiệu trực giác;
- không muốn phân tích sâu.

## 4. Shared core và mode-specific core

### 4.1 Shared core

Hai mode dùng chung một số phần hạ tầng:

- `source_reader`
- `voice_keeper`
- `breath_editor`
- `publisher`
- `learning_keeper`

Những phần này không quyết định mode, mà giữ chất lượng và tính nhất quán.

### 4.2 Deep core

Dành cho `deep_blog_mode`:

- `story_architect`
- `reflection_engine`
- `writing_agent`
- `reader_experience`
- `editor_agent`
- `coach_agent`
- `future_self`

### 4.3 Moment core

Dành cho `moment_blog_mode`:

- `sensory_capture`
- `inner_weather`
- `cosmic_signal_reader`
- `moment_writer`
- `breath_editor`
- `gentle_witness`

## 5. Luồng triển khai đề xuất

### 5.1 Deep blog mode

```text
source_reader
-> story_architect
-> reflection_engine
-> writing_agent
-> reader_experience
-> editor_agent
-> coach_agent
-> future_self
-> human_writer
```

### 5.2 Moment blog mode

```text
source_reader
-> sensory_capture
-> inner_weather
-> cosmic_signal_reader
-> moment_writer
-> breath_editor
-> gentle_witness
-> human_writer
```

## 6. Nguyên tắc thiết kế moment_blog_mode

`moment_blog_mode` phải giữ các đặc tính sau:

- ngắn;
- trực tiếp;
- hiện tại;
- cảm giác hơn lý luận;
- tín hiệu hơn kết luận;
- có thể đọc như một mảnh nhật ký có ánh sáng;
- không ép bài học;
- không coaching;
- không triết lý hóa mọi chi tiết.

## 7. Kế hoạch chuyển đổi hệ thống

### Bước 1: Định danh mode hiện tại là deep_blog_mode

Không thay logic cũ, chỉ đổi tên ngữ nghĩa.

### Bước 2: Thêm moment_blog_mode với flow riêng

Khởi đầu với 5 đến 6 agent cốt lõi:

- `sensory_capture`
- `inner_weather`
- `cosmic_signal_reader`
- `moment_writer`
- `breath_editor`
- `gentle_witness`

### Bước 3: Thêm mode router

CLI và engine cần phân biệt rõ:

- `--mode deep`
- `--mode moment`

### Bước 4: Tách output và learning theo mode

Learning phải học riêng:

- `deep_blog_patterns.md`
- `moment_blog_patterns.md`
- `shared_voice_patterns.md`

### Bước 5: Kiểm chứng bằng cùng một input

Dùng cùng một nguồn vào để kiểm tra:

- deep mode tạo bài phản tư dài;
- moment mode tạo bài ngắn, trong, trực giác.

## 8. Rủi ro cần tránh

- moment mode bị kéo thành deep mode mini;
- agent “cosmic” tạo ra thông điệp quá mạnh dù dữ kiện chưa đủ;
- learning của hai mode bị trộn;
- breath editor can thiệp quá sâu, làm mất tính khoảnh khắc;
- dùng lại `coach_agent` trong moment mode khiến bài chuyển sang phân tích.

## 9. Tiêu chí chấp nhận

Hệ mới đạt yêu cầu nếu:

- một input có thể chạy đúng mode;
- moment blog dưới 600 từ;
- moment blog đọc lên có cảm giác hiện tại;
- không cần giải thích quá mức;
- learning phân biệt được hai mode;
- người viết vẫn giữ quyền quyết định cuối cùng.

---

# Nháp skill YAML cho các agent của `moment_blog_mode`

## 1. `sensory_capture.yaml`

```yaml
skill:
  name: sensory_capture
  mode: moment_blog_mode
  purpose: "Ghi lại một khoảnh khắc hiện tại bằng giác quan, không diễn giải sâu."
  core_question: "Khoảnh khắc này đang hiện ra qua giác quan như thế nào?"
  input:
    required:
      - raw_notes
    optional:
      - author_phrases
      - time_place_context

  tasks:
    - identify_central_moment
    - capture_visible_scene
    - capture_sound_smell_temperature
    - capture_bodily_sensation
    - preserve_authentic_phrasing
    - separate_observation_from_interpretation

  do_not:
    - infer_hidden_meaning
    - explain_transformation
    - add_life_advice
    - beautify_for_effect
    - invent_missing_details

  output:
    artifact: sensory_notes.md
    sections:
      - central_moment
      - visible_scene
      - sensory_details
      - bodily_sensations
      - verbatim_fragments
      - uncertain_details
    handoff:
      required: true
      target_words: "50-90"
      focus: "What was seen, felt, and noticed."

  style_rules:
    - keep_language_concrete
    - prefer_short_sentences
    - preserve_uncertainty
    - do_not_name_philosophy
```

## 2. `inner_weather.yaml`

```yaml
skill:
  name: inner_weather
  mode: moment_blog_mode
  purpose: "Gọi tên thời tiết bên trong người viết ở thời điểm hiện tại."
  core_question: "Thời tiết bên trong người viết ngay lúc này là gì?"
  input:
    required:
      - sensory_handoff
      - raw_notes
    optional:
      - emotional_notes

  tasks:
    - identify_dominant_feeling
    - identify_secondary_feeling
    - map_emotional_motion
    - ground_emotion_in_body
    - preserve_uncertainty

  do_not:
    - diagnose
    - explain_cause_beyond_notes
    - force_resolution
    - force_lesson
    - turn_feeling_into_theory

  output:
    artifact: inner_weather.md
    sections:
      - dominant_feeling
      - secondary_feeling
      - emotional_motion
      - bodily_evidence
      - uncertainty_notes
    handoff:
      required: true
      target_words: "40-70"
      focus: "What the inside weather feels like, not why it exists."

  style_rules:
    - use_plain_language
    - avoid_clinical_tone
    - avoid_spiritual_overclaim
```

## 3. `cosmic_signal_reader.yaml`

```yaml
skill:
  name: cosmic_signal_reader
  mode: moment_blog_mode
  purpose: "Tìm tín hiệu trực giác trong khoảnh khắc, nhưng chỉ khi có dữ kiện gốc đủ rõ."
  core_question: "Khoảnh khắc này đang thì thầm điều gì với người viết?"
  input:
    required:
      - sensory_handoff
      - inner_weather_handoff
    optional:
      - recurring_motifs
      - song_or_phrase_anchor

  tasks:
    - detect_grounded_signal
    - distinguish_intuition_from_fact
    - detect_resonant_phrase
    - allow_no_signal_if_absent
    - keep_signal_small_and_specific

  do_not:
    - claim_universal_truth
    - force_cosmic_message
    - predict_future
    - give_advice
    - generalize_into_philosophy
    - treat_intuition_as_fact

  output:
    artifact: signal_note.md
    sections:
      - signal
      - evidence_for_signal
      - what_makes_it_feel_resonant
      - what_is_not_being_claimed
    handoff:
      required: true
      target_words: "40-70"
      focus: "A small, grounded signal the moment seems to whisper."

  style_rules:
    - prefer_hedged_language
    - keep_signal_modest
    - use_phrases_like_maybe_or_it_feels_like_when_needed
```

## 4. `moment_writer.yaml`

```yaml
skill:
  name: moment_writer
  mode: moment_blog_mode
  purpose: "Viết bản nháp ngắn giữ lại khoảnh khắc đang sống."
  core_question: "Nếu chỉ giữ lại khoảnh khắc này, bài viết cần nói điều gì?"
  input:
    required:
      - sensory_handoff
      - inner_weather_handoff
      - signal_handoff
    optional:
      - shared_voice_profile
      - title_seed

  tasks:
    - build_short_moment_arc
    - preserve_present_tense_energy
    - write_with_spoken_naturalness
    - keep_one_resonant_signal
    - close_with_echo_not_lecture

  do_not:
    - tell_full_life_story
    - explain_transformation
    - add_coaching
    - add_moral
    - overdecorate_language
    - write_more_than_one_moment

  output:
    artifact: moment_draft.md
    limits:
      target_words: "180-600"
      max_words: 600
    structure:
      - scene
      - felt_response
      - signal
      - resonant_closing
    handoff:
      required: true
      target_words: "40-70"
      focus: "A compact draft that still feels alive and immediate."

  style_rules:
    - natural_vietnamese
    - lean_and_clear
    - emotional_but_not_flowery
    - one_intuitive_message_max
```

## 5. `breath_editor.yaml`

```yaml
skill:
  name: breath_editor
  mode: moment_blog_mode
  purpose: "Làm bài thở ra, nhẹ hơn, trong hơn, đúng tinh thần moment."
  core_question: "Cần bỏ hoặc làm nhẹ điều gì để khoảnh khắc được tự cất tiếng?"
  input:
    required:
      - moment_draft
    optional:
      - shared_voice_profile
      - style_notes

  tasks:
    - cut_repetition
    - simplify_heavy_sentences
    - keep_only_one_center
    - check_under_word_limit
    - remove_over_explanation
    - preserve_authentic_voice

  do_not:
    - add_new_insight
    - intensify_emotion_unnecessarily
    - polish_into_literary_overkill
    - turn_into_essay
    - expand_scope

  output:
    artifact: moment_edited.md
    secondary_artifact: edit_log.md
    sections:
      - edited_moment_blog
      - edit_log
    handoff:
      required: false
      target_words: "30-50"
      focus: "What was trimmed and why."
    max_edits: 5

  style_rules:
    - minimal_editing
    - keep_distinctive_phrasing
    - protect_short_form
    - avoid_preachy_tone
```

## 6. `gentle_witness.yaml`

```yaml
skill:
  name: gentle_witness
  mode: moment_blog_mode
  purpose: "Xác nhận bài còn thật, còn trong, còn là một khoảnh khắc sống."
  core_question: "Bài viết có còn là một khoảnh khắc sống, hay đã bị kéo thành bài học?"
  input:
    required:
      - moment_edited
    optional:
      - signal_note
      - voice_profile

  tasks:
    - verify_presence
    - verify_clarity
    - verify_non_didactic_tone
    - verify_moment_center
    - verify_ending_resonance

  do_not:
    - coach
    - diagnose
    - generalize
    - lecture
    - add_new_content

  output:
    artifact: witness_report.md
    sections:
      - what_still_feels_alive
      - what_felt_forced
      - what_should_remain_untouched
    handoff:
      required: true
      target_words: "30-60"
      focus: "A calm verdict on whether the moment still breathes."

  style_rules:
    - calm
    - factual
    - supportive
    - non-judgmental
```

## 10. Quyết định thiết kế quan trọng

### Nên giữ

- artifact + handoff;
- mode tách biệt;
- learning riêng theo mode;
- human writer vẫn giữ quyền chốt cuối.

### Không nên làm

- dùng `coach_agent` cho moment mode;
- ép cosmic signal thành “điềm báo”;
- trộn learning giữa deep và moment;
- để moment mode leo lên thành bài essay ngắn;
- để editor viết thêm ý mới.

## 11. Kết luận

`moment_blog_mode` là một mode thật sự khác, không phải bản rút gọn của deep blog.

Nếu deep blog là:

- viết để hiểu một trải nghiệm,

thì moment blog là:

- viết để nghe một khoảnh khắc.

Đây là nhánh đáng phát triển song song vì:

- nhẹ hơn;
- viết đều hơn;
- hợp với nhật ký hiện tại;
- giữ được cảm xúc sống;
- vẫn có chiều sâu vừa đủ mà không nặng triết lý.

---

# PHẦN BỔ SUNG: PHẢN BIỆN TỪ CÁC HỆ THỐNG AI (2026-07-22)

Dưới đây là các góc nhìn phản biện từ Claude Opus 4.6 và Gemini 3.1 Pro nhằm hoàn thiện kế hoạch của GPT-5.6 Sol trước khi bước vào giai đoạn triển khai.

## 1. Phản Biện Kỹ Thuật (từ Claude Opus 4.6)

*Đánh giá tập trung vào codebase, engine, và tính khả thi kỹ thuật.*

### Những điều hợp lý, hiệu quả
- **Triết lý phân tách mode rất đúng bản chất**: Không đối xử `moment_blog_mode` như "deep blog rút gọn" mà định nghĩa nó là một mode khác về bản thể.
- **Cấu trúc agent cho moment mode được thiết kế rất có ý đồ**: Chuỗi agent phản ánh một luồng nhận thức tự nhiên.
- **Danh sách `do_not` trong mỗi skill YAML rất mạnh**: Là ranh giới triết lý ngăn ngừa chính xác lỗi mà LLM hay mắc.
- **Tách learning theo mode là bắt buộc và đúng**.
- **Chiến lược chuyển đổi an toàn** và tái sử dụng shared core hợp lý.

### Những điều chưa hợp lý, chưa hiệu quả, còn thiếu
- ❌ **Thiếu hoàn toàn thiết kế mode router**: Kế hoạch chỉ đề cập CLI flag, thiếu logic auto-detect hoặc router agent.
- ❌ **Thiếu thay đổi engine code**: Kế hoạch chỉ là YAML. Không chỉ rõ cách sửa `workflow.py` để hỗ trợ chọn flow YAML theo mode, hay sửa `run_workflow.py` và `learning.py`.
- ❌ **`breath_editor` xuất hiện ở cả shared core và moment core**: Mâu thuẫn thiết kế.
- ❌ **Thiếu `voice_keeper` và `publisher` trong cả hai flow**.
- ❌ **`gentle_witness` đặt sai vị trí**: Đặt sau `breath_editor` nhưng không có cơ chế vòng lặp (loop back) nếu phát hiện lỗi.
- ❌ **Thiếu xử lý `provocative` mode đã tồn tại**: Hệ thống hiện dùng `--style` cho reflective/provocative. Kế hoạch không phân biệt rõ hai trục phân loại Mode và Style.
- ❌ **Context window management**: Dùng 6 agent cho một bài 300-600 từ có thể tạo ra overhead context lớn. Handoff target_words quá nhỏ (40-70 từ).

### Đề xuất của Claude Opus 4.6
1. Bổ sung Mode Router Agent hoặc Heuristic để tự động phát hiện (auto-detect) mode dựa trên input.
2. Tạo Implementation Plan chi tiết cho tầng Engine (`workflow.py`, `learning.py`, CLI).
3. Giảm agent cho moment mode từ 6 xuống 4-5 (gộp `sensory_capture` và `inner_weather`).
4. Phân tách rõ hai phiên bản `breath_editor` cho deep và moment.
5. Thêm quality gate loop cho `gentle_witness` (trả về `breath_editor` nếu cần sửa).
6. Tái cấu trúc taxonomy 2 chiều: **Mode** (deep/moment) × **Style** (reflective/provocative).

---

## 2. Phản Biện Độc Lập / Meta-Critique (từ Gemini 3.1 Pro)

*Đánh giá lại bản phản biện của Claude Opus 4.6 để cân bằng giữa tính kỹ thuật (software engineering) và triết lý chánh niệm (mindfulness) của hệ thống.*

### Những điểm Claude nhận định xuất sắc
- **Bắt lỗi về tầng Engine Code và Architecture**: Việc chỉ ra Sol thiếu sót hoàn toàn phần cập nhật core engine (`workflow.py`, v.v.) là cực kỳ chính xác và quan trọng.
- **Phát hiện mâu thuẫn hệ thống (Mode vs Style)**: Chỉ ra đúng điểm mù của Sol về việc trục "Style" đã tồn tại và dễ xung đột taxonomy với "Mode" mới.
- **Sửa lỗi mâu thuẫn của `breath_editor`**.

### Những điểm Claude "Over-engineering" và đi sai triết lý
- ❌ **Đề xuất Mode Router Agent (Rườm rà và sai triết lý)**: Lựa chọn Mode là ý định (intent) của người viết, không phải thứ AI nên tự đoán. Việc dùng `--mode` flag qua CLI (như Sol đề xuất) là cách tôn trọng agency của người dùng nhất và giữ hệ thống nhẹ nhàng.
- ❌ **Đề xuất gộp `sensory_capture` và `inner_weather` (Phá vỡ triết lý)**: Trong chánh niệm, việc tách biệt quan sát bên ngoài và phản ứng bên trong là cốt lõi để không bị cuốn vào diễn dịch. Gộp chung sẽ làm mất độ trong trẻo của reasoning.
- ❌ **Đề xuất Quality Gate Loop cho `gentle_witness`**: Biến Witness thành một "Adversarial Editor" đi ngược lại tinh thần thiền định (chỉ quan sát, không can thiệp). Về mặt kỹ thuật, nó đòi hỏi phải viết lại pipeline tuyến tính hiện tại thành một hệ thống DAG phức tạp một cách không cần thiết.
- ❌ **Nhầm lẫn ma trận Mode × Style (Provocative Moment)**: Một "Provocative Moment" là một khái niệm tự mâu thuẫn vì Provocative mang tính đối đầu, trong khi Moment mang tính lắng nghe, không phán xét.

### Đề xuất cuối cùng cho Lộ Trình Triển Khai (Tinh chỉnh từ Sol và Claude)
1. **Kiến trúc Engine & CLI**: Không làm Mode Router Agent. Dùng `--mode deep` và `--mode moment` thông qua cờ CLI.
2. **Cập nhật `workflow.py`**: Thêm logic phân nhánh flow YAML. Nếu mode là deep thì load `flow/write_deep_blog.yaml` (đổi tên từ `write_blog.yaml`), nếu là moment thì load `flow/write_moment_blog.yaml`.
3. **Cập nhật taxonomy**: Phân định rõ `--mode` quyết định Flow YAML nào được chạy, `--style` quyết định folder skill nào được nạp.
4. **Giới hạn Style cho Moment**: Tạm thời vô hiệu hóa `--style provocative` khi chạy `--mode moment` (tự động fallback về `reflective`).
5. **Giữ nguyên 6 Agent của Sol**: Không gộp `sensory` và `inner_weather` để bảo vệ luồng tư duy chánh niệm.
6. **Không dùng Loop cho `gentle_witness`**: `gentle_witness` tạo ra report và dừng lại để human writer tự quyết định (đúng tinh thần của một nhà xuất bản mini).
7. **Cập nhật Learning Loop**: Phân chia việc lưu patterns theo mode (`learning/deep/editorial_patterns.md` và `learning/moment/editorial_patterns.md`).
