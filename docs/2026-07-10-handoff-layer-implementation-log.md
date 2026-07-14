# Implementation Log - Handoff Layer

Date: 2026-07-10  
Project: `write_blog`  
Main goal: complete the "Handoff Layer" plan to reduce repeated tokens between workflow stages, then document the work and lessons learned.

## 1. Kế hoạch ban đầu

The plan started from the observation that the last stage, `future_self`, was reading too much repeated context. The old engine passed nearly all previous stage outputs into every later prompt. That made the workflow progressively more expensive as it moved downstream.

The proposed optimization was to make every stage produce two outputs:

- `Artifact`: the full output for observation, review, debugging, and learning.
- `Handoff`: a compact structured summary, around 120-250 Vietnamese words, for downstream agents.

The key implementation requirements were:

- update skill YAML schemas so every stage knows it must return both `## Artifact` and `## Handoff`
- update `flow/write_blog.yaml` so every stage declares:
  - `output`
  - `handoff_output`
  - `context_policy`
- update the engine so it:
  - parses `## Artifact` and `## Handoff`
  - saves artifact and handoff separately
  - writes artifact to the existing output file
  - writes handoff to a new handoff file
  - stores both in `step_outputs.json`
  - passes only selected handoffs/artifacts to the next stage
  - keeps learning loop based on full artifacts
  - records estimated artifact/handoff token metrics
- add tests for parser and context policy behavior
- verify by dry-run and offline learning

## 2. Kiến trúc dự án hiện tại

Current project structure:

