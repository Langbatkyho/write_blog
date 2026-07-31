import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.parser import (  # noqa: E402
    StageResponseError,
    build_context_package,
    parse_stage_response,
)
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

    def test_strict_parser_accepts_exact_contract(self) -> None:
        response = """## Artifact

Nội dung đầy đủ.

### Chi tiết hợp lệ

Một mục con.

## Tiêu đề H2 thuộc Artifact

Nội dung bài viết.

## Handoff

Tóm tắt bàn giao.
"""
        artifact, handoff, used_fallback = parse_stage_response(
            response, strict=True
        )
        self.assertIn("### Chi tiết hợp lệ", artifact)
        self.assertIn("## Tiêu đề H2 thuộc Artifact", artifact)
        self.assertEqual(handoff, "Tóm tắt bàn giao.")
        self.assertFalse(used_fallback)

    def test_strict_parser_rejects_extra_duplicate_or_reordered_sections(self) -> None:
        invalid_responses = (
            """## Artifact
A
## Artifact
B
## Handoff
H
""",
            """## Handoff
H
## Artifact
A
""",
            """## Artifact
A
## Handoff
H
## Handoff
H2
""",
            """Preamble
## Artifact
A
## Handoff
H
""",
        )
        for response in invalid_responses:
            with self.subTest(response=response):
                with self.assertRaises(StageResponseError):
                    parse_stage_response(response, strict=True)

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

    def test_secondary_artifact_keeps_internal_blog_headings(self) -> None:
        skill = {
            "output": {
                "name": "edited_blog.md",
                "secondary_name": "edit_log.md",
            }
        }
        artifact = """## Edited Blog

# Kết nối

## Nơi mình thuộc về

Edited article section.

## Vẫn đi tiếp

Another edited article section.

## Edit Log

- Merged two paragraphs.
"""

        contents = derive_artifact_file_contents(skill, artifact)

        self.assertIn("## Nơi mình thuộc về", contents["edited_blog.md"])
        self.assertIn("## Vẫn đi tiếp", contents["edited_blog.md"])
        self.assertNotIn("## Edit Log", contents["edited_blog.md"])
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
