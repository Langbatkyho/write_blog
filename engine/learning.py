import difflib
import textwrap
from typing import Any
import yaml

from engine.utils import load_yaml, resolve_path
from engine.parser import count_words, count_paragraphs, average_sentence_words

def build_learning_prompt(
    workflow: dict[str, Any],
    skills: dict[str, dict[str, Any]],
    author_input: str,
    step_outputs: dict[str, str],
    final_blog: str,
    production_blog: str,
    comparison_label: str = "final_blog.md",
    mode: str = "deep",
) -> str:
    learning_skill = load_yaml(resolve_path("skills/editorial_learning.yaml"))
    skills_yaml = yaml.safe_dump(skills, allow_unicode=True, sort_keys=False)
    workflow_yaml = yaml.safe_dump(workflow, allow_unicode=True, sort_keys=False)
    step_outputs_block = "\n\n".join(
        f"## {name}\n\n{content}" for name, content in step_outputs.items()
    )

    return textwrap.dedent(
        f"""
        You are running the learning loop for an automated reflective blog workflow.
        Writing Mode: {mode}

        Learning skill YAML:
        ```yaml
        {yaml.safe_dump(learning_skill, allow_unicode=True, sort_keys=False)}
        ```

        Workflow YAML:
        ```yaml
        {workflow_yaml}
        ```

        Skill YAML files:
        ```yaml
        {skills_yaml}
        ```

        Original author input:
        ```markdown
        {author_input}
        ```

        Workflow step outputs:
        ```markdown
        {step_outputs_block}
        ```

        AI-supported comparison draft ({comparison_label}):
        ```markdown
        {final_blog}
        ```

        Human-edited production_blog.md:
        ```markdown
        {production_blog}
        ```

        Instructions:
        - Follow the Learning skill YAML strictly.
        - Produce a practical markdown report for improving the workflow for writing mode: {mode}.
        - Focus on what the human editor changed and what the workflow should learn.
        - Give stage-by-stage insights for every workflow stage in this mode.
        - Include suggested YAML changes as concise bullets, not full rewritten files.
        - Do not rewrite the blog post.
        - Do not include hidden reasoning.
        """
    ).strip()

def build_tuning_prompt(report: str, mode: str = "deep") -> str:
    if mode == "moment":
        stages_list = "sensory_capture, inner_weather, cosmic_signal_reader, moment_writer, breath_editor, gentle_witness"
    else:
        stages_list = "story_architect, reflection_engine, writing_agent, reader_experience, editor_agent, coach_agent, future_self"

    return textwrap.dedent(
        f"""
        Turn this editorial learning report for mode '{mode}' into concise workflow tuning suggestions.

        Editorial learning report:
        ```markdown
        {report}
        ```

        Output a markdown document with:
        - one section for each workflow stage in mode '{mode}':
          {stages_list}
        - concrete YAML or prompt-rule changes for that stage
        - expected effect of each change
        - confidence: high, medium, or low

        Do not rewrite the blog post.
        Do not include hidden reasoning.
        """
    ).strip()

def render_offline_diff(final_blog: str, production_blog: str, comparison_label: str = "final_blog.md") -> str:
    final_lines = final_blog.splitlines()
    production_lines = production_blog.splitlines()
    diff_lines = difflib.unified_diff(
        final_lines,
        production_lines,
        fromfile=comparison_label,
        tofile="production_blog.md",
        lineterm="",
    )
    diff = "\n".join(diff_lines)
    return diff if diff.strip() else "No line-level differences detected."

