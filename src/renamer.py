"""Interactive Emoji Rename Wizard.

This module provides a command-line interface for identifying and naming
sanitized emoji assets. It features cross-platform visual previews, 
namespace management, and a persistent skip-queue.
"""

import logging
import os
import platform
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration Constants
NAMESPACE_PREFIX = os.getenv("NAMESPACE_PREFIX", "").strip()
NAMESPACE_MIDDLE = os.getenv("NAMESPACE_MIDDLE", "").strip()
NAMESPACE_SUFFIX = os.getenv("NAMESPACE_SUFFIX", "").strip()

READY_DIR = Path("emojis_ready")
NAMED_DIR = Path("emojis_named")
EXCLUDED_DIR = Path("emojis_excluded")

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def open_file_cross_platform(filepath: Path):
    """Opens a file using the system's default viewer (Mac, Windows, or Linux)."""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(filepath)], check=False)
        elif system == "Windows":  # Windows
            os.startfile(str(filepath))
        else:  # Linux/Other
            subprocess.run(["xdg-open", str(filepath)], check=False)
    except Exception as err:
        logger.warning("   ⚠️ Could not open preview: %s", err)


def apply_namespace(base_name: str, extension: str) -> str:
    """Wraps a human-readable name in the configured namespace."""
    name = base_name.strip().lower().replace(" ", "_")
    if NAMESPACE_PREFIX and not name.startswith(NAMESPACE_PREFIX):
        name = f"{NAMESPACE_PREFIX}{name}"
    if NAMESPACE_MIDDLE and NAMESPACE_MIDDLE not in name:
        name = f"{name}{NAMESPACE_MIDDLE}"
    if NAMESPACE_SUFFIX and not name.endswith(NAMESPACE_SUFFIX):
        name = f"{name}{NAMESPACE_SUFFIX}"
    return f"{name}{extension}"


def run_rename_wizard():
    """Starts the interactive CLI session for naming emojis."""
    logger.info("🧙‍♂️ Launching Cross-Platform Rename Wizard...")

    if not READY_DIR.exists():
        logger.error("❌ Input folder '%s' missing!", READY_DIR)
        return

    NAMED_DIR.mkdir(exist_ok=True)
    EXCLUDED_DIR.mkdir(exist_ok=True)

    while True:
        files = sorted([f for f in READY_DIR.iterdir() if f.is_file() and not f.name.startswith(".")])
        if not files:
            logger.info("✨ Everything is already named!")
            break

        logger.info("📁 Queue: %d emojis remaining.", len(files))
        existing_names = {f.name for f in NAMED_DIR.iterdir() if f.is_file()}

        print("═" * 60)
        print("  COMMANDS: [s]kip loop | [x]exclude to vault | [q]uit session")
        print("═" * 60)

        skipped_this_round = 0

        for filepath in files:
            logger.info("📦 Identifying: %s", filepath.name)
            open_file_cross_platform(filepath)

            while True:
                user_input = input("   ↳ Enter name (or s/x/q): ").strip().lower()

                if user_input == "q":
                    logger.info("🛑 Session ended.")
                    return
                elif user_input == "s" or not user_input:
                    logger.info("   ⏭️  Skipping to next round.")
                    skipped_this_round += 1
                    break
                elif user_input in ("x", "exclude", "ignore"):
                    os.replace(filepath, EXCLUDED_DIR / filepath.name)
                    logger.info("   🛡️  MOVED TO VAULT: %s", filepath.name)
                    break
                else:
                    final_name = apply_namespace(user_input, filepath.suffix)
                    if final_name in existing_names:
                        logger.error("   ❌ COLLISION: '%s' exists.", final_name)
                        continue
                    try:
                        os.replace(filepath, NAMED_DIR / final_name)
                        existing_names.add(final_name)
                        logger.info("   ✅ Saved as: :%s:", final_name.split(".")[0])
                        break
                    except Exception as err:
                        logger.error("   ❌ Error: %s", err)
                        break

        if skipped_this_round == 0: break
        else: logger.info("🔄 Round finished. Looping back...")

    logger.info("🏁 Wizard complete.")

if __name__ == "__main__":
    run_rename_wizard()
