import unittest
import os
import shutil
from pathlib import Path
from PIL import Image
import importlib.util

# Load the sanitizer
BASE_DIR = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("sanitise", str(BASE_DIR / "1_sanitise.py"))
sanitise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sanitise)

class TestSanitizerLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_sandbox")
        self.test_dir.mkdir(exist_ok=True)
        sanitise.INPUT_DIR = self.test_dir
        sanitise.READY_DIR = self.test_dir / "ready"
        sanitise.REVIEW_DIR = self.test_dir / "review"
        sanitise.READY_DIR.mkdir(exist_ok=True)
        sanitise.WHITE_THRESHOLD = 240

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_flood_fill_transparency(self):
        """Verify white background is removed but white center is protected."""
        # Create an image with a white background and a black ring with a white center
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        for x in range(40, 60):
            for y in range(40, 60):
                img.putpixel((x, y), (0, 0, 0)) # Black square
        img.putpixel((50, 50), (255, 255, 255)) # White dot INSIDE the black square
        
        img.save(self.test_dir / "logo_test.png")
        sanitise.run()
        
        with Image.open(sanitise.READY_DIR / "logo_test.png") as out:
            out = out.convert("RGBA")
            self.assertEqual(out.getpixel((0, 0))[3], 0)   # Corner should be transparent
            self.assertEqual(out.getpixel((50, 50))[3], 255) # Center should remain OPAQUE white

    def test_canvas_squaring(self):
        """Verify wide images are padded to 1:1 ratio."""
        img = Image.new("RGB", (200, 50), (255, 0, 0))
        img.save(self.test_dir / "wide_test.png")
        sanitise.run()
        
        with Image.open(sanitise.READY_DIR / "wide_test.png") as out:
            w, h = out.size
            self.assertEqual(w, h)

    def test_frame_decimation_trigger(self):
        """Verify frame count is handled (Metadata check)."""
        # Create a basic gif
        frames = [Image.new("RGB", (10, 10), (i, 0, 0)) for i in range(60)]
        frames[0].save(self.test_dir / "long.gif", save_all=True, append_images=frames[1:])
        
        sanitise.run()
        
        with Image.open(sanitise.READY_DIR / "long.gif") as out:
            # Should be <= 50 frames
            self.assertLessEqual(out.n_frames, 50)

if __name__ == "__main__":
    unittest.main()
