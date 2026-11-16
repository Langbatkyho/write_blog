---
name: mindful-moment-writing
description: Run the write_blog Moment workflow in Codex Cloud for an author's real notes, using an existing style and preserving each stage's artifact and handoff.
---

Use the repository's `flow/write_moment_blog.yaml` and stage YAML files as the source of truth. Read `AGENTS.md` and `.agents/AGENTS.md` before creating a run. The author chooses the final article.

1. Get the author's input and style. Use `python -m engine.cloud_stage_cli create --input <path> --output-root <safe-persistent-or-exportable-root> --style <style>`. Never use `examples/` as real user input.
2. Call `python -m engine.cloud_stage_cli prepare --run-dir <run_dir>`. It returns the next stage, an opaque token, and its complete prompt. Give only that prompt to a fresh subagent. Wait for its response before continuing.
3. Save the response to a UTF-8 file belonging to this attempt. Call `python -m engine.cloud_stage_cli submit --run-dir <run_dir> --stage-id <stage_id> --token <token> --response-file <path>`.
4. Repeat prepare and submit until prepare returns `completed`. If interrupted, prepare the same run again; it will select the next unfinished stage. Do not edit completed stage outputs.
5. Check the article's actual word count with `engine.parser.count_words()` and compare it with the input's `desired_length`; use the code's count over any claim in `witness_report.md`. New runs reject an out-of-range `breath_editor` response at submit, before saving its artifact. For a run completed by older code, report a mismatch clearly and do not rewrite completed stage files. Present `moment_edited.md` and `witness_report.md` to the author for review. Once the author selects or edits the article, save that approved text in a separate file and call `python -m engine.cloud_stage_cli finalize --run-dir <run_dir> --approved-file <path>`. Return `final_blog.md` and `run_log.md` as two individual downloadable files.
6. For resuming a run in another Cloud task, export with `python -m engine.cloud_stage_cli export --run-dir <run_dir> --archive <archive.zip>`. In the new task, import with `python -m engine.cloud_stage_cli import --archive <archive.zip> --output-root <root>`. The user must transfer the ZIP between tasks; the two final Markdown files do not contain the checkpoint.

Subagents share workspace access. Treat the prompt boundary as context control, not a file permission boundary. Keep this workflow sequential.
