import json
from pathlib import Path
import zipfile

import pytest

from engine.cloud_stages import create_run, finalize_blog, prepare_stage, submit_stage, verify_run, recover_run
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
    assert metadata["protocol_version"] == 2
    assert len(metadata["runtime_sha256"]) == 64
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
    assert finalize_blog(run_dir, config, approved_file) == final_path
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["author_approval"]["final_sha256"]
    assert "## Author Approval" in (run_dir / "run_log.md").read_text(encoding="utf-8")


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


@pytest.mark.parametrize("failure_point", ["artifact", "checkpoint", "log", "metadata"])
def test_recover_interrupted_last_stage(tmp_path, monkeypatch, failure_point):
    import engine.cloud_stages as cloud
    from engine.workflow_persistence import RunRepository

    config = Path("engine/config.example.yaml")
    source = tmp_path / "input.md"
    source.write_text("raw_notes: Mưa.\ndesired_length: dưới 30 từ", encoding="utf-8")
    run = create_run(config, source, tmp_path / "runs")
    response = "## Artifact\n\nMưa.\n\n## Handoff\n\nMưa."
    for _ in range(6):
        task = prepare_stage(run, config)
        current = ("## Artifact\n\n## Edited Blog\n\nMưa.\n\n## Edit Log\n\nSửa.\n\n## Handoff\n\nMưa."
                   if task["stage_id"] == "breath_editor" else response)
        if task["stage_id"] == "gentle_witness":
            original = {
                "artifact": RunRepository.write_artifact,
                "checkpoint": RunRepository.write_internal,
                "log": cloud.atomic_write_text,
                "metadata": RunRepository.write_metadata,
            }[failure_point]
            def fail_once(*args, **kwargs):
                monkeypatch.setattr(RunRepository if failure_point != "log" else cloud,
                                    {"artifact": "write_artifact", "checkpoint": "write_internal", "log": "atomic_write_text", "metadata": "write_metadata"}[failure_point], original)
                raise OSError("injected interruption")
            monkeypatch.setattr(RunRepository if failure_point != "log" else cloud,
                                {"artifact": "write_artifact", "checkpoint": "write_internal", "log": "atomic_write_text", "metadata": "write_metadata"}[failure_point], fail_once)
            with pytest.raises(OSError, match="injected interruption"):
                submit_stage(run, config, task["stage_id"], task["token"], current)
            report = verify_run(run, config)
            if failure_point in {"artifact", "checkpoint"}:
                assert report["status"] == "ok"
                submit_stage(run, config, task["stage_id"], task["token"], current)
            else:
                assert report["status"] == "needs_recovery"
                with pytest.raises(ValueError, match="needs recovery"):
                    prepare_stage(run, config)
                assert recover_run(run, config)["status"] == "ok"
            break
        submit_stage(run, config, task["stage_id"], task["token"], current)
    assert prepare_stage(run, config) == {"status": "completed"}
    approved = tmp_path / "approved.md"
    approved.write_text("Mưa.", encoding="utf-8")
    assert finalize_blog(run, config, approved).exists()


def test_recovery_does_not_overwrite_conflicting_log(tmp_path):
    config = Path("engine/config.example.yaml")
    source = tmp_path / "input.md"
    source.write_text("raw_notes: Mưa.", encoding="utf-8")
    run = create_run(config, source, tmp_path / "runs")
    task = prepare_stage(run, config)
    submit_stage(run, config, task["stage_id"], task["token"], "## Artifact\n\nMưa.\n\n## Handoff\n\nMưa.")
    (run / "run_log.md").write_text("Human content", encoding="utf-8")
    assert verify_run(run, config)["conflicts"] == ["run_log.md"]
    with pytest.raises(ValueError, match="conflicts"):
        recover_run(run, config)
    assert (run / "run_log.md").read_text(encoding="utf-8") == "Human content"


