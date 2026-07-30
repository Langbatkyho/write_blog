# Graph Report - D:\Nghiên cứu AI\write_blog  (2026-07-30)

## Corpus Check
- 156 files · ~119,009 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 598 nodes · 1651 edges · 69 communities (24 shown, 45 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 118 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Datetime Logic
- Apptest Logic
- Bridge.Py Logic
- Learning.Py Logic
- Title() Logic
- Style() Logic
- Lab.Py Logic
- Compiler.Py Logic
- Migration.Py Logic
- Coach Agent (Provocative) Logic
- Archive.Py Logic
- Compileresult Logic
- Mergeconflict Logic
- Reset() Logic
- Contract.Py Logic
- () Logic
- Voice Lab Refactor Plan Logic
- Mindful Blog Workflow Logic
- Editor (Minh Hóm Hỉnh) Logic
- Reader (Minh Hóm Hỉnh) Logic
- Witness (Minh Hóm Hỉnh) Logic
- Weather (Minh Hóm Hỉnh) Logic
- Writer (Minh Hóm Hỉnh) Logic
- Capture (Minh Hóm Hỉnh) Logic
- Deep Blog Mode Logic
- Moment Blog Mode Logic
- .Py Logic
- Moment Blog Mode Example 1 Logic
- Surrender The Flow - Không Kế Hoạch Logic
- Architect Logic
- Reflective (Moment) Logic
- .Py Logic
- .Py Logic
- Openai Config Logic
- Architecture Invariants Logic
- Refactor Checklist Logic
- Workflow Design Patterns Logic
- Agentic Workflow Architect Logic
- Project Agent Instructions Logic
- Project Agent Instructions Global Logic
- Code Review Report Logic
- Handoff Layer Logic
- Engine Refactoring Logic
- Editorial Workflow Redesign Review Logic
- Editorial Workflow Redesign Logic
- Redesign Refactoring Logic
- Client Routing Logic
- Antigravity Workflow Run Logic
- Multi Style Implementation Logic
- Mindful Writing Os Final Logic
- Mindful Writing Os Plan Logic
- Guided Style Voice Lab Plan Logic
- Voice Dna Logic
- Multi Editable Style Final Logic
- Multi Editable Style Plan Logic
- Voice Lab Final Plan Logic
- Agent Handoff Logic
- Rules Skill Refactor Logic
- Mindful Blog Workflow Logic
- Trải Nghiệm Cảm Xúc Logic
- Lái Xe Và Tỉnh Thức Logic
- Tìm Thấy Bình An Logic
- Mindful Moment Blog Workflow Logic
- Provocative Style Meta Logic
- Reflective (Deep) Logic
- Learning Logic
- Minh Hóm Hỉnh Logic

## God Nodes (most connected - your core abstractions)
1. `StyleProfile` - 39 edges
2. `resolve_path()` - 31 edges
3. `compile_style()` - 31 edges
4. `_confirmed_profile()` - 29 edges
5. `load_yaml()` - 28 edges
6. `run_workflow()` - 28 edges
7. `analyze_samples()` - 26 edges
8. `run_learning_loop()` - 26 edges
9. `read_text()` - 25 edges
10. `publish_style()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `test_learning_rejects_invalid_source_before_client_call()` --calls--> `run_learning_loop()`  [INFERRED]
  tests/test_workflow_runtime_contract.py → engine/workflow_learning.py
- `Deep Blog Mode` --semantically_similar_to--> `Deep Blog Mode`  [INFERRED] [semantically similar]
  docs/2026-07-22-mindful_writing_os-two-writing-modes-plan.md → README.md
- `Moment Blog Mode` --semantically_similar_to--> `Moment Blog Mode`  [INFERRED] [semantically similar]
  docs/2026-07-22-mindful_writing_os-two-writing-modes-plan.md → README.md
- `test_structured_call_rejects_prompt_over_context_before_gemini()` --calls--> `_call_structured()`  [EXTRACTED]
  tests/test_voice_lab.py → engine/voice_lab/analyzer.py
- `test_analyzer_fails_closed_on_malformed_output()` --calls--> `analyze_samples()`  [EXTRACTED]
  tests/test_voice_lab.py → engine/voice_lab/analyzer.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Writing Modes** — d_nghi_n_c_u_ai_write_blog_docs_2026_07_22_mindful_writing_os_two_writing_modes_plan_deep_blog_mode, d_nghi_n_c_u_ai_write_blog_docs_2026_07_22_mindful_writing_os_two_writing_modes_plan_moment_blog_mode [INFERRED 0.95]
- **Provocative Deep Agents Workflow** — skills_deep_provocative_story_architect_story_architect, skills_deep_provocative_reflection_engine_reflection_engine, skills_deep_provocative_writing_agent_writing_agent, skills_deep_provocative_reader_experience_reader_experience, skills_deep_provocative_editor_agent_editor_agent, skills_deep_provocative_coach_agent_coach_agent, skills_deep_provocative_future_self_future_self [EXTRACTED 1.00]
- **Reflective Deep Agents Workflow** — skills_deep_reflective_coach_agent_coach_agent, skills_deep_reflective_editor_agent_editor_agent, skills_deep_reflective_future_self_future_self, skills_deep_reflective_reader_experience_reader_experience, skills_deep_reflective_reflection_engine_reflection_engine [INFERRED 0.85]
- **Minh hóm hỉnh Moment Workflow** — skills_moment_minh_hom_hinh_breath_editor_breath_editor, skills_moment_minh_hom_hinh_cosmic_signal_reader_cosmic_signal_reader, skills_moment_minh_hom_hinh_gentle_witness_gentle_witness, skills_moment_minh_hom_hinh_inner_weather_inner_weather, skills_moment_minh_hom_hinh_moment_writer_moment_writer, skills_moment_minh_hom_hinh_sensory_capture_sensory_capture, skills_moment_minh_hom_hinh_style_meta_minh_hom_hinh [INFERRED 0.95]
- **Reflective Moment Workflow** — skills_moment_reflective_breath_editor_breath_editor, skills_moment_reflective_cosmic_signal_reader_cosmic_signal_reader, skills_moment_reflective_gentle_witness_gentle_witness, skills_moment_reflective_inner_weather_inner_weather, skills_moment_reflective_moment_writer_moment_writer, skills_moment_reflective_sensory_capture_sensory_capture, skills_moment_reflective_style_meta_reflective [INFERRED 0.95]
- **VA Natural Moment Workflow** — skills_moment_va_natural_breath_editor_breath_editor, skills_moment_va_natural_cosmic_signal_reader_cosmic_signal_reader, skills_moment_va_natural_gentle_witness_gentle_witness, skills_moment_va_natural_inner_weather_inner_weather, skills_moment_va_natural_moment_writer_moment_writer, skills_moment_va_natural_sensory_capture_sensory_capture, skills_moment_va_natural_style_meta_va_natural [INFERRED 0.95]

## Communities (69 total, 45 thin omitted)

### Community 0 - "Datetime Logic"
Cohesion: 0.05
Nodes (84): datetime, dialog, validate_client_map(), build_offline_tuning_suggestions(), main(), is_valid_style_slug(), Any, validate_style_metadata() (+76 more)

### Community 1 - "Apptest Logic"
Cohesion: 0.06
Nodes (96): AppTest, analyze_samples(), _call_structured(), _chunk_samples(), _context_budget(), _dedupe_evidence(), estimate_tokens(), _max_chunk_end() (+88 more)

### Community 2 - "Bridge.Py Logic"
Cohesion: 0.06
Nodes (39): call_antigravity(), Any, Sử dụng file-based bridge để chờ Antigravity agent xử lý prompt. Trả về…, build_client_map(), create_routing_client(), _get_antigravity(), _get_gemini(), _get_openai() (+31 more)

### Community 3 - "Learning.Py Logic"
Cohesion: 0.10
Nodes (36): _budget_step_outputs(), build_learning_prompt(), build_offline_learning_report(), build_tuning_prompt(), _compact_skills(), _compact_workflow(), Any, render_offline_diff() (+28 more)

### Community 4 - "Title() Logic"
Cohesion: 0.14
Nodes (21): extract_title(), slugify(), BaseModel, model_validator, StyleMetadata, Any, StageResult, StepDefinition (+13 more)

### Community 5 - "Style() Logic"
Cohesion: 0.19
Nodes (26): compile_style(), Compile deterministic full-template overlays from an explicit base style., publish_style(), Publish a complete style using staging, validation, backup and rollback., _confirmed_profile(), Path, test_calibration_rejects_output_outside_tolerance(), test_calibration_tracks_hidden_mapping_and_updates_profile() (+18 more)

### Community 6 - "Lab.Py Logic"
Cohesion: 0.15
Nodes (13): _analysis_json(), parametrize, test_analyzer_fails_closed_on_malformed_output(), test_analyzer_fails_closed_when_all_quotes_are_invalid(), test_analyzer_normalizes_gemini_failure_without_retry_layer(), test_analyzer_preserves_untrusted_sample_and_ignores_injection(), test_analyzer_rejects_unbounded_batch_count_before_calling_gemini(), test_analyzer_uses_multi_pass_only_when_token_budget_requires() (+5 more)

### Community 7 - "Compiler.Py Logic"
Cohesion: 0.22
Nodes (12): _contract_object(), get_affected_agents(), _invariant_snapshot(), _load_base_skill(), Any, Normalize legacy scalar contracts into a JSON-safe object contract., _rules_for_dimension(), stable_skill_hash() (+4 more)

### Community 8 - "Migration.Py Logic"
Cohesion: 0.22
Nodes (12): import_existing_style(), migrate_profile_data(), _normalize_legacy_dna(), _normalize_legacy_evidence(), Any, Import an existing runtime style as a draft profile. A prior Voice Lab profile…, Pure, idempotent v1 adapter; current v2 contract stays fail-closed., test_current_profile_contract_rejects_extra_fields() (+4 more)

### Community 9 - "Coach Agent (Provocative) Logic"
Cohesion: 0.15
Nodes (13): Coach Agent (Provocative), Editor Agent (Provocative), Future Self (Provocative), Reader Experience (Provocative), Reflection Engine (Provocative), Story Architect (Provocative), Provocative Style, Writing Agent (Provocative) (+5 more)

### Community 10 - "Archive.Py Logic"
Cohesion: 0.27
Nodes (10): _checksum(), export_style(), import_style(), Any, Export a schema-v2 package with checksums for every payload file., Validate the whole package before optional extraction. Version 1 profiles are…, _safe_member(), test_archive_rejects_checksum_mismatch() (+2 more)

### Community 11 - "Compileresult Logic"
Cohesion: 0.18
Nodes (5): CompileResult, PublishRollbackError, RuntimeError, Publish failed and the previous runtime could not be restored., Exception

### Community 12 - "Mergeconflict Logic"
Cohesion: 0.27
Nodes (9): MergeConflict, MergeResult, apply_conflict_resolutions(), merge_overrides(), Any, Deterministic three-way merge; ambiguous changes remain explicit., Apply explicit user choices and revalidate Canonical IR + invariants., test_explicit_override_resolution_is_revalidated() (+1 more)

### Community 13 - "Reset() Logic"
Cohesion: 0.60
Nodes (5): test_session_state_initialization_and_mode_reset(), initialize_session_state(), Any, reset_voice_lab_state(), switch_mode()

### Community 16 - "Voice Lab Refactor Plan Logic"
Cohesion: 0.67
Nodes (3): Voice Lab Refactor Plan, Guided Style Voice Lab, Publish Safety Pipeline

### Community 17 - "Mindful Blog Workflow Logic"
Cohesion: 1.00
Nodes (3): Mindful Blog Workflow, Mindful Writing OS, Run Blog Workflow Prompt

### Community 18 - "Editor (Minh Hóm Hỉnh) Logic"
Cohesion: 1.00
Nodes (3): breath_editor (Minh hóm hỉnh), breath_editor (Reflective), breath_editor (VA Natural)

### Community 19 - "Reader (Minh Hóm Hỉnh) Logic"
Cohesion: 1.00
Nodes (3): cosmic_signal_reader (Minh hóm hỉnh), cosmic_signal_reader (Reflective), cosmic_signal_reader (VA Natural)

### Community 20 - "Witness (Minh Hóm Hỉnh) Logic"
Cohesion: 1.00
Nodes (3): gentle_witness (Minh hóm hỉnh), gentle_witness (Reflective), gentle_witness (VA Natural)

### Community 21 - "Weather (Minh Hóm Hỉnh) Logic"
Cohesion: 1.00
Nodes (3): inner_weather (Minh hóm hỉnh), inner_weather (Reflective), inner_weather (VA Natural)

### Community 22 - "Writer (Minh Hóm Hỉnh) Logic"
Cohesion: 1.00
Nodes (3): moment_writer (Minh hóm hỉnh), moment_writer (Reflective), moment_writer (VA Natural)

### Community 23 - "Capture (Minh Hóm Hỉnh) Logic"
Cohesion: 1.00
Nodes (3): sensory_capture (Minh hóm hỉnh), sensory_capture (Reflective), sensory_capture (VA Natural)

## Knowledge Gaps
- **55 isolated node(s):** `Project Agent Instructions`, `Agentic Workflow Architect`, `OpenAI Config`, `Architecture Invariants`, `Refactor Checklist` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_workflow()` connect `Datetime Logic` to `Learning.Py Logic`, `Title() Logic`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `StyleProfile` connect `Apptest Logic` to `Datetime Logic`, `Style() Logic`, `Lab.Py Logic`, `Compiler.Py Logic`, `Migration.Py Logic`, `Archive.Py Logic`, `Compileresult Logic`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `resolve_path()` connect `Datetime Logic` to `Learning.Py Logic`, `Compiler.Py Logic`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `ValueError` (e.g. with `build_client_map()` and `create_routing_client()`) actually correct?**
  _`ValueError` has 48 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Project Agent Instructions`, `Agentic Workflow Architect`, `OpenAI Config` to the rest of the system?**
  _55 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Datetime Logic` be split into smaller, more focused modules?**
  _Cohesion score 0.05111434108527132 - nodes in this community are weakly interconnected._
- **Should `Apptest Logic` be split into smaller, more focused modules?**
  _Cohesion score 0.05651296382549294 - nodes in this community are weakly interconnected._