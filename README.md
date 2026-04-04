# Slack Emoji Pipeline

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Playwright](https://img.shields.io/badge/Playwright-45ba4b?style=for-the-badge&logo=Playwright&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-11557c?style=for-the-badge&logo=Python&logoColor=white)
![uv](https://img.shields.io/badge/uv-000000?style=for-the-badge&logo=rust&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

An automated 3-stage pipeline for transforming raw assets into production-grade Slack emojis. Resolves common regressions in transparency, aspect ratio, and GIF complexity.

---

## 🚀 Setup and Installation

### 1. Environment Configuration
This project utilizes [uv](https://github.com/astral-sh/uv) for modern, high-performance Python package management.
```bash
# Clone the repository
git clone <your-url>
cd slack-emoji-pipeline

# Sync environment and install browser binaries
uv sync
uv run playwright install chromium
```

### 2. Configure Your Environment
Copy the template and define your workspace variables:
```bash
cp .env.example .env
```

---

## 🛠️ The Pipeline Workflow

### Phase 1: Intake & Sanitization
Place raw image files (PNG, JPG, GIF, WebP) into the `/emojis` directory.
```bash
mkdir emojis
uv run sanitizer.py
```

### Phase 2: Identification & Naming
Execute the interactive wizard to identify and namespace your sanitized assets.
```bash
uv run renamer.py
```

### Phase 3: Deployment
Automate the mass-upload to your configured Slack workspace.
```bash
uv run uploader.py
```

---

## 🧪 Logic Verification
Execute logic verification tests to ensure the engine state is healthy:
```bash
uv run python -m unittest discover tests
```

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for details.
