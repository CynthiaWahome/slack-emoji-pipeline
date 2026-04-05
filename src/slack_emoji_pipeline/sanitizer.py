"""
Emoji Pipeline — Stage 1: Sanitise & Optimise

Reads every image from emojis/ and produces a Slack-ready version
in emojis_ready/. Anything it cannot fix goes to emojis_review/.

What "Slack-ready" means
------------------------
- Under 1024 KB (Slack's hard limit)
- Max 128 × 128 px
- Square canvas (fills the emoji box in chat)
- Transparent background where possible
- Animated GIFs and WebPs stay animated, with stable frames
- Protected list: logos with intentional white keep their background

White-background removal — flood-fill from corners
---------------------------------------------------
1. Build a binary map of all near-white pixels.
2. From each corner, flood-fill outward (like Photoshop's paint bucket),
   marking every *connected* white pixel as "background."
3. Only background-connected white is removed. White enclosed by dark
   content (logo text, icons) is unreachable from the corners and stays.
Corner guard: if a corner pixel is NOT white the flood-fill never starts,
so images with dark or transparent backgrounds are left completely alone.

Known limitations
-----------------
- White pixels at the exact same luminance as the background AND touching
  a corner edge are removed (anti-aliasing halos). Lower WHITE_THRESHOLD
  to 220 if you lose content; raise to 250 to be more conservative.
- Very large animated GIFs (100+ frames) may still exceed 1024 KB after
  processing. Those land in emojis_review/ — use ezgif.com to reduce
  frame count then re-run.
- We cannot distinguish "background white" from "logo white" in images
  where white content touches the image edge. The flood-fill handles most
  cases; hard edge-cases need manual background removal (remove.bg).

Usage
-----
    python -m slack_emoji_pipeline.sanitizer

Configuration (via .env)
------------------------
    INPUT_DIR          = emojis        folder to read from
    TARGET_RESOLUTION  = 128           max px per side
    MAX_FILE_SIZE_KB   = 1024          reject files above this before processing
    REMOVE_WHITE_BG    = true          flood-fill white removal on/off
    WHITE_THRESHOLD    = 240           240=near-white | 220=off-white too | 250=conservative
    PROTECTED_ASSETS   = cy_foo,cy_bar comma-separated stems; skip white removal for these
"""

import logging
import os
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageSequence
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_DIR        = Path(os.getenv("INPUT_DIR", "emojis"))
READY_DIR        = Path("emojis_ready")
REVIEW_DIR       = Path("emojis_review")
MAX_FILE_SIZE_KB = int(os.getenv("MAX_FILE_SIZE_KB", "1024"))
TARGET_PX        = int(os.getenv("TARGET_RESOLUTION", "128"))
REMOVE_WHITE_BG  = os.getenv("REMOVE_WHITE_BG", "true").lower() == "true"
WHITE_THRESHOLD  = int(os.getenv("WHITE_THRESHOLD", "240"))
ALLOWED_FORMATS  = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

