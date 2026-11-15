import json
from pathlib import Path
import zipfile

import pytest

from engine.cloud_stages import create_run, finalize_blog, prepare_stage, submit_stage
from engine.cloud_transfer import export_run, import_run


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
    author_input.write_text("raw_notes: Mưa nhỏ.", encoding="utf-8")
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
