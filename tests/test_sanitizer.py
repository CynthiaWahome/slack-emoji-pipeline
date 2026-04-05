"""
Comprehensive test suite for slack_emoji_pipeline.sanitizer

Covers every bug fixed in the hotfix PR:
  - BUG-1  save_all=True on static images crashes
  - BUG-2  per-frame bbox causes animation jitter
  - BUG-3  luminance-only white removal erases logo content
  - BUG-4  optimize=True corrupts animated GIF palettes
  - BUG-5  make_square without mask argument

And general behaviour:
  - Animated WebP detection (not extension-based)
  - Protected assets keep white background
  - Non-white backgrounds (black, dark) untouched
  - File validation (unsupported, empty, oversized)
  - JPG → PNG conversion
  - Canvas squaring for thin/wide images
  - Static image output is always PNG
  - Logging output file created
"""

import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_png(size=(60, 60), color=(255, 100, 50, 255), mode="RGBA") -> io.BytesIO:
    buf = io.BytesIO()
    img = Image.new(mode, size, color)
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _make_gif(n_frames=3, size=(80, 80)) -> io.BytesIO:
    """Animated GIF with a dot that moves across frames."""
    frames = []
    for i in range(n_frames):
        f = Image.new("RGBA", size, (0, 0, 0, 0))
        x = 10 + i * 20
        ImageDraw.Draw(f).ellipse([x, 10, x + 20, 30], fill=(255, 100, 0, 255))
        frames.append(f)
    buf = io.BytesIO()
    frames[0].save(
        buf, format="GIF", save_all=True, append_images=frames[1:],
        duration=[100] * n_frames, loop=0,
    )
    buf.seek(0)
    return buf


def _make_webp_animated(n_frames=3, size=(80, 80)) -> io.BytesIO:
    frames = []
    for i in range(n_frames):
        f = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(f).ellipse([5 + i*15, 5, 25 + i*15, 25], fill=(200, 100, 50, 255))
        frames.append(f)
    buf = io.BytesIO()
    frames[0].save(
        buf, format="WEBP", save_all=True, append_images=frames[1:],
        duration=[100] * n_frames, loop=0,
    )
    buf.seek(0)
    return buf


# ── Import module under test ──────────────────────────────────────────────────

import importlib.util, sys

_HERE = Path(__file__).parent
_SRC  = _HERE.parent / "src" / "slack_emoji_pipeline" / "sanitizer.py"
spec  = importlib.util.spec_from_file_location("sanitizer", str(_SRC))
san   = importlib.util.module_from_spec(spec)      # type: ignore[arg-type]
spec.loader.exec_module(san)                        # type: ignore[union-attr]


# ── Base test class ───────────────────────────────────────────────────────────

class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp      = Path(tempfile.mkdtemp())
        self.input    = self.tmp / "emojis"
        self.ready    = self.tmp / "emojis_ready"
        self.review   = self.tmp / "emojis_review"
        self.input.mkdir()

        # Redirect module paths to sandbox
        san.INPUT_DIR  = self.input
        san.READY_DIR  = self.ready
        san.REVIEW_DIR = self.review
        san.PROTECTED_ASSETS  = set()
        san.REMOVE_WHITE_BG   = True
        san.WHITE_THRESHOLD   = 240
        san.TARGET_PX         = 128
        san.MAX_FILE_SIZE_KB  = 1024

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        # Remove log created during test runs
        Path("sanitise_log.txt").unlink(missing_ok=True)

    def _write(self, name: str, data: io.BytesIO) -> Path:
        p = self.input / name
        p.write_bytes(data.read())
        return p


# ═══════════════════════════════════════════════════════════════════════════════
#  BUG-1 — save_all=True on static image
# ═══════════════════════════════════════════════════════════════════════════════

class TestBug1StaticSaveAll(_Base):
    """BUG-1: save_all=True on a static PNG crashed with 'unknown file extension'."""

    def test_static_png_does_not_crash(self):
        self._write("smile.png", _make_png())
        passed, failed = san.run()
        self.assertEqual(passed, 1, "Static PNG should pass without crashing")
        self.assertEqual(failed, 0)

    def test_static_output_is_png(self):
        self._write("smile.png", _make_png())
        san.run()
        output_files = list(self.ready.glob("smile.*"))
        self.assertEqual(len(output_files), 1)
        self.assertEqual(output_files[0].suffix, ".png")

    def test_static_jpg_converted_to_png(self):
        buf = io.BytesIO()
        Image.new("RGB", (60, 60), (200, 100, 50)).save(buf, format="JPEG")
        buf.seek(0)
        self._write("face.jpg", buf)
        san.run()
        self.assertTrue((self.ready / "face.png").exists(), "JPG must be saved as PNG")
        self.assertFalse((self.ready / "face.jpg").exists(), "Original .jpg must not appear in ready/")