def test_recovery_can_resume_after_its_own_interruption(tmp_path, monkeypatch):
    import engine.cloud_stages as cloud
    config = Path("engine/config.example.yaml")
    source = tmp_path / "input.md"
    source.write_text("raw_notes: Mưa.", encoding="utf-8")
    run = create_run(config, source, tmp_path / "runs")
    task = prepare_stage(run, config)
    submit_stage(run, config, task["stage_id"], task["token"], "## Artifact\n\nMưa.\n\n## Handoff\n\nMưa.")
    (run / "sensory_notes.md").unlink()
    (run / "sensory_handoff.md").unlink()
    original = cloud.atomic_write_text
    def fail_once(*args, **kwargs):
        monkeypatch.setattr(cloud, "atomic_write_text", original)
        raise OSError("recover interrupted")
    monkeypatch.setattr(cloud, "atomic_write_text", fail_once)
    with pytest.raises(OSError, match="recover interrupted"):
        recover_run(run, config)
    assert recover_run(run, config)["status"] == "ok"


def test_v2_detects_input_and_checkpoint_tampering(tmp_path):
    config = Path("engine/config.example.yaml")
    source = tmp_path / "input.md"
    source.write_text("raw_notes: Mưa.", encoding="utf-8")
    run = create_run(config, source, tmp_path / "runs")
    task = prepare_stage(run, config)
    submit_stage(run, config, task["stage_id"], task["token"], "## Artifact\n\nMưa.\n\n## Handoff\n\nMưa.")
    checkpoint = run / "step_outputs.json"
    original = checkpoint.read_text(encoding="utf-8")
    checkpoint.write_text(original.replace('"artifact": "Mưa."', '"artifact": "Giả."'), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_run(run, config)
    checkpoint.write_text(original, encoding="utf-8")
    (run / "input.md").write_text("raw_notes: Khác.", encoding="utf-8")
    with pytest.raises(ValueError, match="Input checksum mismatch"):
        verify_run(run, config)


def test_finalize_resumes_after_file_or_log_interruption(tmp_path, monkeypatch):
    import engine.cloud_stages as cloud
    from engine.workflow_persistence import RunRepository
    config = Path("engine/config.example.yaml")
    source = tmp_path / "input.md"
    source.write_text("raw_notes: Mưa.\ndesired_length: dưới 30 từ", encoding="utf-8")
    run = create_run(config, source, tmp_path / "runs")
    while (task := prepare_stage(run, config)).get("stage_id"):
        artifact = "## Edited Blog\n\nMưa.\n\n## Edit Log\n\nSửa." if task["stage_id"] == "breath_editor" else "Mưa."
        submit_stage(run, config, task["stage_id"], task["token"], f"## Artifact\n\n{artifact}\n\n## Handoff\n\nMưa.")
    approved = tmp_path / "approved.md"
    approved.write_text("Tác giả duyệt.", encoding="utf-8")
    stage_log = (run / "run_log.md").read_text(encoding="utf-8")
    original = RunRepository.write_metadata
    def fail_receipt(*args, **kwargs):
        monkeypatch.setattr(RunRepository, "write_metadata", original)
        raise OSError("receipt interrupted")
    monkeypatch.setattr(RunRepository, "write_metadata", fail_receipt)
    with pytest.raises(OSError, match="receipt interrupted"):
        finalize_blog(run, config, approved)
    assert (run / "final_blog.md").exists()
    assert finalize_blog(run, config, approved).exists()
    assert verify_run(run, config)["status"] == "ok"
    (run / "run_log.md").write_text(stage_log, encoding="utf-8")
    assert verify_run(run, config)["stale"] == ["run_log.md"]
    assert recover_run(run, config)["status"] == "ok"
    other = tmp_path / "other.md"
    other.write_text("Bản khác.", encoding="utf-8")
    with pytest.raises(ValueError, match="Different article"):
        finalize_blog(run, config, other)


def test_export_rejects_inconsistent_run(tmp_path):
    config = Path("engine/config.example.yaml")
    source = tmp_path / "input.md"
    source.write_text("raw_notes: Mưa.", encoding="utf-8")
    run = create_run(config, source, tmp_path / "runs")
    (run / "run_log.md").write_text("corrupt", encoding="utf-8")
    archive = tmp_path / "run.zip"
    with pytest.raises(ValueError, match="needs recovery"):
        export_run(run, archive)
    assert not archive.exists()
