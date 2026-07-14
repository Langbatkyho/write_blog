import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.parser import build_context_package, parse_stage_response  # noqa: E402
from engine.workflow import derive_artifact_file_contents  # noqa: E402


class HandoffParserTest(unittest.TestCase):
    def test_parse_artifact_and_handoff_sections(self) -> None:
        response = """## Artifact

Full artifact body.

## Handoff

Compact handoff body.
"""
        artifact, handoff, used_fallback = parse_stage_response(response)

        self.assertEqual(artifact, "Full artifact body.")
        self.assertEqual(handoff, "Compact handoff body.")
        self.assertFalse(used_fallback)

    def test_missing_handoff_uses_fallback(self) -> None:
        artifact, handoff, used_fallback = parse_stage_response("Only artifact content.")

        self.assertEqual(artifact, "Only artifact content.")
        self.assertEqual(handoff, "Only artifact content.")
        self.assertTrue(used_fallback)

    def test_context_package_uses_policy(self) -> None:
        step = {
            "context_policy": {
                "handoffs": ["reflection_engine", "reader_experience"],
                "artifacts": ["writing_agent"],
            }
        }
        package = build_context_package(
            step,
            artifacts={"writing_agent": "draft"},
            handoffs={
                "reflection_engine": "reflection",
                "reader_experience": "reader",
                "story_architect": "story",
            },
        )

        self.assertEqual(
            package,
            {
                "handoffs": {
                    "reflection_engine": "reflection",
                    "reader_experience": "reader",
                },
                "artifacts": {"writing_agent": "draft"},
            },
        )

    def test_secondary_artifact_file_contents_are_split(self) -> None:
        skill = {
            "output": {
                "name": "edited_blog.md",
                "secondary_name": "edit_log.md",
            }
        }
        artifact = """## Edited Blog

Edited article body.

## Edit Log

- Merged two paragraphs.
"""

        contents = derive_artifact_file_contents(skill, artifact)

        self.assertEqual(contents["edited_blog.md"], "Edited article body.")
        self.assertEqual(contents["edit_log.md"], "- Merged two paragraphs.")

    def test_secondary_fallback_when_heading_missing(self) -> None:
        import warnings
        skill = {
            "output": {
                "name": "edited_blog.md",
                "secondary_name": "edit_log.md",
            }
        }
        artifact = "Just plain text without expected headings."
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            contents = derive_artifact_file_contents(skill, artifact)
            
            self.assertEqual(contents["edited_blog.md"], artifact)
            self.assertIn("not found", contents["edit_log.md"])
            self.assertEqual(len(w), 1)
            self.assertTrue("Could not split" in str(w[0].message))


if __name__ == "__main__":
    unittest.main()