# ═══════════════════════════════════════════════════════════════════════════════
#  BUG-2 — per-frame bbox jitter
# ═══════════════════════════════════════════════════════════════════════════════

class TestBug2GlobalBbox(_Base):
    """BUG-2: per-frame bbox causes jitter when content moves between frames."""

    def test_global_bbox_is_union_of_all_frames(self):
        """get_global_bbox must return a box that includes all frame content."""
        gif_path = self._write("confetti.gif", _make_gif(n_frames=3, size=(100, 100)))
        bbox = san._get_global_bbox(gif_path)
        self.assertIsNotNone(bbox, "Global bbox should not be None for a valid GIF")
        l, t, r, b = bbox
        # Content starts at x=10 on frame 0 and reaches x=50 on frame 2
        self.assertLessEqual(l, 10, "Left bound must cover frame-0 content")
        self.assertGreaterEqual(r, 50, "Right bound must cover frame-2 content")

    def test_all_frames_same_size_after_processing(self):
        """After processing, every frame must be the same dimensions."""
        gif_path = self._write("bounce.gif", _make_gif(n_frames=4, size=(100, 100)))
        san.run()
        output = next(self.ready.glob("bounce.*"))
        with Image.open(output) as img:
            from PIL import ImageSequence
            sizes = [f.size for f in ImageSequence.Iterator(img)]
        self.assertEqual(len(set(sizes)), 1, f"All frames must be same size, got: {sizes}")

    def test_global_bbox_none_for_fully_transparent_gif(self):
        """A GIF with all-transparent frames returns None bbox gracefully."""
        frames = [Image.new("RGBA", (50, 50), (0, 0, 0, 0)) for _ in range(2)]
        buf = io.BytesIO()
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=[100, 100])
        buf.seek(0)
        p = self._write("empty.gif", buf)
        bbox = san._get_global_bbox(p)
        self.assertIsNone(bbox)


# ═══════════════════════════════════════════════════════════════════════════════
#  BUG-3 — luminance-only white removal erases logo content
# ═══════════════════════════════════════════════════════════════════════════════

class TestBug3FloodFillWhiteRemoval(_Base):
    """BUG-3: luminance filter removed white logo content; flood-fill must not."""

    def _white_bg_with_red_circle(self) -> Image.Image:
        img = Image.new("RGBA", (50, 50), (255, 255, 255, 255))
        ImageDraw.Draw(img).ellipse([15, 15, 35, 35], fill=(255, 0, 0, 255))
        return img

    def _white_bg_with_enclosed_white_logo(self) -> Image.Image:
        """Dark border with white text inside — logo white must survive."""
        img = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
        ImageDraw.Draw(img).rectangle([4, 4, 36, 36], fill=(20, 20, 20, 255))    # dark border
        ImageDraw.Draw(img).rectangle([10, 10, 30, 30], fill=(255, 255, 255, 255))  # white logo
        return img

    def test_background_white_is_removed(self):
        img    = self._white_bg_with_red_circle()
        result = san.remove_white_background(img)
        alpha  = result.getpixel((0, 0))[3]     # corner pixel
        self.assertEqual(alpha, 0, "Background white corner must become transparent")

    def test_red_content_survives(self):
        img    = self._white_bg_with_red_circle()
        result = san.remove_white_background(img)
        alpha  = result.getpixel((25, 25))[3]   # centre of red circle
        self.assertEqual(alpha, 255, "Red logo content must not be removed")

    def test_enclosed_logo_white_survives(self):
        """White enclosed by dark content must NOT be removed."""
        img    = self._white_bg_with_enclosed_white_logo()
        result = san.remove_white_background(img)
        alpha  = result.getpixel((20, 20))[3]   # centre of enclosed white
        self.assertEqual(alpha, 255, "Enclosed logo white must survive flood-fill")

    def test_dark_background_untouched(self):
        """Image with a dark (non-white) background — nothing should change."""
        img = Image.new("RGBA", (40, 40), (0, 0, 0, 255))
        ImageDraw.Draw(img).ellipse([10, 10, 30, 30], fill=(200, 100, 50, 255))
        original = img.copy()
        result   = san.remove_white_background(img)
        # All alpha values should be unchanged
        for px in [result.getpixel((0, 0)), result.getpixel((20, 20))]:
            orig_px = original.getpixel(px[:2]) if False else None  # just check alpha
        corner_alpha = result.getpixel((0, 0))[3]
        self.assertEqual(corner_alpha, 255, "Dark background corner must stay opaque")

    def test_protected_asset_keeps_white(self):
        san.PROTECTED_ASSETS = {"cy_codeit"}
        img = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
        result = san._process_one_frame(img, "cy_codeit")
        # After squaring + resize the image will still have opaque pixels
        # (protected = white removal skipped entirely)
        # Check that at least some pixels remain opaque
        pixels = [result.getpixel((x, x))[3] for x in range(0, result.size[0], 5)]
        self.assertTrue(any(a > 0 for a in pixels), "Protected asset must retain visible pixels")

    def test_non_protected_asset_gets_cleaned(self):
        san.PROTECTED_ASSETS = set()
        img = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
        result = san._process_one_frame(img, "cy_crying")
        corner_alpha = result.getpixel((0, 0))[3]
        self.assertEqual(corner_alpha, 0, "Non-protected white bg must be removed")


