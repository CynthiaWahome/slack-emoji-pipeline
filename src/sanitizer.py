"""Emoji Sanitization Engine.

This module provides high-quality image processing for Slack emojis, including
flood-fill transparency, canvas squaring, and frame decimation for GIFs.
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
WHITE_THRESHOLD = int(os.getenv("WHITE_THRESHOLD", "240"))
MAX_FILE_SIZE_KB = 1024
MAX_FRAMES = 50

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def remove_white_background(img: Image.Image) -> Image.Image:
    """Removes background white using corner-seeded flood fill.

    This algorithm identifies white pixels reachable from the image corners
    and converts them to transparent, effectively protecting internal white
    content like logo centers.

    Args:
        img (Image.Image): The source PIL Image object.

    Returns:
        Image.Image: The processed image with a transparent background.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()

    # Build white mask
    mask_logic = lambda px: 255 if px > WHITE_THRESHOLD else 0
    white_mask = ImageChops.multiply(
        ImageChops.multiply(r.point(mask_logic), g.point(mask_logic)),
        b.point(mask_logic),
    )

    # Flood-fill from corners
    flood = white_mask.copy()
    w, h = img.size
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if flood.getpixel(corner) == 255:
            ImageDraw.floodfill(flood, corner, 128)

    # 128 = background white -> 0 (transparent)
    bg_mask = flood.point(lambda px: 0 if px == 128 else 255)
    img.putalpha(ImageChops.multiply(a, bg_mask))
    return img


def make_square(img: Image.Image) -> Image.Image:
    """Pads image with transparency to force a 1:1 aspect ratio.

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


def get_global_bbox(img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """Calculates a unified bounding box across all animation frames.

    Args:
        img (Image.Image): The source animated Image object.

    Returns:
        Optional[Tuple]: The bounding box coordinates (left, top, right, bottom).
    """
    union_bbox = None
    for frame in ImageSequence.Iterator(img):
        bbox = frame.convert("RGBA").getbbox()
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


def run():
    """Executes the sanitization pipeline for all files in the intake folder."""
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
                    f = remove_white_background(f)

                    # Scale to target
                    ratio = min(TARGET_PX / f.width, TARGET_PX / f.height)
                    f = f.resize(
                        (int(f.width * ratio), int(f.height * ratio)),
                        Image.Resampling.LANCZOS,
                    )
                    frames.append(f)
                    durations.append(frame.info.get("duration", 100))

                # Frame Decimation for GIFs
                if len(frames) > MAX_FRAMES:
                    step = len(frames) // MAX_FRAMES + 1
                    frames, durations = frames[::step], durations[::step]

                dest = READY_DIR / filepath.name
                if not is_animated:
                    dest = dest.with_suffix(".png")
                    frames[0].save(dest, optimize=True)
                else:
                    # GIF-specific optimization: disable palette scrambling
                    is_gif = dest.suffix.lower() == ".gif"
                    frames[0].save(
                        dest,
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        loop=0,
                        optimize=not is_gif,
                        disposal=2 if is_gif else 0,
                    )
                logger.info("✅ Processed: %s", dest.name)

        except Exception as err:
            logger.error("❌ Failed %s: %s", filepath.name, err)
            shutil.copy2(filepath, REVIEW_DIR / filepath.name)


if __name__ == "__main__":
    run()
