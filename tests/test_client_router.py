import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.client_router import build_client_map, resolve_client, create_routing_client


class TestBuildClientMap(unittest.TestCase):

    def test_none_returns_empty(self):
        self.assertEqual(build_client_map(None), {})

    def test_empty_string_returns_empty(self):
        self.assertEqual(build_client_map(""), {})

    def test_single_mapping(self):
        result = build_client_map("writing_agent=antigravity")
        self.assertEqual(result, {"writing_agent": "antigravity"})

    def test_multiple_mappings(self):
        result = build_client_map(
            "story_architect=antigravity,writing_agent=openai,coach_agent=antigravity"
        )
        self.assertEqual(result, {
            "story_architect": "antigravity",
            "writing_agent": "openai",
            "coach_agent": "antigravity",
        })

    def test_whitespace_tolerance(self):
        result = build_client_map(" writing_agent = antigravity , coach_agent = openai ")
        self.assertEqual(result, {
            "writing_agent": "antigravity",
            "coach_agent": "openai",
        })

    def test_invalid_client_raises(self):
        with self.assertRaises(ValueError) as ctx:
            build_client_map("writing_agent=unknown_client")
        self.assertIn("unknown_client", str(ctx.exception))

    def test_missing_equals_raises(self):
        with self.assertRaises(ValueError):
            build_client_map("writing_agent")

    def test_empty_stage_raises(self):
        with self.assertRaises(ValueError):
            build_client_map("=antigravity")


class TestResolveClient(unittest.TestCase):

    def test_openai_resolves(self):
        client = resolve_client("openai")
        self.assertTrue(callable(client))
        self.assertEqual(client.__name__, "call_openai")

    def test_antigravity_resolves(self):
        client = resolve_client("antigravity")
        self.assertTrue(callable(client))
        self.assertEqual(client.__name__, "call_antigravity")

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            resolve_client("nonexistent")


class TestCreateRoutingClient(unittest.TestCase):

    @patch("engine.client_router.resolve_client")
    def test_routes_to_mapped_client(self, mock_resolve):
        mock_antigravity = MagicMock(return_value="antigravity_response")
        mock_openai = MagicMock(return_value="openai_response")
        mock_resolve.side_effect = lambda name: (
            mock_antigravity if name == "antigravity" else mock_openai
        )

        client_map = {"writing_agent": "antigravity"}
        router = create_routing_client(client_map, fallback="openai")

        # Stage in map → antigravity
        result = router("prompt", {}, "writing_agent")
        self.assertEqual(result, "antigravity_response")

        # Stage NOT in map → fallback openai
        result = router("prompt", {}, "story_architect")
        self.assertEqual(result, "openai_response")

    @patch("engine.client_router.resolve_client")
    def test_none_stage_uses_fallback(self, mock_resolve):
        mock_openai = MagicMock(return_value="openai_response")
        mock_resolve.return_value = mock_openai

        router = create_routing_client({}, fallback="openai")
        result = router("prompt", {}, None)
        self.assertEqual(result, "openai_response")

    @patch("engine.client_router.resolve_client")
    def test_routing_client_has_correct_name(self, mock_resolve):
        mock_resolve.return_value = MagicMock()
        router = create_routing_client({}, fallback="openai")
        self.assertEqual(router.__name__, "routing_client")


if __name__ == "__main__":
    unittest.main()
