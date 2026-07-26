import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.style_manager import (
    validate_style_yaml,
    list_styles,
    get_style_detail,
    save_style_file,
    create_style,
    rename_style,
    delete_style,
    resolve_style_by_slug_or_alias,
    validate_style_contract,
)
from engine.utils import resolve_path, read_text, load_yaml

class TestStyleManager(unittest.TestCase):
    def setUp(self) -> None:
        self.test_slugs = ["test-custom", "test-rename-old", "test-rename-new", "test-save-atomic"]
        for slug in self.test_slugs:
            d = resolve_path(f"skills/deep/{slug}")
            if d.exists():
                shutil.rmtree(d)

    def tearDown(self) -> None:
        for slug in self.test_slugs:
            d = resolve_path(f"skills/deep/{slug}")
            if d.exists():
                shutil.rmtree(d)

    def test_validate_style_yaml_universal_hard_check(self) -> None:
        valid_yaml = "name: test\noutput:\n  file: test.md\ntasks:\n  - task1"
        is_valid, err, warn = validate_style_yaml(valid_yaml, "story_architect.yaml", "deep")
        self.assertTrue(is_valid)

        no_name = "output:\n  file: test.md\ntasks:\n  - task1"
        is_valid, err, warn = validate_style_yaml(no_name, "story_architect.yaml", "deep")
        self.assertFalse(is_valid)
        self.assertIn("name", err)

        no_output = "name: test\ntasks:\n  - task1"
        is_valid, err, warn = validate_style_yaml(no_output, "story_architect.yaml", "deep")
        self.assertFalse(is_valid)
        self.assertIn("output", err)

    def test_validate_style_yaml_specific_hard_check_deep_a(self) -> None:
        no_tasks = "name: story_architect\noutput:\n  file: out.md\npurpose: test"
        is_valid, err, warn = validate_style_yaml(no_tasks, "story_architect.yaml", "deep")
        self.assertFalse(is_valid)
        self.assertIn("tasks", err)

    def test_validate_style_yaml_specific_hard_check_deep_b(self) -> None:
        # writing_agent has supreme_rule, NO tasks! Should PASS!
        writing_yaml = "name: writing_agent\noutput:\n  file: out.md\nsupreme_rule: Never edit."
        is_valid, err, warn = validate_style_yaml(writing_yaml, "writing_agent.yaml", "deep")
        self.assertTrue(is_valid, f"Expected PASS for writing_agent without tasks, got err: {err}")

        # If missing supreme_rule/purpose/identity -> FAIL
        invalid_writing = "name: writing_agent\noutput:\n  file: out.md\ntasks:\n  - do something"
        is_valid, err, warn = validate_style_yaml(invalid_writing, "writing_agent.yaml", "deep")
        self.assertFalse(is_valid)
        self.assertIn("supreme_rule", err)

    def test_validate_style_yaml_soft_warning(self) -> None:
        # Valid YAML, but missing rules/do_not/style_rules/supreme_rule
        no_guardrails = "name: test_agent\noutput:\n  file: out.md\ntasks:\n  - t1"
        is_valid, err, warn = validate_style_yaml(no_guardrails, "story_architect.yaml", "deep")
        self.assertTrue(is_valid)
        self.assertIn("Cảnh báo", warn)

    def test_list_styles(self) -> None:
        styles = list_styles("deep")
        slugs = [s["slug"] for s in styles]
        self.assertIn("reflective", slugs)
        self.assertIn("provocative", slugs)

    def test_get_style_detail(self) -> None:
        detail = get_style_detail("deep", "reflective")
        self.assertEqual(detail["metadata"]["slug"], "reflective")
        self.assertEqual(len(detail["files"]), 7)

    def test_create_and_delete_custom_style(self) -> None:
        success, msg = create_style("deep", "Test Custom", "test-custom", "Description test", clone_from="reflective")
        self.assertTrue(success, msg)
        self.assertTrue(resolve_path("skills/deep/test-custom").exists())
        self.assertTrue(resolve_path("skills/deep/test-custom/style_meta.yaml").exists())

        # Check protected system style delete attempt
        del_success, del_msg = delete_style("deep", "reflective")
        self.assertFalse(del_success)
        self.assertIn("is_protected", del_msg)

        # Check custom style delete
        del_success, del_msg = delete_style("deep", "test-custom")
        self.assertTrue(del_success, del_msg)
        self.assertFalse(resolve_path("skills/deep/test-custom").exists())

    def test_rename_style_and_alias_resolution(self) -> None:
        success, msg = create_style("deep", "Test Rename Old", "test-rename-old", "Desc", clone_from="reflective")
        self.assertTrue(success, msg)

        # Rename
        ren_success, ren_msg = rename_style("deep", "test-rename-old", "Test Rename New", "test-rename-new")
        self.assertTrue(ren_success, ren_msg)
        self.assertFalse(resolve_path("skills/deep/test-rename-old").exists())
        self.assertTrue(resolve_path("skills/deep/test-rename-new").exists())

        # Alias lookup
        resolved = resolve_style_by_slug_or_alias("deep", "test-rename-old")
        self.assertEqual(resolved, "test-rename-new")

        # Contract validation with old slug
        validated = validate_style_contract("deep", "test-rename-old")
        self.assertEqual(validated, "test-rename-new")

        delete_style("deep", "test-rename-new")

    def test_create_style_rollback_on_failure(self) -> None:
        success, msg = create_style("deep", "Invalid", "invalid..slug", "Desc")
        self.assertFalse(success)
        self.assertFalse(resolve_path("skills/deep/invalid..slug").exists())

        success, msg = create_style("deep", "Invalid Source", "test-custom", "Desc", clone_from="non-existent-source")
        self.assertFalse(success)
        self.assertFalse(resolve_path("skills/deep/test-custom").exists())

    def test_save_style_file_atomic(self) -> None:
        create_style("deep", "Test Save", "test-save-atomic", "Desc", clone_from="reflective")
        target_file = "story_architect.yaml"
        original_content = read_text(resolve_path(f"skills/deep/test-save-atomic/{target_file}"))
        new_content = original_content + "\n# Modified comment\n"

        success, err, warn = save_style_file("deep", "test-save-atomic", target_file, new_content)
        self.assertTrue(success, err)
        saved_content = read_text(resolve_path(f"skills/deep/test-save-atomic/{target_file}"))
        self.assertIn("# Modified comment", saved_content)
        self.assertFalse(resolve_path(f"skills/deep/test-save-atomic/{target_file}.tmp").exists())

        delete_style("deep", "test-save-atomic")

if __name__ == "__main__":
    unittest.main()
