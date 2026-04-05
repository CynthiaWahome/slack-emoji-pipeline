"""Professional Playwright Emoji Uploader.

Automates bulk uploading of sanitized emoji assets to a Slack workspace.
Features API-driven duplicate guard, cross-platform browser detection,
and verified upload confirmation.

Cross-platform browser detection
---------------------------------
The uploader tries to find an existing Chromium-based browser on the
system so it can borrow your real login session, which Slack trusts.

Priority order:
  macOS   → Brave → Chrome → Edge → Chromium
  Windows → Brave → Chrome → Edge → Chromium
  Linux   → brave-browser → google-chrome → chromium-browser → chromium

If no installed browser is found the uploader falls back to Playwright's
bundled Chromium with a dedicated session directory (browser_session/).
In that fallback case you will need to log in once; the session is then
saved for all future runs.

Override via .env
-----------------
    BROWSER_EXECUTABLE=/path/to/your/browser
    BROWSER_PROFILE_DIR=/path/to/your/profile

Usage
-----
    python -m slack_emoji_pipeline.uploader
"""

import asyncio
import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Optional, Set

from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SLACK_WORKSPACE = os.getenv("SLACK_WORKSPACE", "").strip()
NAMED_DIR       = Path("emojis_named")
SESSION_DIR     = Path("browser_session")   # fallback when no system browser found
UPLOAD_DELAY    = float(os.getenv("UPLOAD_DELAY_SECONDS", "2.0"))

EXCLUDE_ASSETS: Set[str] = {
    name.strip()
    for name in os.getenv("EXCLUDE_ASSETS", "").split(",")
    if name.strip()
}

# Manual overrides — if set in .env these take precedence over auto-detection
BROWSER_EXECUTABLE  = os.getenv("BROWSER_EXECUTABLE", "").strip() or None
BROWSER_PROFILE_DIR = os.getenv("BROWSER_PROFILE_DIR", "").strip() or None

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


# ── Cross-platform browser detection ─────────────────────────────────────────

