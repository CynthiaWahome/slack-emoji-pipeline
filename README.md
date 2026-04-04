# 🤖 Slack Emoji Engine

A professional-grade, 3-stage pipeline for transforming raw images into high-quality, optimized Slack emojis. This engine is designed to bypass Slack's hidden complexity limits while maintaining pixel-perfect visual integrity.

## 🏗️ Core Philosophy: Total Collection Integrity
**All emojis intended for the workspace should be added to this pipeline.** This ensures that every asset—whether a simple logo or a complex 137-frame animation—is standardized for dimensions, transparency, and file-size compliance.

---

## 🛠️ The 3-Stage Pipeline

### **Stage 1: Sanitise (`1_sanitise.py`)**
The "Factory" stage. It handles the heavy mathematical lifting:
*   **Flood-Fill Transparency:** Corner-seeded algorithm that removes backgrounds while protecting internal white content (e.g., logos).
*   **Global Bounding Box:** Union-based cropping across all frames to eliminate animation jitter.
*   **Canvas Squaring:** Automatic transparent padding to 1:1 ratio to prevent "tiny" emoji rendering.
*   **Frame Decimation:** Intelligent frame-dropping to stay under Slack's 50-frame limit.

### **Stage 2: Rename (`2_rename.py`)**
The "Identity" stage. An interactive CLI wizard:
*   **Visual Previews:** Automatically opens assets in macOS Preview for identification.
*   **Dynamic Namespacing:** Wraps names in configurable Prefixes/Suffixes (defined in `.env`).
*   **Collision Guard:** Prevents accidental overwrites of existing assets.

### **Stage 3: Upload (`3_upload_playwright.py`)**
The "Deployment" stage. A high-stability Playwright robot:
*   **API Guard:** Queries the Slack workspace first to skip existing duplicates.
*   **Honest Verification:** Confirms UI state before logging success to prevent "Ghost Uploads."
*   **Single-Tab Mandate:** Aggressively manages browser tabs for stability.

---

## 🚀 Getting Started

1. **Setup Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure `.env`:**
   Copy `.env.example` to `.env` and set your `SLACK_WORKSPACE` and `NAMESPACE_PREFIX`.

3. **Execution:**
   ```bash
   # Stage 1
   python3 1_sanitise.py
   # Stage 2
   python3 2_rename.py
   # Stage 3
   python3 3_upload_playwright.py
   ```

## 🧪 Testing
The engine includes a full suite of logic tests. To verify the engine state:
```bash
python3 -m unittest discover tests
```
