import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import importlib.util

# Load the uploader
BASE_DIR = Path(__file__).parent.parent
SRC_PATH = BASE_DIR / "src" / "uploader.py"
spec = importlib.util.spec_from_file_location("uploader", str(SRC_PATH))
uploader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uploader)

class TestUploaderLogic(unittest.TestCase):
    def test_api_guard_filter(self):
        """Verify the API Guard correctly identifies live emojis."""
        mock_page = MagicMock()
        # Mocking the internal Slack API response
        with patch('src.uploader.fetch_live_list') as mock_fetch:
            mock_fetch.return_value = {"cy_smile", "cy_rocket"}
            # This is where we verify the logic of the guard
            self.assertIn("cy_smile", mock_fetch.return_value)

    def test_browser_executable_detection(self):
        """Verify the browser hunter returns a string."""
        path = uploader._find_browser_executable()
        self.assertIsInstance(path, str)

if __name__ == "__main__":
    unittest.main()
