import unittest
import os
import shutil
from pathlib import Path
from PIL import Image
import importlib.util

# Load the sanitizer from the new src layout
BASE_DIR = Path(__file__).parent.parent
SRC_PATH = BASE_DIR / "src" / "slack_emoji_pipeline" / "sanitizer.py"
spec = importlib.util.spec_from_file_location("sanitizer", str(SRC_PATH))
sanitizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sanitizer)

class TestSanitizerLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_sandbox")
        self.test_dir.mkdir(exist_ok=True)
        sanitizer.INPUT_DIR = self.test_dir
        sanitizer.READY_DIR = self.test_dir / "ready"
        sanitizer.READY_DIR.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_processing_creation(self):
        """Verify the sanitizer correctly creates an output file."""
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        img.save(self.test_dir / "test_emoji.png")
        sanitizer.run()
        self.assertTrue((sanitizer.READY_DIR / "test_emoji.png").exists())

if __name__ == "__main__":
    unittest.main()
