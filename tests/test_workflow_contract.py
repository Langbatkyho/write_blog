import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8-sig"))


class WorkflowContractTest(unittest.TestCase):
    def test_editorial_workflow_order_and_outputs(self) -> None:
        workflow = load_yaml("flow/write_blog.yaml")
        steps = workflow["steps"]

        self.assertEqual(
            [step["id"] for step in steps],
            [
                "story_architect",
                "reflection_engine",
                "writing_agent",
                "reader_experience",
                "editor_agent",
                "coach_agent",
                "future_self",
            ],
        )
        outputs = {step["id"]: step["output"] for step in steps}
        self.assertEqual(outputs["editor_agent"], "edited_blog.md")
        self.assertEqual(outputs["future_self"], "future_reflection.md")
        self.assertNotIn("final_blog.md", outputs.values())

    def test_reader_experience_is_blind_review(self) -> None:
        workflow = load_yaml("flow/write_blog.yaml")
        reader_step = next(step for step in workflow["steps"] if step["id"] == "reader_experience")

        self.assertEqual(reader_step["context_policy"]["handoffs"], [])
        self.assertEqual(reader_step["context_policy"]["artifacts"], ["writing_agent"])

        reader_skill = load_yaml("skills/reader_experience.yaml")
        self.assertIn("Never edit", reader_skill["supreme_rule"])
        self.assertIn("Never diagnose", reader_skill["supreme_rule"])
        self.assertNotIn("suggested_revisions", str(reader_skill))

    def test_editor_agent_has_secondary_edit_log(self) -> None:
        editor_skill = load_yaml("skills/editor_agent.yaml")

        self.assertEqual(editor_skill["output"]["name"], "edited_blog.md")
        self.assertEqual(editor_skill["output"]["secondary_name"], "edit_log.md")
        self.assertIn("## Edit Log", editor_skill["output"]["artifact"]["required_sections"])


if __name__ == "__main__":
    unittest.main()
