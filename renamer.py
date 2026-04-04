"""Interactive Emoji Rename Wizard.

This module provides a command-line interface for identifying and naming
sanitized emoji assets. It features visual previews, namespace management,
collision protection, and a persistent skip-queue.
"""

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration Constants
NAMESPACE_PREFIX = os.getenv("NAMESPACE_PREFIX", "").strip()
NAMESPACE_SUFFIX = os.getenv("NAMESPACE_SUFFIX", "").strip()
READY_DIR = Path("emojis_ready")
NAMED_DIR = Path("emojis_named")
EXCLUDED_DIR = Path("emojis_excluded")

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("rename_log.txt", mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def apply_namespace(base_name: str, extension: str) -> str:
    """Wraps a human-readable name in the configured namespace.

    This method ensures that the name is lowercase, uses underscores for
    spaces, and correctly applies the configured prefix and suffix without
    duplication.

    Args:
        base_name (str): The raw name entered by the user.
        extension (str): The file extension (e.g., '.png').

    Returns:
        str: The fully namespaced filename.
    """
    name = base_name.strip().lower().replace(" ", "_")

    # Prefix wrap (avoid duplication)
    if NAMESPACE_PREFIX and not name.startswith(NAMESPACE_PREFIX):
        name = f"{NAMESPACE_PREFIX}{name}"

    # Suffix wrap (avoid duplication)
    if NAMESPACE_SUFFIX and not name.endswith(NAMESPACE_SUFFIX):
        name = f"{name}{NAMESPACE_SUFFIX}"

    return f"{name}{extension}"


def run_rename_wizard():
    """Starts the interactive CLI session for naming emojis.

    Loops through all files in the 'ready' directory, opening previews and
    handling human input via an If/Elif/Else logic gate.
    """
    logger.info("🧙‍♂️ Launching Zero-Loss Master Wizard...")

    if not READY_DIR.exists():
        logger.error("❌ Input folder '%s' missing! Run Stage 1 first.", READY_DIR)
        return

    NAMED_DIR.mkdir(exist_ok=True)
    EXCLUDED_DIR.mkdir(exist_ok=True)

    while True:
        # Fetch fresh list of remaining assets
        files = sorted(
            [
                f
                for f in READY_DIR.iterdir()
                if f.is_file() and not f.name.startswith(".")
            ]
        )

        if not files:
            logger.info("✨ MISSION COMPLETE! All emojis processed.")
            break

        logger.info("📁 Queue: %d emojis remaining.", len(files))
        existing_names = {f.name for f in NAMED_DIR.iterdir() if f.is_file()}

        print("═" * 60)
        print("  COMMANDS: [s]kip loop | [x]exclude to vault | [q]uit session")
        print("═" * 60)

        skipped_this_round = 0

        for filepath in files:
            logger.info("📦 Identifying: %s", filepath.name)
            try:
                subprocess.run(["open", str(filepath)], check=False)
            except Exception as err:
                logger.warning("   ⚠️ Could not open preview: %s", err)

            while True:
                user_input = input("   ↳ Enter name (or s/x/q): ").strip().lower()

                # IF: QUIT
                if user_input == "q":
                    logger.info("🛑 Session ended by user. Progress saved.")
                    return

                # ELIF: SKIP (Move to back of the queue)
                elif user_input == "s" or not user_input:
                    logger.info("   ⏭️  Skipping to next round.")
                    skipped_this_round += 1
                    break

                # ELIF: EXCLUDE (Surgical removal to Vault)
                elif user_input in ("x", "exclude", "ignore"):
                    try:
                        os.replace(filepath, EXCLUDED_DIR / filepath.name)
                        logger.info("   🛡️  MOVED TO VAULT: %s", filepath.name)
                    except Exception as err:
                        logger.error("   ❌ Vault error: %s", err)
                    break

                # ELSE: PROCESS RENAME
                else:
                    final_name = apply_namespace(user_input, filepath.suffix)

                    if final_name in existing_names:
                        logger.error(
                            "   ❌ COLLISION: '%s' exists. Try again.", final_name
                        )
                        continue

                    try:
                        os.replace(filepath, NAMED_DIR / final_name)
                        existing_names.add(final_name)
                        logger.info("   ✅ Saved as: :%s:", final_name.split(".")[0])
                        break
                    except Exception as err:
                        logger.error("   ❌ System Error: %s", err)
                        break

        # Check if we finished a pass without skipping
        if skipped_this_round == 0:
            break
        else:
            logger.info(
                "🔄 Round finished. %d emojis still need names. Looping back...",
                skipped_this_round,
            )

    logger.info("🏁 Wizard session complete.")


if __name__ == "__main__":
    run_rename_wizard()
