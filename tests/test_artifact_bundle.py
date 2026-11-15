"""ART-1: bundle Claude Artifact và golden fixtures.

Mọi test ghi file đều dùng tmp_path; test lỗi chạy trên bản sao flow/ và skills/
trong tmp_path (patch engine.utils.ROOT), không chạm dữ liệu thật. Không gọi API.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine.utils  # noqa: E402
from artifact import build_bundle as bb  # noqa: E402
from artifact import make_golden  # noqa: E402
from artifact.claude_config import ClaudeConfigError, validate_claude_config  # noqa: E402
from engine.voice_lab.compiler import AGENT_FILENAME_MAP, REQUIRED_AGENTS, stable_skill_hash  # noqa: E402
from engine.workflow_context import build_step_prompt  # noqa: E402
from engine.workflow_resolution import resolve_step_skill_path  # noqa: E402


@pytest.fixture(scope="module")
def bundle() -> dict:
    return bb.build_bundle_content()


@pytest.fixture
def workspace(tmp_path, monkeypatch) -> Path:
    shutil.copytree(ROOT / "flow", tmp_path / "flow")
    shutil.copytree(ROOT / "skills", tmp_path / "skills")
    (tmp_path / "engine").mkdir()
    shutil.copy(ROOT / "engine" / "config.example.yaml", tmp_path / "engine" / "config.example.yaml")
    monkeypatch.setattr(engine.utils, "ROOT", tmp_path)
    return tmp_path


def _config(workspace: Path) -> Path:
    return workspace / "engine" / "config.example.yaml"


def _edit_yaml(path: Path, mutate) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# --- AC2: tất định -----------------------------------------------------------

def test_bundle_build_is_deterministic(tmp_path):
    first_hash, first = bb.build_bundle(out_path=tmp_path / "a.json")
    second_hash, second = bb.build_bundle(out_path=tmp_path / "b.json")
    assert first_hash == second_hash
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8"))["content_hash"] == first_hash


# --- Nội dung bundle ----------------------------------------------------------

def test_bundle_contains_every_system_style(bundle):
    styles = bundle["styles"]
    assert sorted(styles["deep"]) == ["provocative", "reflective"]
    assert sorted(styles["moment"]) == ["minh-hom-hinh", "reflective", "va-natural"]
    for mode, by_slug in styles.items():
        expected_files = set(bundle["workflows"][mode]["stage_files"].values())
        for slug, style in by_slug.items():
            assert style["system"] is True
            assert style["meta"]["slug"] == slug
            assert set(style["files"]) == expected_files
            for entry in style["files"].values():
                assert entry["yaml"] == bb.dump_yaml(entry["data"])
                assert entry["base_hash"] == stable_skill_hash(entry["data"])
    assert styles["deep"]["reflective"]["meta"]["is_protected"] is True
    assert styles["moment"]["va-natural"]["meta"]["base_style_slug"] == "reflective"


def test_bundle_yaml_is_embedded_verbatim_in_engine_prompt(bundle):
    workflow = bundle["workflows"]["deep"]["definition"]
    step = next(s for s in workflow["steps"] if s["id"] == "writing_agent")
    skill = engine.utils.load_yaml(resolve_step_skill_path(step, "reflective", "deep"))
    prompt = build_step_prompt(workflow, step, skill, "input", {"handoffs": {}, "artifacts": {}})
    assert bundle["styles"]["deep"]["reflective"]["files"]["writing_agent.yaml"]["yaml"] in prompt


def test_bundle_models_cover_every_stage_with_tier(bundle):
    models = bundle["models"]
    stage_ids = bundle["workflows"]["deep"]["stage_ids"] + bundle["workflows"]["moment"]["stage_ids"]
    assert sorted(models["stages"]) == sorted(stage_ids)
    assert list(models["learning"]) == ["editorial_learning", "workflow_tuning"]
    assert list(models["voice_lab"]) == ["vl_analysis", "vl_synthesis", "vl_interview_patch", "vl_calibration"]
    tiers = {"claude-haiku-5-5": "quick", "claude-sonnet-5-5": "default", "claude-opus-5-5": "complex"}
    for group in models.values():
        for entry in group.values():
            assert entry["model_tier"] == tiers[entry["model"]]
            assert entry["effort"] in {"low", "medium", "high"}
    assert models["stages"]["writing_agent"] == {"model": "claude-opus-5-5", "effort": "high", "model_tier": "complex"}
    assert bundle["model_catalog"] == {"models": tiers, "efforts": ["low", "medium", "high"]}


def test_bundle_voice_lab_constants_match_engine(bundle):
    vl = bundle["voice_lab"]
    assert vl["schema_version"] == 2
    assert len(vl["dimensions"]) == 12
    assert vl["agent_filename_map"] == AGENT_FILENAME_MAP
    assert vl["required_agents"] == REQUIRED_AGENTS
    for name in ("analysis_payload", "synthesis_payload", "interview_patch_payload", "calibration_payload", "style_profile"):
        assert vl["schemas"][name]["type"] == "object"
    assert vl["calibration"]["min_words"] < vl["calibration"]["max_words"]
    # ART-8.1: nhãn tiếng Việt, tham số chia mẫu và chuỗi schema dựng sẵn cho prompt.
    from engine.voice_lab import analyzer as vl_analyzer
    from engine.voice_lab.interview_routing import DIMENSION_VI
    from engine.voice_lab.overrides import IR_LEVEL_INVARIANTS

    assert vl["dimension_labels"] == DIMENSION_VI
    assert vl["analysis"]["chunk_overlap_chars"] == vl_analyzer.CHUNK_OVERLAP_CHARS
    assert vl["analysis"]["max_analysis_batches"] == vl_analyzer.MAX_ANALYSIS_BATCHES
    assert vl["ir_level_invariants"] == sorted(IR_LEVEL_INVARIANTS)
    for name, schema in vl["schemas"].items():
        assert vl["schema_texts"][name] == json.dumps(schema, ensure_ascii=False)
    assert '"maximum": 1.0' in vl["schema_texts"]["analysis_payload"]


def test_bundle_base_hash_matches_compiler_golden(bundle):
    golden = json.loads((make_golden.GOLDEN_DIR / "voicelab_logic.json").read_text(encoding="utf-8"))
    case = next(c for c in golden["compile"] if c["name"] == "deep_full")
    files = bundle["styles"]["deep"]["reflective"]["files"]
    for filename, artifact in case["result"]["artifacts"].items():
        assert artifact["base_hash"] == files[filename]["base_hash"]


# --- AC3: fail-closed ---------------------------------------------------------

def test_missing_skill_file_fails(workspace):
    (workspace / "skills" / "moment" / "va-natural" / "inner_weather.yaml").unlink()
    with pytest.raises(bb.BundleBuildError, match="va-natural.*inner_weather"):
        bb.build_bundle_content(_config(workspace))


def test_flow_skill_output_mismatch_fails(workspace):
    _edit_yaml(
        workspace / "skills" / "deep" / "provocative" / "coach_agent.yaml",
        lambda d: d["output"].update({"name": "sai_ten.md"}),
    )
    with pytest.raises(bb.BundleBuildError, match="provocative.*sai_ten.md"):
        bb.build_bundle_content(_config(workspace))


def test_invalid_style_slug_directory_fails(workspace):
    shutil.copytree(workspace / "skills" / "moment" / "reflective", workspace / "skills" / "moment" / "Bad_Slug")
    with pytest.raises(bb.BundleBuildError, match="Bad_Slug"):
        bb.build_bundle_content(_config(workspace))


def test_unknown_base_style_fails(workspace):
    _edit_yaml(workspace / "skills" / "moment" / "va-natural" / "style_meta.yaml", lambda d: d.update({"base_style_slug": "khong-co"}))
    with pytest.raises(bb.BundleBuildError, match="khong-co"):
        bb.build_bundle_content(_config(workspace))


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda c: c["claude"]["stages"].pop("gentle_witness"), "thiếu gentle_witness"),
        (lambda c: c["claude"]["stages"].update({"gentle_witnes": {"model": "claude-opus-5-5", "effort": "low"}}), "thừa gentle_witnes"),
        (lambda c: c["claude"]["stages"]["writing_agent"].update({"model": "claude-opsu-5-5"}), "chưa được kiểm chứng"),
        (lambda c: c["claude"]["stages"]["writing_agent"].update({"effort": "max"}), "effort"),
        (lambda c: c["claude"]["voice_lab"].pop("vl_calibration"), "thiếu vl_calibration"),
        (lambda c: c.pop("claude"), "thiếu khối"),
    ],
)
def test_invalid_claude_config_fails(workspace, mutate, message):
    _edit_yaml(_config(workspace), mutate)
    with pytest.raises(ClaudeConfigError, match=message):
        bb.build_bundle_content(_config(workspace))


def test_claude_config_rejects_non_mapping():
    with pytest.raises(ClaudeConfigError):
        validate_claude_config(["không phải object"], workflow_stage_ids=["a"])


@pytest.mark.parametrize("broken", [lambda: (_ for _ in ()).throw(RuntimeError("hỏng")), lambda: None, lambda: {"type": "string"}])
def test_schema_export_failure_fails(monkeypatch, broken):
    monkeypatch.setitem(bb.SCHEMA_EXPORTS, "analysis_payload", broken)
    with pytest.raises(bb.BundleBuildError, match="analysis_payload"):
        bb.build_bundle_content()


def test_cli_reports_failure_without_writing(workspace, tmp_path, capsys):
    (workspace / "skills" / "deep" / "reflective" / "future_self.yaml").unlink()
    out = tmp_path / "out" / "bundle.json"
    assert bb.main(["--config", str(_config(workspace)), "--out", str(out)]) == 1
    assert "Build thất bại" in capsys.readouterr().err
    assert not out.exists()


# --- O-05: golden khớp engine hiện tại ----------------------------------------

def test_golden_fixtures_are_up_to_date():
    rendered = make_golden.render_all()
    stale = [
        name
        for name, text in rendered.items()
        if (make_golden.GOLDEN_DIR / name).read_text(encoding="utf-8") != text
    ]
    assert not stale, f"Golden đã cũ, chạy `python artifact/make_golden.py`: {stale}"


def test_learning_templates_are_generated_from_engine():
    from artifact import gen_learning_templates

    assert gen_learning_templates.TARGET.read_text(encoding="utf-8") == gen_learning_templates.render(), (
        "learning_templates.js đã cũ, chạy `python artifact/gen_learning_templates.py`"
    )