def _find_browser_executable() -> Optional[str]:
    """Locate a Chromium-based browser on the current system.

    Returns the path to the first browser found, or None if none is
    installed (Playwright's bundled Chromium will be used as fallback).
    """
    system = platform.system()
    home   = os.path.expanduser("~")
    candidates: list[str] = []

    if system == "Darwin":  # macOS
        candidates = [
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif system == "Windows":
        pf  = os.environ.get("PROGRAMFILES",       r"C:\Program Files")
        pf86= os.environ.get("PROGRAMFILES(X86)",  r"C:\Program Files (x86)")
        candidates = [
            rf"{pf}\BraveSoftware\Brave-Browser\Application\brave.exe",
            rf"{pf}\Google\Chrome\Application\chrome.exe",
            rf"{pf86}\Google\Chrome\Application\chrome.exe",
            rf"{pf}\Microsoft\Edge\Application\msedge.exe",
            rf"{pf86}\Microsoft\Edge\Application\msedge.exe",
        ]
    else:  # Linux / other POSIX
        # shutil.which searches $PATH — covers snap, flatpak, distro packages
        for name in ["brave-browser", "brave", "google-chrome",
                     "chromium-browser", "chromium", "microsoft-edge"]:
            found = shutil.which(name)
            if found:
                candidates.insert(0, found)
        candidates += [
            "/usr/bin/brave-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
        ]

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _find_profile_dir(executable: Optional[str]) -> Optional[str]:
    """Return the user-data directory that matches the detected browser.

    Returning the real profile means Slack sees a genuine human session
    and doesn't show a "browser not supported" block page.
    Returns None if the profile directory cannot be determined — in that
    case Playwright uses the dedicated browser_session/ directory instead.
    """
    if not executable:
        return None

    system = platform.system()
    home   = os.path.expanduser("~")
    exe    = executable.lower()

    if system == "Darwin":
        if "brave"  in exe: return f"{home}/Library/Application Support/BraveSoftware/Brave-Browser"
        if "chrome" in exe: return f"{home}/Library/Application Support/Google/Chrome"
        if "edge"   in exe: return f"{home}/Library/Application Support/Microsoft Edge"
        if "chromium" in exe: return f"{home}/Library/Application Support/Chromium"

    elif system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA", "")
        if "brave"    in exe: return rf"{appdata}\BraveSoftware\Brave-Browser\User Data"
        if "chrome"   in exe: return rf"{appdata}\Google\Chrome\User Data"
        if "edge"     in exe: return rf"{appdata}\Microsoft\Edge\User Data"
        if "chromium" in exe: return rf"{appdata}\Chromium\User Data"

    else:  # Linux
        if "brave"    in exe: return f"{home}/.config/BraveSoftware/Brave-Browser"
        if "chrome"   in exe: return f"{home}/.config/google-chrome"
        if "edge"     in exe: return f"{home}/.config/microsoft-edge"
        if "chromium" in exe: return f"{home}/.config/chromium"

    return None


def resolve_browser() -> tuple[Optional[str], str]:
    """Return (executable_path, user_data_dir) to pass to Playwright.

    .env overrides take precedence. Falls back to auto-detection.
    If no system browser is found, returns (None, 'browser_session/')
    so Playwright uses its bundled Chromium with a persistent session dir.
    """
    exe      = BROWSER_EXECUTABLE  or _find_browser_executable()
    data_dir = BROWSER_PROFILE_DIR or _find_profile_dir(exe) or str(SESSION_DIR)

    if exe:
        logger.info("🌐 Browser : %s", exe)
    else:
        logger.info("🌐 Browser : Playwright bundled Chromium (no system browser found)")
    logger.info("📁 Profile : %s", data_dir)
    return exe, data_dir


# ── Slack helpers ─────────────────────────────────────────────────────────────

async def fetch_live_emoji_list(page: Page) -> Set[str]:
    """Retrieve the set of currently active emoji names from the Slack API.

    Uses the browser context to perform an authenticated fetch, which
    automatically includes session cookies.
    """
    try:
        token    = await page.evaluate("window.TS.boot_data.api_token")
        script   = f"fetch('/api/emoji.list?token={token}').then(r => r.json())"
        response = await page.evaluate(script)
        if response.get("ok"):
            return set(response["emoji"].keys())
    except Exception as exc:
        logger.warning("Could not fetch live emoji list: %s", exc)
    return set()


# ── Main upload mission ───────────────────────────────────────────────────────

async def execute_upload_mission() -> None:
    """Manage the end-to-end browser automation for emoji deployment."""
    if not NAMED_DIR.exists():
        logger.error("❌ Directory '%s' does not exist. Run the renamer first.", NAMED_DIR)
        return

    targets = sorted(
        f for f in NAMED_DIR.iterdir()
        if f.is_file()
        and not f.name.startswith(".")
        and f.stem not in EXCLUDE_ASSETS
    )

    if not targets:
        logger.info("🎉 No emojis found for upload in '%s'.", NAMED_DIR)
        return

    workspace_url = f"https://{SLACK_WORKSPACE}.slack.com"
    emoji_page    = f"{workspace_url}/customize/emoji"

    exe, data_dir = resolve_browser()
    SESSION_DIR.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        launch_kwargs: dict = {
            "user_data_dir": data_dir,
            "headless":      False,
            "slow_mo":       200,
            "ignore_default_args": ["--enable-automation"],
            "args":          ["--disable-blink-features=AutomationControlled"],
        }
        if exe:
            launch_kwargs["executable_path"] = exe

        logger.info("🚀 Launching browser...")
        context = await pw.chromium.launch_persistent_context(**launch_kwargs)

        # Enforce a single tab to avoid workspace-mismatch ghost uploads
        page = context.pages[0]
        for extra in context.pages[1:]:
            await extra.close()

        logger.info("🔗 Navigating to %s", emoji_page)
        await page.goto(emoji_page, wait_until="commit")

        print("\n" + "═" * 60)
        print("  ACTION REQUIRED")
        print("  1. Make sure you are logged into Slack in the browser.")
        print("  2. Navigate to the custom emoji page if not already there.")
        print("  3. Press ENTER in this terminal when ready.")
        print("═" * 60)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "\nPress ENTER to start upload...")

        success_count = skip_count = fail_count = 0

        live_list = await fetch_live_emoji_list(page)
        logger.info("📊 Workspace currently has %d custom emojis.", len(live_list))

        for i, filepath in enumerate(targets, start=1):
            emoji_name = filepath.stem

            if emoji_name in live_list:
                logger.info("⏭  [%d/%d] Already live — skipping :%s:", i, len(targets), emoji_name)
                skip_count += 1
                continue

            logger.info("📦 [%d/%d] Uploading :%s:", i, len(targets), emoji_name)

            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

                add_btn = page.locator("[data-qa='customize_emoji_add_button']").first
                await add_btn.wait_for(state="visible", timeout=10_000)
                await add_btn.click(force=True)

                await page.locator("input[type='file']").first.set_input_files(
                    str(filepath.resolve())
                )
                await page.locator("[data-qa='customize_emoji_name_input']").first.fill(
                    emoji_name
                )

                save_btn = page.locator("[data-qa='customize_emoji_save_button']").first
                await save_btn.click()

                # Success confirmed only when the modal dismisses
                await add_btn.wait_for(state="visible", timeout=15_000)
                logger.info("   ✅ Verified: :%s:", emoji_name)
                success_count += 1

            except Exception as exc:
                logger.warning("   ❌ Failed: :%s: — %s", emoji_name, exc)
                fail_count += 1
                await page.keyboard.press("Escape")

            await asyncio.sleep(UPLOAD_DELAY)

        logger.info("\n%s", "═" * 60)
        logger.info("  UPLOAD COMPLETE")
        logger.info("  ✅ Uploaded : %d", success_count)
        logger.info("  ⏭  Skipped  : %d  (already in workspace)", skip_count)
        logger.info("  ❌ Failed   : %d", fail_count)
        logger.info("%s", "═" * 60)

        await context.close()


if __name__ == "__main__":
    if not SLACK_WORKSPACE:
        logger.error("SLACK_WORKSPACE is not set in .env")
    else:
        asyncio.run(execute_upload_mission())