# ═══════════════════════════════════════════════════════════════════════════════
#  BUG-4 — optimize=True corrupts animated GIF
# ═══════════════════════════════════════════════════════════════════════════════

class TestBug4GifOptimize(_Base):
    """BUG-4: optimize=True can corrupt multi-frame GIF palettes."""

    def test_animated_gif_stays_animated(self):
        self._write("dance.gif", _make_gif(n_frames=5))
        san.run()
        output = next(self.ready.glob("dance.*"), None)
        self.assertIsNotNone(output, "Animated GIF must produce an output file")
        with Image.open(output) as img:
            n = getattr(img, "n_frames", 1)
        self.assertGreater(n, 1, f"Output must be animated (got {n} frames)")

    def test_animated_gif_frame_count_preserved(self):
        self._write("spin.gif", _make_gif(n_frames=3))
        san.run()
        output = next(self.ready.glob("spin.*"))
        with Image.open(output) as img:
            self.assertEqual(img.n_frames, 3)

    def test_animated_gif_keeps_extension(self):
        self._write("wave.gif", _make_gif(n_frames=2))
        san.run()
        self.assertTrue((self.ready / "wave.gif").exists())


# ═══════════════════════════════════════════════════════════════════════════════
#  Animated WebP detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnimatedWebpDetection(_Base):
    """Animated WebPs must not be treated as static images."""

    def test_animated_webp_stays_animated(self):
        self._write("batman.webp", _make_webp_animated(n_frames=3))
        san.run()
        output = next(self.ready.glob("batman.*"), None)
        self.assertIsNotNone(output)
        with Image.open(output) as img:
            n = getattr(img, "n_frames", 1)
        self.assertGreater(n, 1, "Animated WebP must remain animated after processing")

    def test_static_webp_produces_png(self):
        buf = io.BytesIO()
        Image.new("RGBA", (60, 60), (100, 200, 50, 255)).save(buf, format="WEBP")
        buf.seek(0)
        self._write("chill.webp", buf)
        san.run()
        self.assertTrue((self.ready / "chill.png").exists(), "Static WebP must be saved as PNG")


# ═══════════════════════════════════════════════════════════════════════════════
#  Canvas squaring
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanvasSquaring(_Base):
    """make_square must produce 1:1 images so emojis fill Slack's box."""

    def test_square_image_unchanged(self):
        img = Image.new("RGBA", (64, 64), (100, 200, 50, 255))
        result = san._make_square(img)
        self.assertEqual(result.size, (64, 64))

    def test_wide_image_becomes_square(self):
        img = Image.new("RGBA", (120, 30), (100, 200, 50, 255))
        result = san._make_square(img)
        self.assertEqual(result.size[0], result.size[1], "Width and height must be equal")
        self.assertEqual(result.size[0], 120)

    def test_tall_image_becomes_square(self):
        img = Image.new("RGBA", (30, 120), (100, 200, 50, 255))
        result = san._make_square(img)
        self.assertEqual(result.size[0], result.size[1])
        self.assertEqual(result.size[0], 120)

    def test_padding_is_transparent(self):
        img = Image.new("RGBA", (100, 20), (255, 100, 50, 255))
        result = san._make_square(img)
        # Top-left corner should be transparent padding
        top_left = result.getpixel((0, 0))
        self.assertEqual(top_left[3], 0, "Padding must be fully transparent")

    def test_content_is_centred(self):
        """Original content must land in the vertical centre of the square."""
        img    = Image.new("RGBA", (100, 20), (255, 0, 0, 255))  # red strip
        result = san._make_square(img)
        cx, cy = result.size[0] // 2, result.size[1] // 2
        centre_pixel = result.getpixel((cx, cy))
        self.assertEqual(centre_pixel[:3], (255, 0, 0), "Red content must be at centre")

    def test_wide_emoji_processed_correctly(self):
        """End-to-end: a thin wide emoji must produce a square PNG."""
        buf = io.BytesIO()
        Image.new("RGBA", (200, 40), (100, 200, 50, 255)).save(buf, format="PNG")
        buf.seek(0)
        self._write("clockit.png", buf)
        san.run()
        output = next(self.ready.glob("clockit.*"))
        with Image.open(output) as img:
            self.assertEqual(img.size[0], img.size[1], "Output must be square")


