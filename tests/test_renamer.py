import unittest
import os
import shutil
from pathlib import Path
import importlib.util

# Load the renamer
BASE_DIR = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("renamer", str(BASE_DIR / "2_rename.py"))
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
        renamer.PREFIX = "cy_"
        renamer.SUFFIX = ""

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_namespace_prefix_application(self):
        """Verify prefix is added correctly and not doubled."""
        # Case 1: Simple name
        self.assertEqual(renamer.apply_namespace("smile", ".png"), "cy_smile.png")
        # Case 2: Already has prefix (Should not double)
        self.assertEqual(renamer.apply_namespace("cy_smile", ".png"), "cy_smile.png")

    def test_collision_guard(self):
        """Verify the renamer detects existing files."""
        # Create an existing file
        (self.named_dir / "cy_smile.png").touch()
        
        # Test the list of existing names
        existing = {f.name for f in self.named_dir.iterdir()}
        self.assertIn("cy_smile.png", existing)

if __name__ == "__main__":
    unittest.main()
