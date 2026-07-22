# Kế Hoạch Nâng Cấp `mindful_writing_os` Thành Hệ Hai Writing Modes
Ngày: 2026-07-22

## Tóm Tắt

Nâng cấp `mindful_writing_os` từ một workflow viết phản tư đơn sang một hệ hai chế độ:

- `deep_blog_mode`: bài dài, phản tư, chuyển hóa, giữ nguyên logic hiện tại.
- `moment_blog_mode`: bài ngắn, hiện tại, trực giác, giữ tín hiệu của khoảnh khắc.

Mục tiêu:

- giữ `moment_blog_mode` dưới 600 từ;
- ưu tiên cảm giác, cảnh vật, tín hiệu;
- giảm triết lý sâu;
- không biến moment mode thành “deep blog mini”;
- vẫn giữ người viết là người quyết định cuối cùng.

## Kiến Trúc Đích

### Hai writing modes

```yaml
mindful_writing_os:
  modes:
    deep_blog_mode:
      purpose: "Viết để hiểu và chuyển hóa trải nghiệm"
      target_length: "1000-1500 words"
      depth: "high"

    moment_blog_mode:
      purpose: "Viết để nghe một khoảnh khắc đang sống"
      target_length: "300-600 words"
      depth: "light"
```

### Nguyên tắc chia mode

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

## Shared Core Và Mode Core

### Shared core

Hai mode dùng chung các phần sau:

- `source_reader`
- `voice_keeper`
- `breath_editor`
- `publisher`
- `learning_keeper`

### Deep core

Giữ nguyên cho `deep_blog_mode`:

- `story_architect`
- `reflection_engine`
- `writing_agent`
- `reader_experience`
- `editor_agent`
- `coach_agent`
- `future_self`

### Moment core

Dành riêng cho `moment_blog_mode`:

- `sensory_capture`
- `inner_weather`
- `cosmic_signal_reader`
- `moment_writer`
- `breath_editor`
- `gentle_witness`

## Luồng Triển Khai

### Deep blog mode

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

### Moment blog mode

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

## Thiết Kế `moment_blog_mode`

`moment_blog_mode` phải giữ các đặc tính sau:

- ngắn;
- trực tiếp;
- hiện tại;
- cảm giác hơn lý luận;
- tín hiệu hơn kết luận;
- như một mảnh nhật ký có ánh sáng;
- không ép bài học;
- không coaching;
- không triết lý hóa mọi chi tiết.

### Quy tắc riêng

- `sensory_capture` chỉ ghi nhận cảnh và thân thể.
- `inner_weather` chỉ gọi tên thời tiết bên trong.
- `cosmic_signal_reader` chỉ nêu tín hiệu nhỏ, có căn cứ.
- `moment_writer` chỉ viết một khoảnh khắc trung tâm.
- `breath_editor` chỉ cắt gọn, không thêm ý mới.
- `gentle_witness` chỉ xác nhận bài còn sống và còn trong.

## Kế Hoạch Điều Phối Multi-Agent

### Phase 0: Khóa contract trước khi viết code

Coordinator chốt trước 4 hợp đồng:

- phân biệt rõ `mode` và `style`;
- mỗi agent chỉ có một câu hỏi chính;
- learning phải tách theo mode;
- human writer giữ quyền chốt cuối.

### Phase 1: Chia việc theo cụm ownership

#### Agent A - Engine/CLI

Phạm vi:

- `engine/run_workflow.py`
- `engine/workflow.py`
- `engine/config.example.yaml`

Nhiệm vụ:

- thêm `--mode deep|moment`;
- giữ `--style` tách biệt với `--mode`;
- chọn flow theo mode;
- gắn `mode`, `style`, `workflow_file` vào run metadata;
- bảo đảm legacy deep flow vẫn chạy.

#### Agent B - Moment Editorial

Phạm vi:

- `flow/write_moment_blog.yaml`
- `skills/moment/reflective/*.yaml`
- input mẫu cho moment mode

Nhiệm vụ:

- viết flow moment hoàn chỉnh;
- viết skill YAML cho từng agent moment;
- giữ handoff ngắn và rõ;
- không cho moment bị kéo sang coaching.

#### Agent C - Learning & Tests

Phạm vi:

- `engine/learning.py`
- test mới cho mode separation, flow routing, learning routing