def build_offline_learning_report(
    final_blog: str,
    production_blog: str,
    step_outputs: dict[str, str],
    comparison_label: str = "final_blog.md",
    mode: str = "deep",
) -> str:
    final_words = count_words(final_blog)
    production_words = count_words(production_blog)
    word_delta = production_words - final_words
    final_paragraphs = count_paragraphs(final_blog)
    production_paragraphs = count_paragraphs(production_blog)
    paragraph_delta = production_paragraphs - final_paragraphs
    final_sentence_avg = average_sentence_words(final_blog)
    production_sentence_avg = average_sentence_words(production_blog)
    similarity = difflib.SequenceMatcher(None, final_blog, production_blog).ratio()
    diff = render_offline_diff(final_blog, production_blog, comparison_label=comparison_label)

    if word_delta < 0:
        length_note = "The production version is shorter, suggesting the human edit may have removed excess explanation or tightened rhythm."
    elif word_delta > 0:
        length_note = "The production version is longer, suggesting the human edit may have added context, emotional detail, or connective tissue."
    else:
        length_note = "The production version has the same word count, so the main learning is likely in phrasing, structure, or emphasis."

    if production_sentence_avg < final_sentence_avg:
        rhythm_note = "Average sentence length went down, suggesting a preference for shorter breath and clearer pauses."
    elif production_sentence_avg > final_sentence_avg:
        rhythm_note = "Average sentence length went up, suggesting a preference for more developed reflection or smoother flow."
    else:
        rhythm_note = "Average sentence length stayed similar."

    available_steps = ", ".join(step_outputs.keys()) or "No step outputs found"

    if mode == "moment":
        stage_insights = textwrap.dedent("""
            ### sensory_capture
            Check whether production edits preserved authentic concrete observations or added unverified details.

            ### inner_weather
            Check whether production edits changed emotional naming or added clinical/spiritual theory.

            ### cosmic_signal_reader
            Check whether the small intuitive signal was kept, trimmed, or expanded into a major lecture.

            ### moment_writer
            Check whether production edits shortened sentence length or removed past-tense reflection to keep present energy.

            ### breath_editor
            Check whether production edits simplified heavy sentences further or over-polished the prose.

            ### gentle_witness
            Check whether the witness report accurately flagged forced moments or preachiness.
        """).strip()
    else:
        stage_insights = textwrap.dedent("""
            ### story_architect
            Check whether production edits changed the opening, reordered sections, or moved the emotional turn.

            ### reflection_engine
            Check whether production edits added uncertainty, removed premature certainty, or deepened a hidden tension.

            ### writing_agent
            Check whether production edits shortened paragraphs, changed pronouns, removed generic phrasing, or added more lived detail.

            ### reader_experience
            Check whether the reader diary captured where attention, trust, or connection changed.

            ### editor_agent
            Check whether production edits repeated, contradicted, or improved the editor_agent changes.

            ### coach_agent
            Check whether production edits answered a deeper question that the coaching report did not ask.

            ### future_self
            Check whether production edits followed or ignored future_reflection.md.
        """).strip()

    return textwrap.dedent(
        f"""
        # Offline Editorial Learning Report ({mode.upper()} MODE)

        This report was generated without calling the OpenAI API. It uses local text comparison to analyze differences.

        ## Executive Summary

        - Mode: {mode}
        - Similarity score: {similarity:.3f}
        - {comparison_label} word count: {final_words}
        - production_blog.md word count: {production_words}
        - Word delta: {word_delta:+d}
        - Paragraph delta: {paragraph_delta:+d}
        - Average sentence words, {comparison_label}: {final_sentence_avg:.2f}
        - Average sentence words, production: {production_sentence_avg:.2f}

        {length_note}

        {rhythm_note}

        ## Available Workflow Context

        Step outputs found: {available_steps}

        ## Stage-by-Stage Offline Insights

        {stage_insights}

        ## Local Diff

        ```diff
        {diff}
        ```
        """
    ).strip()

def build_offline_tuning_suggestions(report: str, mode: str = "deep") -> str:
    if mode == "moment":
        suggestions_body = textwrap.dedent("""
            ## sensory_capture
            - Check: "Did human edit keep concrete observations without inferring hidden meaning?"
            - Expected effect: cleaner sensory baseline.
            - Confidence: high

            ## inner_weather
            - Check: "Did human edit simplify internal weather naming?"
            - Expected effect: avoids clinical or over-analytical tone.
            - Confidence: medium

            ## cosmic_signal_reader
            - Check: "Was the intuitive signal modest and grounded?"
            - Expected effect: prevents cosmic signal from becoming preachy advice.
            - Confidence: high

            ## moment_writer
            - Check: "Did human edit shorten sentences to preserve present-moment breath?"
            - Expected effect: more natural short-form cadence.
            - Confidence: high

            ## breath_editor
            - Check: "Did editor trim without adding new ideas?"
            - Expected effect: keeps moment under target word limit (300-600 words).
            - Confidence: high

            ## gentle_witness
            - Check: "Did witness report accurately identify any didactic tone?"
            - Expected effect: reinforces calm verification without triggering loops.
            - Confidence: medium
        """).strip()
    else:
        suggestions_body = textwrap.dedent("""
            ## story_architect
            - Add a review question: "Did the production edit move the real beginning of the story?"
            - Expected effect: better opening selection.
            - Confidence: medium

            ## reflection_engine
            - Add a review question: "Did the production edit delay or soften an insight?"
            - Expected effect: less premature meaning-making.
            - Confidence: medium

            ## writing_agent
            - Compare paragraph length and sentence length against production edits before accepting future drafts.
            - Expected effect: closer rhythm to the author's edited voice.
            - Confidence: high

            ## reader_experience
            - Keep this stage as a blind reader diary with no diagnosis or recommendations.
            - Expected effect: cleaner signal for editor_agent.
            - Confidence: high

            ## editor_agent
            - Compare edit_log.md against production edits and add recurring human edit choices as minimum-edit rules.
            - Expected effect: fewer unnecessary rewrites and better reader connection.
            - Confidence: medium

            ## coach_agent
            - Read edited_blog.md instead of draft_blog.md so coaching focuses on the writer's blind spots, not prose cleanup.
            - Expected effect: deeper coaching questions.
            - Confidence: medium

            ## future_self
            - Keep this stage reflective only; it should identify decisions for the human writer, not rewrite final_blog.md.
            - Expected effect: clearer human ownership of the final version.
            - Confidence: medium
        """).strip()

    return textwrap.dedent(
        f"""
        # Offline Workflow Tuning Suggestions ({mode.upper()} MODE)

        These suggestions were generated without OpenAI API access for mode '{mode}'.

        {suggestions_body}

        ## Source Report

        See `editorial_learning_report.md` for metrics and diff details.
        """
    ).strip()
