import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from engine.antigravity_bridge import call_antigravity

class TestAntigravityBridge(unittest.TestCase):

    @patch("engine.antigravity_bridge.Path")
    @patch("engine.antigravity_bridge.time.sleep")
    @patch("engine.antigravity_bridge.time.time")
    def test_call_antigravity_success(self, mock_time, mock_sleep, mock_path_cls):
        # Setup mock paths
        mock_temp_dir = MagicMock()
        mock_prompt_file = MagicMock()
        mock_response_file = MagicMock()
        mock_model_file = MagicMock()
        
        # When temp_dir / ... is called, return the appropriate mock
        def side_effect_truediv(other):
            if "prompt" in other: return mock_prompt_file
            if "response" in other: return mock_response_file
            if "model" in other: return mock_model_file
            return MagicMock()
            
        mock_temp_dir.__truediv__.side_effect = side_effect_truediv
        
        mock_file_path = mock_path_cls.return_value
        mock_resolved = mock_file_path.resolve.return_value
        mock_parents_1 = mock_resolved.parents.__getitem__.return_value
        mock_parents_1.__truediv__.return_value.__truediv__.return_value = mock_temp_dir
        
        # Mock time progression: start at 100, then wait 1 second
        mock_time.side_effect = [100.0, 100.0, 101.0, 101.0]
        
        # Mock response_file.exists(): False on first check, True on second
        mock_response_file.exists.side_effect = [False, True]
        mock_response_file.read_text.return_value = "Mocked Response"

        config = {"openai": {"model": "test-model"}, "antigravity": {"timeout": 5}}
        
        result = call_antigravity("Hello", config, "test_stage")
        
        self.assertEqual(result, "Mocked Response")
        mock_prompt_file.write_text.assert_called_with("Hello", encoding="utf-8")
        mock_model_file.write_text.assert_called_with("test-model", encoding="utf-8")
        mock_response_file.read_text.assert_called_with(encoding="utf-8")
        
        # Check cleanup was called
        mock_prompt_file.unlink.assert_called()
        mock_model_file.unlink.assert_called()

    @patch("engine.antigravity_bridge.Path")
    @patch("engine.antigravity_bridge.time.sleep")
    @patch("engine.antigravity_bridge.time.time")
    def test_call_antigravity_timeout(self, mock_time, mock_sleep, mock_path_cls):
        # Setup mock paths
        mock_temp_dir = MagicMock()
        mock_prompt_file = MagicMock()
        mock_response_file = MagicMock()
        mock_model_file = MagicMock()
        
        def side_effect_truediv(other):
            if "prompt" in other: return mock_prompt_file
            if "response" in other: return mock_response_file
            if "model" in other: return mock_model_file
            return MagicMock()
            
        mock_temp_dir.__truediv__.side_effect = side_effect_truediv
        
        mock_file_path = mock_path_cls.return_value
        mock_resolved = mock_file_path.resolve.return_value
        mock_parents_1 = mock_resolved.parents.__getitem__.return_value
        mock_parents_1.__truediv__.return_value.__truediv__.return_value = mock_temp_dir
        
        # Time progression exceeds timeout immediately
        mock_time.side_effect = [100.0, 100.0, 110.0, 110.0]
        mock_response_file.exists.return_value = False
        
        config = {"antigravity": {"timeout": 5}}
        
        with self.assertRaises(TimeoutError) as context:
            call_antigravity("Hello", config, "test_stage")
            
        self.assertIn("did not respond within 5 seconds", str(context.exception))

if __name__ == "__main__":
    unittest.main()