_raw = os.getenv("PROTECTED_ASSETS", "")
PROTECTED_ASSETS: set[str] = set(n.strip() for n in _raw.split(",") if n.strip())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("sanitise_log.txt", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── White-background removal ──────────────────────────────────────────────────

def remove_white_background(img: Image.Image) -> Image.Image:
    """Remove background white using flood-fill from image corners.

    Only white pixels *connected to a corner* are removed.
    White enclosed by dark content (logo text, icons) stays intact.
    Corner guard: only floods from a corner if that corner pixel IS white.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    r, g, b, a = img.split()
    r_mask = r.point(lambda px: 255 if px > WHITE_THRESHOLD else 0)
    g_mask = g.point(lambda px: 255 if px > WHITE_THRESHOLD else 0)
    b_mask = b.point(lambda px: 255 if px > WHITE_THRESHOLD else 0)
    white_mask = ImageChops.multiply(ImageChops.multiply(r_mask, g_mask), b_mask)

    flood = white_mask.copy()
    w, h = img.size
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if flood.getpixel(corner) == 255:   # only flood from white corners
            ImageDraw.floodfill(flood, corner, 128)

    # 128 = background-connected → transparent; anything else → keep
    bg_mask = flood.point(lambda px: 0 if px == 128 else 255)
    img.putalpha(ImageChops.multiply(a, bg_mask))
    return img


# ── Frame helpers ─────────────────────────────────────────────────────────────

def _get_global_bbox(filepath: Path) -> tuple[int, int, int, int] | None:
    """Return the union bounding box across ALL frames.

    Per-frame bbox causes jitter in animations: each frame has content in a
    different position → different crop box → animation shakes.
    One shared box covering all frames = stable animation.
    """
    gl = gt = gr = gb = None
    try:
        with Image.open(filepath) as img:
            for frame in ImageSequence.Iterator(img):
                bbox = frame.convert("RGBA").getbbox()
                if not bbox:
                    continue
                l, t, r, b = bbox
                gl = l if gl is None else min(gl, l)
                gt = t if gt is None else min(gt, t)
                gr = r if gr is None else max(gr, r)
                gb = b if gb is None else max(gb, b)
    except Exception as exc:
        log.warning("         ⚠  Global bbox failed: %s", exc)
    return (gl, gt, gr, gb) if gl is not None else None


def _make_square(img: Image.Image) -> Image.Image:
    """Pad a non-square image to a perfect square with transparent fill.

    A 120 × 30 emoji stays tiny in Slack because Slack fits it in a square —
    the 30 px height never grows. After squaring it becomes 120 × 120 and
    Slack fills the box properly.
    """
    w, h = img.size
    if w == h:
        return img
    size   = max(w, h)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - w) // 2, (size - h) // 2), img)
    return canvas


def _resize(img: Image.Image) -> Image.Image:
    """Scale down so the longest side = TARGET_PX. Never upscales."""
    w, h = img.size
    if w <= TARGET_PX and h <= TARGET_PX:
        return img
    ratio    = min(TARGET_PX / w, TARGET_PX / h)
    new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def _process_one_frame(
    frame: Image.Image,
    emoji_name: str,
    crop_box: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Transform one image frame: RGBA → white removal → crop → square → resize."""
    f = frame.convert("RGBA")

    if REMOVE_WHITE_BG and emoji_name not in PROTECTED_ASSETS:
        f = remove_white_background(f)

    if crop_box:
        f = f.crop(crop_box)
    else:
        bbox = f.getbbox()
        if bbox:
            f = f.crop(bbox)

    f = _make_square(f)
    return _resize(f)


# ── Processors ────────────────────────────────────────────────────────────────

def _process_animation(filepath: Path, dest: Path, emoji_name: str) -> bool:
    """Process animated GIF or WebP frame-by-frame, preserving timing."""
    try:
        global_bbox = _get_global_bbox(filepath)

        with Image.open(filepath) as img:
            orig_loop           = img.info.get("loop", 0)
            frames: list[Image.Image] = []
            durations: list[int]      = []

            for frame in ImageSequence.Iterator(img):
                frames.append(_process_one_frame(frame.copy(), emoji_name, global_bbox))
                durations.append(frame.info.get("duration", 100))

        if not frames:
            return False

        log.info("         🎞  %d frames | bbox: %s", len(frames), global_bbox)

        if filepath.suffix.lower() == ".webp":
            frames[0].save(
                dest,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=orig_loop,
                method=6,
                lossless=False,
                quality=90,
            )
        else:
            # optimize=False: critical — optimizer can corrupt multi-frame palettes
            # disposal=2: clear each frame before the next (prevents ghosting)
            frames[0].save(
                dest,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=orig_loop,
                optimize=False,
                disposal=2,
            )
        return True

    except Exception as exc:
        log.error("         ❌ Animation failed: %s", exc)
        return False


def _process_static(filepath: Path, dest: Path, emoji_name: str) -> bool:
    """Process a single static image. Always saves as PNG."""
    try:
        with Image.open(filepath) as img:
            processed = _process_one_frame(img.copy(), emoji_name)
        processed.save(dest.with_suffix(".png"), format="PNG", optimize=True)
        return True
    except Exception as exc:
        log.error("         ❌ Static failed: %s", exc)
        return False


# ── Validation ────────────────────────────────────────────────────────────────

def _check_file(filepath: Path) -> tuple[bool, str]:
    if filepath.suffix.lower() not in ALLOWED_FORMATS:
        return False, f"Unsupported format '{filepath.suffix}'"
    if filepath.stat().st_size == 0:
        return False, "Empty file"
    size_kb = filepath.stat().st_size / 1024
    if size_kb > MAX_FILE_SIZE_KB:
        return False, f"Too large: {size_kb:.0f} KB (limit: {MAX_FILE_SIZE_KB} KB)"
    try:
        with Image.open(filepath) as img:
            img.verify()          # catches corrupt files; also closes the stream
    except Exception as exc:
        return False, f"Corrupt or unreadable: {exc}"
    return True, "OK"


# ── Main ──────────────────────────────────────────────────────────────────────

def run() -> tuple[int, int]:
    """Run the sanitiser. Returns (passed, failed)."""
    READY_DIR.mkdir(exist_ok=True)
    REVIEW_DIR.mkdir(exist_ok=True)

    files = sorted(
        f for f in INPUT_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )

    if not files:
        log.warning("⚠  No files found in '%s/'. Drop emojis there first.", INPUT_DIR)
        return 0, 0

    log.info("\n%s", "═" * 64)
    log.info("  EMOJI PIPELINE — sanitizer.py")
    log.info("  Files     : %d", len(files))
    log.info("  Target    : %d×%d px  |  Max: %d KB", TARGET_PX, TARGET_PX, MAX_FILE_SIZE_KB)
    log.info(
        "  White BG  : %s",
        f"flood-fill ON (threshold={WHITE_THRESHOLD})" if REMOVE_WHITE_BG else "OFF",
    )
    if PROTECTED_ASSETS:
        log.info("  Protected : %s", ", ".join(sorted(PROTECTED_ASSETS)))
    log.info("%s\n", "═" * 64)

    passed = failed = 0

    for filepath in files:
        size_kb    = filepath.stat().st_size / 1024
        emoji_name = filepath.stem

        ok, reason = _check_file(filepath)
        if not ok:
            shutil.copy2(filepath, REVIEW_DIR / filepath.name)
            log.warning("❌ SKIP    %s  [%.0f KB]", filepath.name, size_kb)
            log.warning("           ↳ %s\n", reason)
            failed += 1
            continue

        # Detect animation from metadata — NOT from file extension.
        # Checking extension misses animated WebPs (the source of the
        # "Batman went static" bug in earlier versions).
        is_animated = False
        try:
            with Image.open(filepath) as img:
                is_animated = (
                    getattr(img, "is_animated", False)
                    and getattr(img, "n_frames", 1) > 1
                )
        except Exception:
            pass

        prot = emoji_name in PROTECTED_ASSETS
        log.info(
            "%s %s  [%.0f KB]%s",
            "🎞 " if is_animated else "🖼 ",
            filepath.name,
            size_kb,
            "  [protected — white kept]" if prot else "",
        )

        # Animated keeps its extension; static always becomes PNG
        dest = READY_DIR / (
            filepath.name if is_animated else filepath.stem + ".png"
        )

        success = (
            _process_animation(filepath, dest, emoji_name)
            if is_animated
            else _process_static(filepath, dest, emoji_name)
        )

        if success:
            saved    = next(READY_DIR.glob(filepath.stem + ".*"), dest)
            final_kb = saved.stat().st_size / 1024
            log.info("   ✅ → %s  [%.0f KB → %.0f KB]\n", saved.name, size_kb, final_kb)
            passed += 1
        else:
            shutil.copy2(filepath, REVIEW_DIR / filepath.name)
            log.warning("   ❌ → emojis_review/\n")
            failed += 1

    log.info("%s", "═" * 64)
    log.info("  ✅ %d ready   →  emojis_ready/", passed)
    log.info("  ❌ %d review  →  emojis_review/", failed)
    if failed:
        log.info("")
        log.info("  How to fix emojis_review/ files:")
        log.info("    White bg remaining  →  remove.bg  or  Canva BG Remover")
        log.info("    Still too large     →  squoosh.app  or  ezgif.com (reduce frames)")
        log.info("    Drop fixed files back into emojis/ and re-run")
    log.info("  Log: sanitise_log.txt")
    log.info("%s\n", "═" * 64)

    return passed, failed


if __name__ == "__main__":
    run()