```text
write_blog/
|-- engine/
|   |-- config.example.yaml
|   `-- run_workflow.py
|-- examples/
|   `-- blog_input_template.md
|-- flow/
|   `-- write_blog.yaml
|-- skills/
|   |-- story_architect.yaml
|   |-- reflection_engine.yaml
|   |-- writing_agent.yaml
|   |-- reader_experience.yaml
|   |-- coach_agent.yaml
|   |-- future_self.yaml
|   `-- editorial_learning.yaml
|-- tests/
|   `-- test_handoff_parser.py
|-- docs/
|   `-- 2026-07-10-handoff-layer-implementation-log.md
|-- README.md
`-- mindful_writing_os.md
```

Core runtime:

- `engine/run_workflow.py` is the workflow runner.
- `flow/write_blog.yaml` is the workflow graph and context policy source of truth.
- `skills/*.yaml` define the behavior and output contract for each agent.
- `engine/config.example.yaml` controls OpenAI endpoint, default model, per-stage model overrides, and learning model overrides.

Current handoff data flow:

- `story_architect`
  - artifact: `story_map.md`
  - handoff: `story_handoff.md`
  - receives no prior workflow context
- `reflection_engine`
  - artifact: `reflection_notes.md`
  - handoff: `reflection_handoff.md`
  - receives `story_architect` handoff
- `writing_agent`
  - artifact: `draft_blog.md`
  - handoff: `draft_handoff.md`
  - receives `story_architect` and `reflection_engine` handoffs
- `reader_experience`
  - artifact: `reader_report.md`
  - handoff: `reader_handoff.md`
  - receives story/reflection handoffs and full `writing_agent` artifact
- `coach_agent`
  - artifact: `coaching_report.md`
  - handoff: `coaching_handoff.md`
  - receives story/reflection handoffs and full `writing_agent` artifact
- `future_self`
  - artifact: `final_blog.md`
  - handoff: `final_handoff.md`
  - receives `reflection_engine`, `reader_experience`, and `coach_agent` handoffs, plus full `writing_agent` artifact

Generated files per run:

- `run_log.md`: full artifact log
- `handoff_log.md`: compact handoff log
- `step_outputs.json`: artifact, handoff, file names, fallback flag, and estimated token metrics
- `metadata.json`: model configuration, context strategy, stage metrics, and total estimated artifact/handoff tokens
- individual artifact files and handoff files

Learning loop:

- API learning and offline learning still read full artifacts from `step_outputs.json`.
- This preserves full evidence for `production_blog.md` comparison.
- Handoffs are used for workflow execution, not as the archival source of truth.

## 3. Change Log

Implemented changes:

- Added `handoff_output` and `context_policy` to every step in `flow/write_blog.yaml`.
- Updated each main skill YAML to declare:
  - `artifact_heading: "## Artifact"`
  - `handoff_heading: "## Handoff"`
  - artifact intent
  - handoff intent and included fields
- Updated `engine/run_workflow.py`:
  - added `parse_stage_response`
  - added `build_context_package`
  - added dry-run responses that include both artifact and handoff
  - changed prompt construction to include selected compact handoffs and selected full artifacts
  - changed prompt instructions to require exactly two top-level sections
  - added fallback handoff generation when a model omits `## Handoff`
  - stores artifacts and handoffs separately
  - writes `handoff_log.md`
  - writes per-step handoff files
  - writes nested `step_outputs.json`
  - writes estimated token metrics into `metadata.json`
  - keeps learning loop compatible by loading artifact content from nested `step_outputs.json`
- Added `tests/test_handoff_parser.py`:
  - parser correctly separates `## Artifact` and `## Handoff`
  - missing handoff uses fallback
  - context policy selects only requested handoffs/artifacts
- Updated `README.md` to document:
  - artifact/handoff format
  - generated handoff files
  - `handoff_log.md`
  - metadata token estimates
  - context policy behavior

Verification performed:

```powershell
python -m py_compile engine/run_workflow.py
python -m unittest tests.test_handoff_parser
python engine/run_workflow.py --input examples/blog_input_template.md --dry-run
python engine/run_workflow.py --learn-from-run runs\20260710_180536_raw-notes --offline-learning
```

Observed dry-run evidence:

- run folder: `runs/20260710_180536_raw-notes`
- generated artifact files:
  - `story_map.md`
  - `reflection_notes.md`
  - `draft_blog.md`
  - `reader_report.md`
  - `coaching_report.md`
  - `final_blog.md`
- generated handoff files:
  - `story_handoff.md`
  - `reflection_handoff.md`
  - `draft_handoff.md`
  - `reader_handoff.md`
  - `coaching_handoff.md`
  - `final_handoff.md`
- generated logs:
  - `run_log.md`
  - `handoff_log.md`
  - `step_outputs.json`
  - `metadata.json`
- learning loop output:
  - `runs/20260710_180536_raw-notes/learning/20260710_180601/editorial_learning_report.md`
  - `workflow_tuning_suggestions.md`
  - `learning_log.md`
  - `metadata.json`

Known note:

- The shell reports this folder as not being a git repository from the current working context, even though a `.git` path appears in filesystem permissions. No commit or branch status was available.

## 4. User Prompts

Main user prompts that shaped the project today:

1. "Tôi muốn sử dụng các tài liệu dạng YAML trong thư mục skills của dự án để thiết lập một workflow viết blog với input của tôi và sự hỗ trợ của AI"

2. "Tôi muốn 1 engine cấu hình với API Key và Endpoint của OpenAI để chạy tự động workflow này đồng thời log lại toàn bộ các output từng bước vào 1 file riêng cho mỗi lần chạy."

3. "Tôi muốn mở rộng thiết kế như sau: Từ final_blog.md tôi sẽ là human editor chỉnh sửa bằng tay ra một bản production_blog.md. Dựa trên đó, AI học lại từ bản production_blog.md đó để tham chiếu lại toàn bộ workflow. Từ đó đưa ra các insight mới để giúp tôi tinh chỉnh từng giai đoạn workflow."

4. "Tôi muốn cấu hình để chọn model cho từng giai đoạn trong workflow. Mục đích là khai thác các model giá rẻ cho những giai đoạn không đòi hỏi suy luận và sáng tạo mức độ cao. Tôi cũng muốn bạn bổ sung cách chạy vòng lặp learning mà không cần OpenAI API."

5. User observation about a larger optimization opportunity:

   Stage 6 was reading too much repeated history. Instead of passing full outputs between all stages, each agent should output an `Artifact` for debug/review and a compact `Handoff` for downstream agents.

6. "PLEASE IMPLEMENT THIS PLAN: Thêm Handoff Layer Để Giảm Token Lặp Giữa Các Stage"

7. Goal continuation request:

   Complete the handoff layer plan, then log the full work process into `docs` under:
   - initial plan
   - current project architecture
   - change log
   - user prompts
   - workflow analysis and lessons for future implementations

## 5. Phân tích workflow để tìm ra bài học rút kinh nghiệm cho các lần triển khai dự án tiếp theo

### Bai hoc 1: Token optimization should start with context architecture

Choosing cheaper models helps, but the larger cost source was repeated context. The old workflow passed all prior outputs forward. That made later stages pay repeatedly for context they did not need.

Better pattern:

- keep full artifacts for review and learning
- pass compact handoffs for execution
- make context transfer explicit in the flow file

### Bai hoc 2: Debug output and execution context should be separate

The original design used one output for two jobs:

- human/debug visibility
- downstream machine context

Those jobs have different size and precision requirements. Separating `artifact` from `handoff` makes the workflow easier to optimize without losing observability.

### Bai hoc 3: The flow file should own context policy

Putting `context_policy` in `flow/write_blog.yaml` makes the workflow inspectable. A future maintainer can see exactly why `future_self` receives the draft artifact but only compact reflection/reader/coach handoffs.

This is better than hiding context decisions inside Python code.

### Bai hoc 4: Learning loops need full evidence, not compressed handoff

Handoffs are useful for execution, but learning from `production_blog.md` needs full artifacts. If the learning loop used only handoffs, it could miss the real cause of human edits.

The current design preserves that distinction:

- execution path uses handoffs
- learning path uses artifacts

### Bai hoc 5: Fallback behavior matters for LLM output contracts

Even with clear prompts, a model may forget to emit `## Handoff`. The engine should not fail the whole workflow unnecessarily. It now creates a local fallback handoff and marks `handoff_used_fallback` in `step_outputs.json`.

This keeps the workflow robust while preserving traceability.

### Bai hoc 6: Verification should cover both parser and runtime artifacts

The parser unit test proves the contract at the smallest level. The dry-run proves the runtime creates the expected files. Offline learning proves compatibility with downstream workflow history.

For future workflow work, useful verification layers are:

- schema/YAML parse check
- parser unit test
- dry-run file generation check
- downstream compatibility check

### Bai hoc 7: Cost controls should be layered

The project now has three cost-control layers:

1. per-stage model selection
2. handoff-based context reduction
3. offline learning mode without API calls

This layered approach is stronger than relying on any single cost-control mechanism.

### Recommended next iteration

The next high-value improvement is token telemetry before real API calls:

- estimate prompt token size for each stage before calling the model
- write estimated input/output budget to metadata
- optionally fail or warn if a stage exceeds a configured budget

That would turn cost optimization from a design assumption into a measurable runtime signal.
