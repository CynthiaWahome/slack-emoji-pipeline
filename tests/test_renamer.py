import unittest
from pathlib import Path
import importlib.util

# Load the renamer from the flat src/ directory
BASE_DIR = Path(__file__).parent.parent
SRC_PATH = BASE_DIR / "src" / "renamer.py"
spec = importlib.util.spec_from_file_location("renamer", str(SRC_PATH))
renamer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renamer)

class TestRenamerLogic(unittest.TestCase):
    def test_namespace_application(self):
        """Verify the namespace prefix/middle/suffix logic."""
        renamer.NAMESPACE_PREFIX = "cy_"
        renamer.NAMESPACE_MIDDLE = ""
        renamer.NAMESPACE_SUFFIX = ""
        result = renamer.apply_namespace("smile", ".png")
        self.assertEqual(result, "cy_smile.png")

if __name__ == "__main__":
    unittest.main()
