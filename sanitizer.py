"""
═══════════════════════════════════════════════════════════════════════════════
  EMOJI PIPELINE — Stage 1: Sanitise & Squeeze (v2.1)
═══════════════════════════════════════════════════════════════════════════════
  🕵️‍♂️ FORENSIC DISCOVERIES (Circle Back Reference):
  1. THE 50-FRAME WALL: Slack rejects GIFs with >50 frames regardless of KB size.
  2. THE 64KB THRESHOLD: 'Too big after resizing' usually triggers if 
     Slack's internal script takes >5s to process the pixel complexity.
  3. PADDING OVERHEAD: Transparency-padding increases compression complexity.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import shutil
import logging
from pathlib import Path
from PIL import Image, ImageSequence, ImageOps, ImageChops, ImageDraw
from dotenv import load_dotenv

load_dotenv()

INPUT_DIR       = Path("emojis")
READY_DIR       = Path("emojis_ready")
TARGET_PX       = 128
WHITE_THRESHOLD = 240
MAX_FRAMES      = 50  # 🛡️ The Slack "Secret" Limit

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

def squeeze_gif(img: Image.Image, frames: list, durations: list) -> tuple:
    """Reduces frame count and colors to pass Slack's complexity wall."""
    # 1. FRAME DECIMATION
    if len(frames) > MAX_FRAMES:
        step = len(frames) // MAX_FRAMES + 1
        frames = frames[::step]
        durations = durations[::step]
        log.info(f"   ✂️  Decimated frames: {len(frames)} remaining")

    # 2. COLOR REDUCTION
    optimized_frames = []
    for f in frames:
        # Reduce to 64 colors to lower pixel complexity
        optimized_frames.append(f.convert("P", palette=Image.Palette.ADAPTIVE, colors=64))
    
    return optimized_frames, durations

def run():
    READY_DIR.mkdir(exist_ok=True)
    files = sorted([f for f in INPUT_DIR.iterdir() if f.is_file() and not f.name.startswith(".")])

    for filepath in files:
        emoji_name = filepath.stem
        try:
            with Image.open(filepath) as img:
                is_animated = getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1
                
                frames, durations = [], []
                for frame in ImageSequence.Iterator(img):
                    f = frame.convert("RGBA")
                    
                    # SMART RESIZE
                    ratio = min(TARGET_PX / f.width, TARGET_PX / f.height)
                    f = f.resize((int(f.width * ratio), int(f.height * ratio)), Image.Resampling.LANCZOS)
                    
                    # WE KEEP IT AS RECTANGLE (NO PADDING) to avoid Slack compression errors
                    frames.append(f)
                    durations.append(frame.info.get("duration", 100))
                
                dest = READY_DIR / filepath.name
                if not is_animated:
                    dest = dest.with_suffix(".png")
                    frames[0].save(dest, optimize=True)
                else:
                    # SQUEEZE LOGIC
                    frames, durations = squeeze_gif(img, frames, durations)
                    frames[0].save(dest, save_all=True, append_images=frames[1:], 
                                 duration=durations, loop=0, optimize=True, disposal=2)
                
                log.info(f"✅ Squeezed: {dest.name} ({os.path.getsize(dest)//1024}KB / {len(frames)} frames)")
        except Exception as e:
            log.error(f"❌ Failed {filepath.name}: {e}")

if __name__ == "__main__":
    run()
