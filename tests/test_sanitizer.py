import unittest
import os
import shutil
from pathlib import Path
from PIL import Image
import importlib.util

# Load the sanitizer from the flat src/ directory
BASE_DIR = Path(__file__).parent.parent
SRC_PATH = BASE_DIR / "src" / "sanitizer.py"
spec = importlib.util.spec_from_file_location("sanitizer", str(SRC_PATH))
san = importlib.util.module_from_spec(spec)
spec.loader.exec_module(san)

class TestImagePersistence(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("test_sanitizer_sandbox")
        self.test_root.mkdir(exist_ok=True)
        san.INPUT_DIR = self.test_root / "emojis"
        san.READY_DIR = self.test_root / "ready"
        san.INPUT_DIR.mkdir()
        san.READY_DIR.mkdir()

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_processing_works(self):
        """Verify the high-fidelity sanitizer processes an image."""
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        img.save(san.INPUT_DIR / "test.png")
        san.run()
        self.assertTrue((san.READY_DIR / "test.png").exists())

if __name__ == "__main__":
    unittest.main()
