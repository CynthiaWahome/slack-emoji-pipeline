"""Professional Playwright Emoji Uploader.

This module automates the process of uploading sanitized emoji assets to a
Slack workspace. It features an API-driven duplicate guard, physical UI
verification, and automated browser hunting.
"""

import asyncio
import logging
import os
import platform
from pathlib import Path
from typing import List, Set

from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

load_dotenv()

# Configuration Constants
SLACK_WORKSPACE = os.getenv("SLACK_WORKSPACE", "").strip()
NAMED_DIR = Path("emojis_named")
UPLOAD_DELAY = float(os.getenv("UPLOAD_DELAY_SECONDS", 2.0))
EXCLUDE_ASSETS = {
    name.strip()
    for name in os.getenv("EXCLUDE_ASSETS", "").split(",")
    if name.strip()
}

# Browser Overrides
ENV_BROWSER_PATH = os.getenv("BROWSER_EXECUTABLE", "").strip()
ENV_PROFILE_DIR = os.getenv("BROWSER_PROFILE_DIR", "").strip()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _find_browser_executable() -> str:
    """Detects the location of a Chromium-based browser on the host OS.

    Returns:
        str: The absolute path to the browser binary or empty string.
    """
    if ENV_BROWSER_PATH:
        return ENV_BROWSER_PATH

    system = platform.system()
    paths = []

    if system == "Darwin":  # macOS
        paths = [
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    elif system == "Windows":
        paths = [
            os.path.expandvars(
                r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
            ),
            os.path.expandvars(
                r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"
            ),
        ]

    for path in paths:
        if os.path.exists(path):
            return path

    return ""


def _find_profile_dir() -> str:
    """Detects the standard user-data directory for the detected browser.

    Returns:
        str: The absolute path to the user profile directory.
    """
    if ENV_PROFILE_DIR:
        return ENV_PROFILE_DIR

    system = platform.system()
    if system == "Darwin":
        return os.path.expanduser(
            "~/Library/Application Support/BraveSoftware/Brave-Browser"
        )

    return os.path.join(os.getcwd(), "browser_session")


async def fetch_live_list(page: Page) -> Set[str]:
    """Queries the Slack API for the current list of custom emojis.

    Args:
        page (Page): The active Playwright Page object.

    Returns:
        Set[str]: A set of all live emoji names.
    """
    try:
        token = await page.evaluate("window.TS.boot_data.api_token")
        response = await page.evaluate(
            f"fetch('/api/emoji.list?token={token}').then(r => r.json())"
        )
        if response.get("ok"):
            return set(response["emoji"].keys())
    except Exception as err:
        logger.warning("API Guard failure: %s", err)
    return set()


async def execute_upload():
    """Main deployment loop for the Playwright robot."""
    if not NAMED_DIR.exists():
        logger.error("Source directory not found: %s", NAMED_DIR)
        return

    all_files = sorted(
        [
            f
            for f in NAMED_DIR.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
    )
    targets = [f for f in all_files if f.stem not in EXCLUDE_ASSETS]

    if not targets:
        logger.info("No assets queued for upload.")
        return

    failed_emojis: List[str] = []
    success_count = 0
    skip_count = 0

    async with async_playwright() as pw:
        browser_path = _find_browser_executable()
        profile_path = _find_profile_dir()

        logger.info("🚀 Launching robot (Path: %s)", browser_path or "Default")
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            executable_path=browser_path or None,
            headless=False,
            slow_mo=200,
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0]
        for p in context.pages[1:]:
            await p.close()

        url = f"https://{SLACK_WORKSPACE}.slack.com/customize/emoji"
        await page.goto(url, wait_until="commit")

        print("\n🚀 ACTION: Log in and press ENTER in terminal when ready.")
        await asyncio.get_event_loop().run_in_executor(None, input, "")

        live_list = await fetch_live_list(page)

        for i, filepath in enumerate(targets):
            name = filepath.stem
            if name in live_list:
                logger.info(
                    "[%d/%d] Skipping :%s: (Live)", i + 1, len(targets), name
                )
                skip_count += 1
                continue

            logger.info("[%d/%d] Uploading :%s:", i + 1, len(targets), name)
            try:
                await page.keyboard.press("Escape")
                add_btn = page.locator(
                    "[data-qa='customize_emoji_add_button']"
                ).first
                await add_btn.wait_for(state="visible", timeout=5000)
                await add_btn.click(force=True)

                await page.locator("input[type='file']").first.set_input_files(
                    str(filepath.resolve())
                )
                await page.locator(
                    "[data-qa='customize_emoji_name_input']"
                ).first.fill(name)

                save_btn = page.locator(
                    "[data-qa='customize_emoji_save_button']"
                ).first
                await save_btn.click()

                # Physical Verification
                await add_btn.wait_for(state="visible", timeout=15000)
                logger.info("   ✅ SUCCESS")
                success_count += 1
            except Exception:
                logger.warning("   ❌ FAILED: %s", name)
                failed_emojis.append(name)
                await page.keyboard.press("Escape")

            await asyncio.sleep(UPLOAD_DELAY)

    # FINAL CLEAN REPORT
    print("\n" + "═" * 60)
    print("  🏁 FINAL MISSION REPORT")
    print("═" * 60)
    print(f"  ✅ SUCCESSES: {success_count}")
    print(f"  ⏭️  SKIPPED  : {skip_count}")
    print(f"  ❌ FAILURES : {len(failed_emojis)}")
    if failed_emojis:
        print("\n  📋 FAILED LIST (Copy-Paste):")
        print(f"  {', '.join(failed_emojis)}")
    print("═" * 60)


if __name__ == "__main__":
    if not SLACK_WORKSPACE:
        logger.error("SLACK_WORKSPACE not defined in .env")
    else:
        asyncio.run(execute_upload())
