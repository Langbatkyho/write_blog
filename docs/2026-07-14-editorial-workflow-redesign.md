# Editorial Workflow Redesign Log

Date: 2026-07-14  
Project: `write_blog`

## 1. Why The Workflow Changed

The previous workflow already had a handoff layer, but its role boundaries were still blurry:

- `writing_agent` was both drafting and partially optimizing the writing.
- `reader_experience` still behaved like a reviewer by producing weaknesses, scores, and suggested revisions.
- `coach_agent` read the draft before reader friction had been resolved.
- `future_self` was responsible for producing `final_blog.md`, which weakened human ownership of the final article.

The referenced conversation introduced a clearer editorial model:

```text
Writer intent
  -> faithful draft
  -> blind reader diary
  -> minimal editor intervention
  -> coaching reflection
  -> future-self reflection
  -> human final decision
```

The central architectural principle is:

> Each agent protects one truth and must not answer another agent's question.

## 2. New Agent Loyalties

| Agent | Loyalty | Main Question |
| --- | --- | --- |
| `story_architect` | Truth of the story | What really happened? |
| `reflection_engine` | Truth of inner change | What changed inside the writer? |
| `writing_agent` | Writer's voice | How would the writer tell this if they had enough time? |
| `reader_experience` | First-time reader experience | What did the reader feel while reading once? |
| `editor_agent` | Connection | What minimum edit reduces reader friction? |
| `coach_agent` | Writer growth | What is the writer still not seeing? |
| `future_self` | Future integrity | Would the writer still stand under this article in five years? |

## 3. Workflow Changes

New workflow:

```text
story_architect
  -> reflection_engine
  -> writing_agent
  -> reader_experience
  -> editor_agent
  -> coach_agent
  -> future_self
  -> human writer
```

Main outputs:

- `story_map.md`
- `reflection_notes.md`
- `draft_blog.md`
- `reader_report.md`
- `edited_blog.md`
- `edit_log.md`
- `coaching_report.md`
- `future_reflection.md`

Human-owned outputs:

- `final_blog.md`
- `production_blog.md`

## 4. Implementation Changes

Changed `flow/write_blog.yaml`:

- Added `editor_agent` after `reader_experience`.
- Changed `future_self` output from `final_blog.md` to `future_reflection.md`.
- Changed `final_output` to distinguish AI draft, future reflection, human final, and production outputs.
- Updated `context_policy` so:
  - `reader_experience` gets only `draft_blog.md` for blind review.
  - `editor_agent` gets draft + reader report.
  - `coach_agent` gets edited article instead of raw draft.
  - `future_self` gets edited article plus editor/coach/reflection handoffs.

Changed skills:

- Rewrote `writing_agent.yaml` as a ghost writer that creates a faithful first draft.
- Rewrote `reader_experience.yaml` as a first-time reader diary with no diagnosis or recommendations.
- Added `editor_agent.yaml` as a minimum-intervention connection editor.
- Rewrote `coach_agent.yaml` to focus on writer blind spots after editing.
- Rewrote `future_self.yaml` to produce reflection only, not final article rewrite.
- Updated `editorial_learning.yaml` to understand the new workflow and `editor_agent`.

Changed engine/config:

- Added per-stage model config for `editor_agent`.
- Added support for `secondary_name` artifacts so `editor_agent` can save `edit_log.md` separately from `edited_blog.md`.
- Updated learning fallback so it can use `final_blog.md` when present, or `edited_blog.md` as the AI-supported draft when human final has not yet been created.

## 5. Expected Behavior

During a dry-run or API run, the engine should now create:

- artifact files for all stages
- handoff files for all stages
- `edited_blog.md`
- `edit_log.md`
- `future_reflection.md`
- `run_log.md`
- `handoff_log.md`
- `step_outputs.json`
- `metadata.json`

The learning loop should still use full artifacts from `step_outputs.json`, not compact handoffs.

## 6. Lessons For Future Project Work

- Do not let one agent do many jobs just because the model can.
- "Reader" and "Editor" are different roles: reader reports experience; editor diagnoses and intervenes.
- Final publication should remain human-owned.
- Skill YAML should describe both purpose and boundaries, especially excluded responsibilities.
- Workflow design should be reviewed whenever a new real-world feedback loop appears.
