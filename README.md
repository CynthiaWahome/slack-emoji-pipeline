# Slack Emoji Pipeline

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Playwright](https://img.shields.io/badge/Playwright-45ba4b?style=for-the-badge&logo=Playwright&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-11557c?style=for-the-badge&logo=Python&logoColor=white)
![uv](https://img.shields.io/badge/uv-000000?style=for-the-badge&logo=rust&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

A simple tool to standardize your entire emoji collection and transform raw images and GIFs into perfect Slack emojis. This engine automatically fixes common problems like blurry backgrounds, tiny icons, and GIFs that are too large to upload—ensuring every emoji fits Slack's requirements perfectly.

---

## 🚀 Getting Started

### 1. Environment Setup
This project utilizes [uv](https://github.com/astral-sh/uv) for modern, high-performance Python package management.
```bash
# Clone the repository
git clone https://github.com/CynthiaWahome/slack-emoji-pipeline.git
cd slack-emoji-pipeline

# Sync environment and install browser binaries
uv sync
uv run playwright install chromium
```

### 2. Prepare Your Emojis (Required)
**Crucial:** Create an `/emojis` directory in the root and place all your raw images/GIFs inside. The pipeline depends on this folder to start the process.
```bash
mkdir emojis
# [Action] Place raw image files into the /emojis directory
```

### 3. Configure Your Environment
Copy the template and define your workspace variables:
```bash
cp .env.example .env
# [Action] Edit .env to set SLACK_WORKSPACE and NAMESPACE_PREFIX
```

---

## 🛠️ The Pipeline Workflow

Execute the stages in order. Stage 2 is optional if your files are already named.

| Stage | Command | Input Folder | Output Folder |
| :--- | :--- | :--- | :--- |
| **1. Sanitise** | `uv run src/slack_emoji_pipeline/sanitizer.py` | `/emojis` | `/emojis_ready` |
| **2. Rename** | `uv run src/slack_emoji_pipeline/renamer.py` | `/emojis_ready` | `/emojis_named` |
| **3. Deploy** | `uv run src/slack_emoji_pipeline/uploader.py` | `/emojis_named` | Slack |

> 🏗️ **The Namespace Principle:** We recommend using a consistent prefix (e.g., `acme_`) during Stage 2. This prevents name collisions and allows for surgical mass-deletion if you ever need to reset your library.

---

## Additional Tools

> 💡 **Lightweight Alternative:** For browser-based management without the full Python pipeline, see the [Slack Emoji Toolkit Gist](https://gist.github.com/CynthiaWahome/7cef9951dd0cb7ed3caaf0e63d7774a7) for workspace-aware bulk uploading and surgical mass deletion via the console.

---

## 🧪 Logic Verification
Execute logic verification tests to ensure the engine state is healthy:
```bash
uv run python -m unittest discover tests
```

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for details.