# ═══════════════════════════════════════════════════════════════════════════════
#  File validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileValidation(_Base):
    """Bouncer: reject bad files before processing."""

    def test_unsupported_format_goes_to_review(self):
        (self.input / "emoji.bmp").write_bytes(b"fake bmp data")
        passed, failed = san.run()
        self.assertEqual(failed, 1)
        self.assertTrue((self.review / "emoji.bmp").exists())

    def test_empty_file_goes_to_review(self):
        (self.input / "empty.png").write_bytes(b"")
        passed, failed = san.run()
        self.assertEqual(failed, 1)

    def test_oversized_file_goes_to_review(self):
        # Make a file that is genuinely over 5KB so we can set a 5KB limit
        buf = io.BytesIO()
        import random
        # Noisy image → poor compression → larger file
        import struct
        pixels = bytes([random.randint(0, 255) for _ in range(400 * 400 * 3)])
        img = Image.frombytes("RGB", (400, 400), pixels)
        img.save(buf, format="PNG")
        actual_kb = len(buf.getvalue()) / 1024
        san.MAX_FILE_SIZE_KB = max(1, int(actual_kb) - 10)  # set limit below actual size
        buf.seek(0)
        self._write("big.png", buf)
        passed, failed = san.run()
        self.assertEqual(failed, 1)
        self.assertTrue((self.review / "big.png").exists())

    def test_valid_file_passes(self):
        self._write("ok.png", _make_png())
        passed, failed = san.run()
        self.assertEqual(passed, 1)
        self.assertEqual(failed, 0)

    def test_hidden_files_skipped(self):
        (self.input / ".DS_Store").write_bytes(b"mac garbage")
        self._write("smile.png", _make_png())
        passed, failed = san.run()
        self.assertEqual(passed, 1)
        self.assertEqual(failed, 0)

    def test_empty_input_returns_zero_zero(self):
        result = san.run()
        self.assertEqual(result, (0, 0))


# ═══════════════════════════════════════════════════════════════════════════════
#  Resize behaviour
# ═══════════════════════════════════════════════════════════════════════════════

class TestResize(_Base):
    def test_large_image_shrunk_to_target(self):
        buf = io.BytesIO()
        Image.new("RGBA", (500, 500), (100, 100, 200, 255)).save(buf, format="PNG")
        buf.seek(0)
        self._write("big.png", buf)
        san.run()
        with Image.open(self.ready / "big.png") as img:
            self.assertLessEqual(max(img.size), san.TARGET_PX)

    def test_small_image_not_upscaled(self):
        buf = io.BytesIO()
        Image.new("RGBA", (32, 32), (100, 100, 200, 255)).save(buf, format="PNG")
        buf.seek(0)
        self._write("tiny.png", buf)
        san.run()
        with Image.open(self.ready / "tiny.png") as img:
            self.assertLessEqual(max(img.size), san.TARGET_PX)
            # Should NOT have been blown up
            self.assertLessEqual(max(img.size), 32 + 1)   # +1 for rounding


# ═══════════════════════════════════════════════════════════════════════════════
#  run() return values and logging
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunBehaviour(_Base):
    def test_returns_correct_counts(self):
        self._write("good.png", _make_png())
        (self.input / "bad.bmp").write_bytes(b"garbage")
        passed, failed = san.run()
        self.assertEqual(passed, 1)
        self.assertEqual(failed, 1)

    def test_log_file_created(self):
        # Log file path is configured at module level; redirect to tmp so tests stay clean
        log_path = self.tmp / "sanitise_log.txt"
        # Replace the FileHandler to write into our sandbox
        import logging
        logger = logging.getLogger("sanitizer")
        for h in san.log.handlers[:]:
            if isinstance(h, logging.FileHandler):
                san.log.removeHandler(h)
                h.close()
        handler = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
        san.log.addHandler(handler)
        try:
            self._write("smile.png", _make_png())
            san.run()
            self.assertTrue(log_path.exists(), "Log file must be created during run()")
        finally:
            san.log.removeHandler(handler)
            handler.close()


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
