import json
from pathlib import Path
import zipfile

import pytest

from engine.cloud_stages import create_run, finalize_blog, prepare_stage, submit_stage
from engine.cloud_transfer import export_run, import_run
from engine.article_length import check_article_length


def test_moment_stage_resume_and_idempotency(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("title: Thử nghiệm\nraw_notes: Lá xanh.\n", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "runs", mode="moment", style="reflective")
    first = prepare_stage(run_dir, config)
    assert first["stage_id"] == "sensory_capture"
    assert prepare_stage(run_dir, config) == first
    response = "## Artifact\n\nLá xanh.\n\n## Handoff\n\nLá xanh được quan sát."
    assert submit_stage(run_dir, config, first["stage_id"], first["token"], response)["status"] == "running"
    assert submit_stage(run_dir, config, first["stage_id"], first["token"], response)["status"] == "already_completed"
    with pytest.raises(ValueError, match="different content"):
        submit_stage(run_dir, config, first["stage_id"], first["token"], response + " khác")
    second = prepare_stage(run_dir, config)
    assert second["stage_id"] == "inner_weather"
    with pytest.raises(ValueError, match="Stale or out-of-order"):
        submit_stage(run_dir, config, second["stage_id"], first["token"], response)
    assert (run_dir / "sensory_notes.md").read_text(encoding="utf-8") == "Lá xanh."


def test_cloud_editor_rejects_missing_edit_log(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("raw_notes: Thử nghiệm", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "runs")
    for _ in range(4):
        task = prepare_stage(run_dir, config)
        submit_stage(run_dir, config, task["stage_id"], task["token"], "## Artifact\n\nBản thử.\n\n## Handoff\n\nTóm tắt.")
    task = prepare_stage(run_dir, config)
    assert task["stage_id"] == "breath_editor"
    with pytest.raises(ValueError, match="Edit Log"):
        submit_stage(run_dir, config, task["stage_id"], task["token"], "## Artifact\n\nBản thử.\n\n## Handoff\n\nTóm tắt.")
    assert prepare_stage(run_dir, config) == task


def test_moment_six_stages_complete_without_provider(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("raw_notes: Mưa nhỏ.\ndesired_length: dưới 30 từ", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "runs")
    stages = []
    while True:
        task = prepare_stage(run_dir, config)
        if task.get("status") == "completed":
            break
        stages.append(task["stage_id"])
        artifact = (
            "## Edited Blog\n\n# Mưa\n\nMưa nhỏ.\n\n## Edit Log\n\nBỏ từ thừa."
            if task["stage_id"] == "breath_editor" else "Mưa nhỏ."
        )
        submit_stage(run_dir, config, task["stage_id"], task["token"], f"## Artifact\n\n{artifact}\n\n## Handoff\n\nMưa nhỏ.")
    assert len(stages) == 6
    assert (run_dir / "moment_edited.md").read_text(encoding="utf-8").startswith("# Mưa")
    assert (run_dir / "edit_log.md").read_text(encoding="utf-8") == "Bỏ từ thừa."
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["api_called"] is False
    assert set(metadata["contract_hashes"]) == set(stages) | {"flow"}
    log = (run_dir / "run_log.md").read_text(encoding="utf-8")
    assert "## sensory_capture Artifact" in log
    assert "## gentle_witness Handoff" in log
    assert not (run_dir / "final_blog.md").exists()
    approved_file = tmp_path / "approved.md"
    approved_file.write_text("# Mưa\n\nBản tác giả đã chọn.", encoding="utf-8")
    final_path = finalize_blog(run_dir, config, approved_file)
    assert final_path.read_text(encoding="utf-8") == "# Mưa\n\nBản tác giả đã chọn.\n"
    with pytest.raises(FileExistsError):
        finalize_blog(run_dir, config, approved_file)


def test_finalize_requires_author_input_and_completed_run(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("raw_notes: Mưa nhỏ.", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "runs")
    with pytest.raises(ValueError, match="Complete every stage"):
        finalize_blog(run_dir, config, author_input)
    assert not (run_dir / "final_blog.md").exists()


def test_moment_editor_rejects_295_words_before_witness(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("raw_notes: Mưa nhỏ.\ndesired_length:\n300-600 từ\n", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "runs")
    for _ in range(4):
        task = prepare_stage(run_dir, config)
        submit_stage(run_dir, config, task["stage_id"], task["token"], "## Artifact\n\nMưa nhỏ.\n\n## Handoff\n\nMưa.")
    task = prepare_stage(run_dir, config)
    assert task["stage_id"] == "breath_editor"
    short_article = " ".join(["mưa"] * 295)
    response = f"## Artifact\n\n## Edited Blog\n\n{short_article}\n\n## Edit Log\n\nRút gọn.\n\n## Handoff\n\nMưa."
    with pytest.raises(ValueError, match="295 words.*300–600"):
        submit_stage(run_dir, config, task["stage_id"], task["token"], response)
    assert prepare_stage(run_dir, config) == task
    assert not (run_dir / "moment_edited.md").exists()
    assert "breath_editor" not in json.loads((run_dir / "step_outputs.json").read_text(encoding="utf-8"))

    corrected = response.replace(short_article, short_article + " mưa" * 5)
    submit_stage(run_dir, config, task["stage_id"], task["token"], corrected)
    assert prepare_stage(run_dir, config)["stage_id"] == "gentle_witness"


@pytest.mark.parametrize("count,valid", [(295, False), (300, True), (600, True), (601, False)])
def test_moment_length_range_boundaries(count, valid):
    flow = {"mode": "moment", "input": {"desired_length": {"default": "300-600 words"}}}
    article = " ".join(["mưa"] * count)
    if valid:
        assert check_article_length(article, "raw_notes: Mưa", flow) == count
    else:
        with pytest.raises(ValueError, match=f"{count} words"):
            check_article_length(article, "raw_notes: Mưa", flow)


@pytest.mark.parametrize("count,valid", [(1199, False), (1200, True), (1800, True), (1801, False)])
def test_deep_length_range_boundaries(count, valid):
    flow = {"mode": "deep", "input": {"desired_length": {"default": "1200-1800 words"}}}
    article = " ".join(["mưa"] * count)
    if valid:
        assert check_article_length(article, "raw_notes: Mưa", flow) == count
    else:
        with pytest.raises(ValueError, match=f"Deep article has {count} words"):
            check_article_length(article, "raw_notes: Mưa", flow)


def test_deep_seven_stages_reader_prompt_and_editor_length_gate(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("title: Deep test\nraw_notes: PRIVATE_AUTHOR_NOTE\n", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "runs", mode="deep", style="reflective")
    stages = []
    while True:
        task = prepare_stage(run_dir, config)
        if task.get("status") == "completed":
            break
        stage = task["stage_id"]
        stages.append(stage)
        if stage == "reader_experience":
            assert "DRAFT_FOR_READER" in task["prompt"]
            assert "Final edited article length contract" not in task["prompt"]
            assert "PRIVATE_AUTHOR_NOTE" not in task["prompt"]
            assert "STORY_ONLY" not in task["prompt"]
            assert "REFLECTION_ONLY" not in task["prompt"]
        if stage == "writing_agent":
            assert "1200–1800 words" in task["prompt"]
        if stage == "editor_agent":
            short = "## Artifact\n\n## Edited Blog\n\nBản ngắn.\n\n## Edit Log\n\nGiữ giọng.\n\n## Handoff\n\nĐã sửa."
            with pytest.raises(ValueError, match="Deep article has 2 words.*1200–1800"):
                submit_stage(run_dir, config, stage, task["token"], short)
            assert not (run_dir / "edited_blog.md").exists()
            assert prepare_stage(run_dir, config) == task
            article = "## Opening\n\n" + " ".join(["mưa"] * 1199)
            artifact = f"## Edited Blog\n\n{article}\n\n## Edit Log\n\nGiữ giọng."
        else:
            artifact = {
                "story_architect": "STORY_ONLY",
                "reflection_engine": "REFLECTION_ONLY",
                "writing_agent": "DRAFT_FOR_READER",
            }.get(stage, "Phản hồi.")
        submit_stage(run_dir, config, stage, task["token"], f"## Artifact\n\n{artifact}\n\n## Handoff\n\nTóm tắt.")
    assert len(stages) == 7
    assert (run_dir / "edited_blog.md").read_text(encoding="utf-8") == "## Opening\n\n" + " ".join(["mưa"] * 1199)
    assert (run_dir / "edit_log.md").read_text(encoding="utf-8") == "Giữ giọng."
    assert json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))["status"] == "completed"
    approved = tmp_path / "approved.md"
    approved.write_text("# Tác giả duyệt\n\nBài cuối.\n", encoding="utf-8")
    assert finalize_blog(run_dir, config, approved).read_text(encoding="utf-8") == "# Tác giả duyệt\n\nBài cuối.\n"


@pytest.mark.parametrize("mode", ["moment", "deep"])
def test_cloud_create_rejects_unenforceable_length_before_creating_run(tmp_path, mode):
    author_input = tmp_path / "input.md"
    author_input.write_text("raw_notes: Mưa.\ndesired_length: khoảng một trang", encoding="utf-8")
    output_root = tmp_path / "runs"
    with pytest.raises(ValueError, match="Cannot enforce desired_length"):
        create_run(Path("engine/config.example.yaml"), author_input, output_root, mode=mode)
    assert not output_root.exists()


def test_export_import_resumes_in_new_root(tmp_path):
    config = Path("engine/config.example.yaml")
    author_input = tmp_path / "input.md"
    author_input.write_text("raw_notes: Mưa nhỏ.", encoding="utf-8")
    run_dir = create_run(config, author_input, tmp_path / "first")
    task = prepare_stage(run_dir, config)
    submit_stage(run_dir, config, task["stage_id"], task["token"], "## Artifact\n\nMưa.\n\n## Handoff\n\nMưa.")
    archive = export_run(run_dir, tmp_path / "transfer.zip")
    restored = import_run(archive, tmp_path / "second")
    assert prepare_stage(restored, config)["stage_id"] == "inner_weather"
    with pytest.raises(FileExistsError):
        import_run(archive, tmp_path / "second")


def test_import_rejects_corrupt_file_without_creating_run(tmp_path):
    archive = tmp_path / "broken.zip"
    run_id = "fixture_run"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("input.md", "tampered")
        bundle.writestr("metadata.json", "{}")
        bundle.writestr("step_outputs.json", "{}")
        bundle.writestr("_manifest.json", json.dumps({
            "format": 1, "run_id": run_id,
            "sha256": {name: "0" * 64 for name in ("input.md", "metadata.json", "step_outputs.json")},
        }))
    with pytest.raises(ValueError, match="checksum"):
        import_run(archive, tmp_path / "destination")
    assert not (tmp_path / "destination" / run_id).exists()
