# Slack Emoji Pipeline

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Playwright](https://img.shields.io/badge/Playwright-45ba4b?style=for-the-badge&logo=Playwright&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-11557c?style=for-the-badge&logo=Python&logoColor=white)
![uv](https://img.shields.io/badge/uv-000000?style=for-the-badge&logo=rust&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

A high-fidelity, 3-stage automated pipeline for transforming raw image assets into production-grade Slack emojis. This engine automatically resolves common quality regressions including jittery animations, jagged transparency, and incorrect aspect ratios.

---

## Core Philosophy: Collection Integrity
To maintain a high-quality Slack workspace, all emojis must be processed through this pipeline. The engine ensures every asset complies with Slack's internal rendering constraints and complexity limits.

---

## The 3-Stage Pipeline

### Stage 1: Sanitization (sanitizer.py)
**Intake:** Place raw source files (PNG, JPG, GIF, WebP) into the `/emojis` directory.
- **Action:** The factory engine crops "empty air," pads images to 1:1 squares, and applies corner-seeded flood-fill transparency.
- **Optimization:** Automatically decimates frames in oversized GIFs to bypass Slack's 50-frame processing wall.

### Stage 2: Identification (renamer.py)
- **Action:** An interactive CLI wizard that initiates macOS Preview for visual identification.
- **Namespacing:** Automatically applies the custom `{PREFIX}{name}{SUFFIX}` pattern defined in the environment configuration.

### Stage 3: Deployment (uploader.py)
- **Action:** A Playwright-based automation tool that utilizes a persistent Brave browser profile.
- **API Guard:** Queries the Slack workspace to skip existing duplicates and verify server-side acceptance.

---

## Installation and Setup

### 1. Environment Configuration
This project utilizes [uv](https://github.com/astral-sh/uv) for high-performance Python package management.
```bash
# Initialize environment and install dependencies
uv sync

# Install browser binaries for Playwright
uv run playwright install chromium
```

### 2. Asset Preparation
Create the intake directory and add raw assets:
```bash
mkdir emojis
# [Action] Place raw image files into the /emojis directory
```

### 3. Configuration
Copy the environment template and define the target workspace:
```bash
cp .env.example .env
# Configure SLACK_WORKSPACE and NAMESPACE_PREFIX in .env
```

### 4. Execution
```bash
uv run sanitizer.py
uv run renamer.py
uv run uploader.py
```

---

## Testing
Execute logic verification tests:
```bash
uv run python -m unittest discover tests
```

---

## Project Structure
- `/emojis`: [Intake] Raw, unprocessed source files.
- `/emojis_ready`: [Work] Sanitized files awaiting identification.
- `/emojis_named`: [Deploy] Final assets ready for Slack deployment.
- `/notes`: [History] Technical journals and forensic reports.

---

## License
Distributed under the MIT License. See `LICENSE` for more information.
