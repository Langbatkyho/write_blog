import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.utils import load_yaml, read_text, resolve_path
from engine.workflow import run_workflow, run_learning_loop, resolve_workflow_file, resolve_step_skill_path


class TestMomentBlogMode(unittest.TestCase):

    def test_moment_blog_flow_contract(self) -> None:
        workflow = load_yaml(resolve_path("flow/write_moment_blog.yaml"))
        self.assertEqual(workflow["mode"], "moment")
        steps = workflow["steps"]
        step_ids = [step["id"] for step in steps]
        expected_ids = [
            "sensory_capture",
            "inner_weather",
            "cosmic_signal_reader",
            "moment_writer",
            "breath_editor",
            "gentle_witness",
        ]
        self.assertEqual(step_ids, expected_ids)

        outputs = {step["id"]: step["output"] for step in steps}
        self.assertEqual(outputs["moment_writer"], "moment_draft.md")
        self.assertEqual(outputs["breath_editor"], "moment_edited.md")
        self.assertEqual(outputs["gentle_witness"], "witness_report.md")

    def test_deep_blog_flow_contract(self) -> None:
        workflow = load_yaml(resolve_path("flow/write_blog.yaml"))
        self.assertEqual(workflow["mode"], "deep")
        steps = workflow["steps"]
        step_ids = [step["id"] for step in steps]
        self.assertEqual(len(step_ids), 7)
        self.assertEqual(step_ids[0], "story_architect")
        self.assertEqual(step_ids[-1], "future_self")

    def test_resolve_workflow_file(self) -> None:
        config = {}
        path_moment = resolve_workflow_file(config, mode="moment")
        self.assertTrue(path_moment.name, "write_moment_blog.yaml")

        path_deep = resolve_workflow_file(config, mode="deep")
        self.assertEqual(path_deep.name, "write_blog.yaml")

    def test_resolve_step_skill_path(self) -> None:
        moment_step = {"id": "sensory_capture", "skill": "skills/moment/reflective/sensory_capture.yaml"}
        skill_path = resolve_step_skill_path(moment_step, style="reflective", mode="moment")
        self.assertTrue(skill_path.exists())

        deep_step = {"id": "story_architect", "skill": "skills/story_architect.yaml"}
        deep_skill_path = resolve_step_skill_path(deep_step, style="reflective", mode="deep")
        self.assertTrue(deep_skill_path.exists())

    def test_dry_run_moment_mode(self) -> None:
        config_path = ROOT / "engine" / "config.example.yaml"
        input_path = ROOT / "examples" / "moment_blog_input_template.md"
        if not input_path.exists():
            input_path = ROOT / "examples" / "blog_input_template.md"

        run_dir = run_workflow(
            config_path=config_path,
            input_path=input_path,
            dry_run=True,
            style="reflective",
            mode="moment",
        )
        self.assertTrue(run_dir.exists())
        self.assertTrue((run_dir / "metadata.json").exists())

        metadata = json.loads(read_text(run_dir / "metadata.json"))
        self.assertEqual(metadata["mode"], "moment")
        self.assertEqual(metadata["style"], "reflective")

        # Verify output artifacts exist
        self.assertTrue((run_dir / "moment_edited.md").exists())
        self.assertTrue((run_dir / "witness_report.md").exists())

    def test_dry_run_deep_mode(self) -> None:
        config_path = ROOT / "engine" / "config.example.yaml"
        input_path = ROOT / "examples" / "blog_input_template.md"

        run_dir = run_workflow(
            config_path=config_path,
            input_path=input_path,
            dry_run=True,
            style="reflective",
            mode="deep",
        )
        self.assertTrue(run_dir.exists())
        metadata = json.loads(read_text(run_dir / "metadata.json"))
        self.assertEqual(metadata["mode"], "deep")
        self.assertTrue((run_dir / "edited_blog.md").exists())

    def test_same_input_both_modes(self) -> None:
        config_path = ROOT / "engine" / "config.example.yaml"
        input_path = ROOT / "examples" / "moment_blog_input_template.md"

        run_dir_deep = run_workflow(
            config_path=config_path,
            input_path=input_path,
            dry_run=True,
            style="reflective",
            mode="deep",
        )
        self.assertTrue(run_dir_deep.exists())
        self.assertTrue((run_dir_deep / "edited_blog.md").exists())

        run_dir_moment = run_workflow(
            config_path=config_path,
            input_path=input_path,
            dry_run=True,
            style="reflective",
            mode="moment",
        )
        self.assertTrue(run_dir_moment.exists())
        self.assertTrue((run_dir_moment / "moment_edited.md").exists())

    def test_offline_learning_loop_moment_mode(self) -> None:
        config_path = ROOT / "engine" / "config.example.yaml"
        input_path = ROOT / "examples" / "moment_blog_input_template.md"

        run_dir = run_workflow(
            config_path=config_path,
            input_path=input_path,
            dry_run=True,
            style="reflective",
            mode="moment",
        )
        # Create dummy production_blog.md and final_blog.md
        (run_dir / "final_blog.md").write_text("Khoảnh khắc mưa rơi nhè nhẹ trên phố.", encoding="utf-8")
        (run_dir / "production_blog.md").write_text("Khoảnh khắc mưa rơi nhè nhẹ trên đường phố cũ.", encoding="utf-8")

        learning_dir = run_learning_loop(
            config_path=config_path,
            run_dir=run_dir,
            dry_run=True,
            offline=True,
            mode="moment",
        )
        self.assertTrue(learning_dir.exists())
        self.assertTrue((learning_dir / "moment_blog_patterns.md").exists())
        report_text = read_text(learning_dir / "moment_blog_patterns.md")
        self.assertIn("MOMENT MODE", report_text)


if __name__ == "__main__":
    unittest.main()
