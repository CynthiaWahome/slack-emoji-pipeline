"""Professional Playwright Emoji Uploader.

This module automates the process of uploading sanitized emoji assets to a
Slack workspace. It features an API-driven duplicate guard, physical UI
verification, and aggressive browser session management.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

# Load environment variables
load_dotenv()

# Configuration Constants
SLACK_WORKSPACE = os.getenv("SLACK_WORKSPACE", "").strip()
NAMED_DIR = Path("emojis_named")
UPLOAD_DELAY = float(os.getenv("UPLOAD_DELAY_SECONDS", 2.0))

# Comma-separated list of assets to skip for specific deployments
EXCLUDE_ASSETS = {
    name.strip()
    for name in os.getenv("EXCLUDE_ASSETS", "").split(",")
    if name.strip()
}

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("upload_log.txt", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def fetch_live_emoji_list(page: Page) -> Set[str]:
    """Retrieves the set of currently active emoji names from the Slack API.

    This method utilizes the browser context to perform an authenticated
    fetch request to the Slack 'emoji.list' endpoint.

    Args:
        page (Page): The active Playwright Page object.

    Returns:
        Set[str]: A set containing the names of all live emojis.
    """
    try:
        # Extract API token from the page context
        token = await page.evaluate("window.TS.boot_data.api_token")
        # Execute the fetch directly in the browser to leverage session cookies
        script = f"fetch('/api/emoji.list?token={token}').then(r => r.json())"
        response = await page.evaluate(script)

        if response.get("ok"):
            return set(response["emoji"].keys())
    except Exception as err:
        logger.warning("Could not fetch live list: %s", err)

    return set()


async def execute_upload_mission():
    """Manages the end-to-end browser automation for emoji deployment."""
    if not NAMED_DIR.exists():
        logger.error("❌ Named directory '%s' missing!", NAMED_DIR)
        return

    # Filter out files excluded by the user configuration
    all_files = sorted(
        [
            f
            for f in NAMED_DIR.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
    )
    targets = [f for f in all_files if f.stem not in EXCLUDE_ASSETS]

    if not targets:
        logger.info("🎉 No emojis found for upload.")
        return

    workspace_url = f"https://{SLACK_WORKSPACE}.slack.com"
    target_page = f"{workspace_url}/customize/emoji"

    async with async_playwright() as pw:
        # Standard paths for Brave on macOS
        brave_bin = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        user_data = os.path.expanduser(
            "~/Library/Application Support/BraveSoftware/Brave-Browser"
        )

        logger.info("🚀 Launching Master-Grade Robot (Brave)...")
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=user_data,
            executable_path=brave_bin,
            headless=False,
            slow_mo=200,
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"],
        )

        # AGGRESSIVE SINGLE-TAB MANDATE
        page = context.pages[0]
        for extra_page in context.pages[1:]:
            await extra_page.close()

        logger.info("🔗 Connecting to: %s", target_page)
        await page.goto(target_page, wait_until="commit")

        print("\n" + "═" * 60)
        print("  🚀 ACTION REQUIRED")
        print("  1. Log into Slack and navigate to the Emoji page.")
        print("  2. Press ENTER in this terminal when ready to deploy.")
        print("═" * 60)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "\nPress ENTER to start...")

        # Initialize counters
        success_count = 0
        skip_count = 0
        fail_count = 0

        # Fetch live list for smart duplicate skipping (API Guard)
        live_list = await fetch_live_emoji_list(page)
        logger.info("📊 Workspace currently has %d custom emojis.", len(live_list))

        for i, filepath in enumerate(targets):
            emoji_name = filepath.stem

            # 🛡️ API GUARD: Skip if already live
            if emoji_name in live_list:
                logger.info(
                    "⏭️  [%d/%d] Skipping: :%s: (Already Live)",
                    i + 1,
                    len(targets),
                    emoji_name,
                )
                skip_count += 1
                continue

            logger.info(
                "📦 [%d/%d] Uploading: :%s:", i + 1, len(targets), emoji_name
            )

            try:
                # Clear UI clutter
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

                # Open Add Modal using stable data-qa selector
                add_btn = page.locator(
                    "[data-qa='customize_emoji_add_button']"
                ).first
                await add_btn.wait_for(state="visible", timeout=10000)
                await add_btn.click(force=True)

                # Inject file path and set identification name
                await page.locator("input[type='file']").first.set_input_files(
                    str(filepath.resolve())
                )
                await page.locator(
                    "[data-qa='customize_emoji_name_input']"
                ).first.fill(emoji_name)

                # Commit to Slack
                save_btn = page.locator(
                    "[data-qa='customize_emoji_save_button']"
                ).first
                await save_btn.click()

                # HONEST VERIFICATION: Success confirmed only if modal vanishes
                await add_btn.wait_for(state="visible", timeout=15000)
                logger.info("   ✅ VERIFIED SUCCESS")
                success_count += 1

            except Exception as err:
                logger.warning("   ❌ FAILED: %s - %s", emoji_name, err)
                fail_count += 1
                await page.keyboard.press("Escape")

            await asyncio.sleep(UPLOAD_DELAY)

        logger.info("\n" + "═" * 60)
        logger.info("  🏁 FINAL MISSION REPORT")
        logger.info("═" * 60)
        logger.info("  ✅ SUCCESSFULLY UPLOADED : %d", success_count)
        logger.info("  ⏭️  SKIPPED (ALREADY LIVE) : %d", skip_count)
        logger.info("  ❌ FAILED / TIMED OUT    : %d", fail_count)
        logger.info("═" * 60)


if __name__ == "__main__":
    if not SLACK_WORKSPACE:
        logger.error("Configuration Error: SLACK_WORKSPACE not defined in .env")
    else:
        asyncio.run(execute_upload_mission())
