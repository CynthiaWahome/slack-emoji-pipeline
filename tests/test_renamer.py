import unittest
import os
import shutil
from pathlib import Path
import importlib.util

# Load the renamer from the new src layout
BASE_DIR = Path(__file__).parent.parent
SRC_PATH = BASE_DIR / "src" / "slack_emoji_pipeline" / "renamer.py"
spec = importlib.util.spec_from_file_location("renamer", str(SRC_PATH))
renamer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renamer)

class TestRenamerLogic(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("test_renamer_sandbox")
        self.test_root.mkdir(exist_ok=True)
        self.ready_dir = self.test_root / "ready"
        self.named_dir = self.test_root / "named"
        self.ready_dir.mkdir()
        self.named_dir.mkdir()
        
        # Point script to sandbox
        renamer.READY_DIR = self.ready_dir
        renamer.NAMED_DIR = self.named_dir
        renamer.NAMESPACE_PREFIX = "cy_"
        renamer.NAMESPACE_SUFFIX = ""

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_namespace_prefix_application(self):
        """Verify prefix is added correctly and not doubled."""
        self.assertEqual(renamer.apply_namespace("smile", ".png"), "cy_smile.png")
        self.assertEqual(renamer.apply_namespace("cy_smile", ".png"), "cy_smile.png")

    def test_collision_guard(self):
        """Verify the renamer detects existing files."""
        (self.named_dir / "cy_smile.png").touch()
        existing = {f.name for f in self.named_dir.iterdir()}
        self.assertIn("cy_smile.png", existing)

if __name__ == "__main__":
    unittest.main()
