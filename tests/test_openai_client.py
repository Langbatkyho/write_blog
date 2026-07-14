import sys
import unittest
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.openai_client import get_api_key, call_openai

class OpenAIClientTest(unittest.TestCase):
    def test_get_api_key_direct_warns(self) -> None:
        config = {
            "openai": {
                "api_key": "sk-test-direct-key"
            }
        }
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            key = get_api_key(config)
            self.assertEqual(key, "sk-test-direct-key")
            self.assertEqual(len(w), 1)
            self.assertTrue("hardcoded" in str(w[0].message))

    @patch("urllib.request.urlopen")
    def test_call_openai_retries_on_429(self, mock_urlopen: MagicMock) -> None:
        # Mock HTTP Error 429 followed by a success
        mock_response_success = MagicMock()
        mock_response_success.read.return_value = b'{"output_text": "Success Response"}'
        mock_response_success.__enter__.return_value = mock_response_success
        
        # We need a function to mock HTTPError raising then succeeding
        mock_error = urllib.error.HTTPError(
            url="http://test.com",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=MagicMock()
        )
        
        mock_urlopen.side_effect = [mock_error, mock_response_success]
        
        config = {
            "openai": {
                "api_key": "sk-mock-key",
                "endpoint": "https://api.openai.com/v1/responses",
                "model": "gpt-4.1",
                "temperature": 0.7,
                "max_output_tokens": 4096
            }
        }
        
        # Speed up retry sleep during tests
        with patch("time.sleep") as mock_sleep:
            res = call_openai("test prompt", config, max_retries=2)
            self.assertEqual(res, "Success Response")
            self.assertEqual(mock_sleep.call_count, 1)
            mock_sleep.assert_called_with(1) # 2 ** 0

if __name__ == "__main__":
    unittest.main()