Nhiệm vụ:

- học theo `run.metadata.mode`;
- phân tách deep/moment patterns;
- kiểm tra legacy runs;
- xác minh learning không trộn hai mode.

### Phase 2: Handoff bắt buộc giữa các agent

Mỗi agent phải trả về:

- file đã đổi;
- quyết định đã chốt;
- contract giả định;
- test đã chạy;
- điểm còn rủi ro.

Coordinator chỉ ghép khi 3 bộ handoff khớp nhau.

### Phase 3: Tích hợp

Coordinator làm 4 việc:

- ghép CLI, flow, learning;
- cập nhật README/docs;
- bổ sung integration tests;
- chạy dry-run cho cả deep và moment.

### Phase 4: Vòng sửa lỗi

Nếu có lệch contract:

- lỗi engine quay về Agent A;
- lỗi editorial quay về Agent B;
- lỗi learning/test quay về Agent C.

Không để một agent sửa chéo phần của agent khác nếu chưa chốt interface.

## Kế Hoạch Chuyển Đổi Hệ Thống

### Bước 1: Định danh mode hiện tại là `deep_blog_mode`

Không đổi logic, chỉ đổi tên ngữ nghĩa và metadata.

### Bước 2: Thêm `moment_blog_mode`

Khởi đầu với 6 agent:

- `sensory_capture`
- `inner_weather`
- `cosmic_signal_reader`
- `moment_writer`
- `breath_editor`
- `gentle_witness`

### Bước 3: Thêm mode routing ở CLI và engine

- `--mode deep`
- `--mode moment`

### Bước 4: Tách output và learning theo mode

Learning nên tách thành:

- `deep_blog_patterns.md`
- `moment_blog_patterns.md`
- `shared_voice_patterns.md`

### Bước 5: Kiểm chứng bằng cùng một input

Một input phải chạy được theo 2 mode:

- deep mode cho ra bài phản tư dài;
- moment mode cho ra bài ngắn, trong, trực giác.

## Rủi Ro Cần Tránh

- moment mode bị kéo thành deep mode mini;
- `cosmic_signal_reader` diễn giải quá tay;
- learning của hai mode bị trộn;
- `breath_editor` can thiệp quá sâu;
- `coach_agent` lọt vào moment flow;
- `gentle_witness` bị biến thành vòng coaching ngược.

## Tiêu Chí Chấp Nhận

Hệ mới đạt yêu cầu nếu:

- một input chạy đúng mode đã chọn;
- moment blog dưới 600 từ;
- moment blog giữ được cảm giác hiện tại;
- không cần giải thích quá mức;
- learning phân biệt được deep và moment;
- người viết vẫn chốt bản cuối.

---

# Nháp Skill YAML Cho Các Agent Của `moment_blog_mode`

## 1. `sensory_capture.yaml`

```yaml
skill:
  name: sensory_capture
  mode: moment_blog_mode
  purpose: "Ghi lại khoảnh khắc hiện tại bằng giác quan, không diễn giải sâu."
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
  purpose: "Tìm tín hiệu trực giác trong khoảnh khắc, chỉ khi có dữ kiện gốc đủ rõ."
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
    - use_maybe_when_needed
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
  core_question: "Bài viết còn là một khoảnh khắc sống hay đã bị kéo thành bài học?"
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

## Quyết Định Thiết Kế Quan Trọng

### Nên giữ

- artifact + handoff;
- mode tách biệt;
- learning riêng theo mode;
- human writer giữ quyền chốt cuối.

### Không nên làm

- dùng `coach_agent` cho moment mode;
- ép cosmic signal thành chân lý lớn;
- trộn learning giữa deep và moment;
- để moment mode leo thành bài essay ngắn;
- để editor viết thêm ý mới.

## Kết Luận

`moment_blog_mode` là một mode thật sự khác, không phải bản rút gọn của deep blog.

Nếu deep blog là:

- viết để hiểu một trải nghiệm,

thì moment blog là:

- viết để nghe một khoảnh khắc.

Đây là nhánh nên phát triển song song vì:

- nhẹ hơn;
- viết đều hơn;
- hợp với nhật ký hiện tại;
- giữ được cảm xúc sống;
- vẫn có chiều sâu vừa đủ mà không nặng triết lý.
