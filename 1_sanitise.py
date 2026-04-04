"""Emoji Sanitization Engine.

This module provides high-quality image processing for Slack emojis, including
transparency removal, canvas squaring, and frame decimation for GIFs.

The engine follows a "Safety-First" philosophy, protecting intentional white
content in logos while stripping absolute white backgrounds from the edges.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from PIL import Image, ImageChops, ImageDraw, ImageSequence

# Load environment variables
load_dotenv()

# Configuration Constants
INPUT_DIR = Path("emojis")
READY_DIR = Path("emojis_ready")
REVIEW_DIR = Path("emojis_review")
TARGET_PX = int(os.getenv("TARGET_RESOLUTION", "128"))
REMOVE_WHITE_BG = os.getenv("REMOVE_WHITE_BG", "true").lower() == "true"
WHITE_THRESHOLD = int(os.getenv("WHITE_THRESHOLD", "240"))
MAX_FILE_SIZE_KB = 1024
MAX_FRAMES = 50

# Assets that must retain their original background
PROTECTED_ASSETS = set(os.getenv("PROTECTED_ASSETS", "").split(","))

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def remove_white_background(img: Image.Image) -> Image.Image:
    """Removes white background using a corner-seeded flood fill algorithm.

    This method upscales the image to 2x resolution to perform a high-precision
    mask calculation, ensuring smooth anti-aliased edges.

    Args:
        img (Image.Image): The source PIL Image object.

    Returns:
        Image.Image: The processed image with a transparent background.
    """
    orig_size = img.size
    upscale_size = (orig_size[0] * 2, orig_size[1] * 2)

    # Upscale for precision
    working_img = img.resize(upscale_size, Image.Resampling.LANCZOS).convert("RGBA")
    r, g, b, a = working_img.split()

    # Build white mask
    mask_logic = lambda px: 255 if px > WHITE_THRESHOLD else 0
    r_m = r.point(mask_logic)
    g_m = g.point(mask_logic)
    b_m = b.point(mask_logic)
    white_mask = ImageChops.multiply(ImageChops.multiply(r_m, g_m), b_m)

    # Flood-fill from corners
    flood = white_mask.copy()
    w, h = working_img.size
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if flood.getpixel(corner) == 255:
            ImageDraw.floodfill(flood, corner, 128)

    # Downscale mask for anti-aliasing
    bg_mask = flood.point(lambda px: 0 if px == 128 else 255)
    bg_mask = bg_mask.resize(orig_size, Image.Resampling.LANCZOS)

    # Apply to original
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    o_r, o_g, o_b, o_a = img.split()
    img.putalpha(ImageChops.multiply(o_a, bg_mask))

    return img


def make_square(img: Image.Image) -> Image.Image:
    """Pads an image with transparency to force a 1:1 aspect ratio.

    Args:
        img (Image.Image): The source PIL Image object.

    Returns:
        Image.Image: A square version of the input image.
    """
    w, h = img.size
    if w == h:
        return img
    size = max(w, h)
    new_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    new_img.paste(img, ((size - w) // 2, (size - h) // 2))
    return new_img


def resize_to_target(img: Image.Image) -> Image.Image:
    """Scales an image down to fit within the target Slack resolution.

    Args:
        img (Image.Image): The source PIL Image object.

    Returns:
        Image.Image: The resized PIL Image.
    """
    w, h = img.size
    if w <= TARGET_PX and h <= TARGET_PX:
        return img
    ratio = min(TARGET_PX / w, TARGET_PX / h)
    return img.resize(
        (int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS
    )


def get_global_bbox(img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """Calculates a unified bounding box across all animation frames.

    Args:
        img (Image.Image): The source animated Image object.

    Returns:
        Optional[Tuple]: The bounding box coordinates (left, top, right, bottom)
            or None if no content is found.
    """
    union_bbox = None
    for frame in ImageSequence.Iterator(img):
        f = frame.convert("RGBA")
        bbox = f.getbbox()
        if bbox:
            if union_bbox is None:
                union_bbox = bbox
            else:
                union_bbox = (
                    min(union_bbox[0], bbox[0]),
                    min(union_bbox[1], bbox[1]),
                    max(union_bbox[2], bbox[2]),
                    max(union_bbox[3], bbox[3]),
                )
    return union_bbox


def run_sanitization_pipeline():
    """Executes the sanitization process for all files in the intake directory."""
    READY_DIR.mkdir(exist_ok=True)
    REVIEW_DIR.mkdir(exist_ok=True)

    files = sorted(
        [
            f
            for f in INPUT_DIR.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
    )

    if not files:
        logger.info("No files found in input directory: %s", INPUT_DIR)
        return

    logger.info("Starting sanitization of %d files...", len(files))

    for filepath in files:
        emoji_name = filepath.stem
        try:
            with Image.open(filepath) as img:
                is_animated = (
                    getattr(img, "is_animated", False)
                    and getattr(img, "n_frames", 1) > 1
                )
                bbox = get_global_bbox(img)

                frames: List[Image.Image] = []
                durations: List[int] = []

                for frame in ImageSequence.Iterator(img):
                    f = frame.convert("RGBA")
                    if bbox:
                        f = f.crop(bbox)
                    f = make_square(f)

                    if emoji_name not in PROTECTED_ASSETS and REMOVE_WHITE_BG:
                        f = remove_white_background(f)

                    f = resize_to_target(f)
                    frames.append(f)
                    durations.append(frame.info.get("duration", 100))

                dest = READY_DIR / filepath.name
                if not is_animated:
                    dest = dest.with_suffix(".png")
                    frames[0].save(dest, optimize=True)
                else:
                    frames[0].save(
                        dest,
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        loop=0,
                        optimize=False,
                    )
                logger.info("✅ Sanitized: %s", dest.name)

        except Exception as err:
            logger.error("❌ Failed to process %s: %s", filepath.name, err)
            shutil.copy2(filepath, REVIEW_DIR / filepath.name)


if __name__ == "__main__":
    run_sanitization_pipeline()
