# 🤖 Slack Emoji Pipeline

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

A professional, 3-stage automated pipeline for transforming raw image assets into high-fidelity Slack emojis. This engine automatically resolves common quality regressions including jittery animations, jagged transparency, and incorrect aspect ratios.

---

## 🏗️ Core Philosophy: Collection Integrity
To maintain a high-quality Slack workspace, **all emojis must be processed through this pipeline.** The engine ensures every asset complies with Slack's internal rendering constraints and complexity limits.

---

## 🛠️ The 3-Stage Pipeline

### **Stage 1: Sanitization** (`sanitizer.py`)
**Intake:** Place your raw source files (PNG, JPG, GIF, WebP) into the `/emojis` directory.
- **Action:** The factory engine crops "empty air," pads images to perfect 1:1 squares, and applies corner-seeded flood-fill transparency.
- **Optimization:** Automatically decimates frames in oversized GIFs to bypass Slack's hidden 50-frame limit.

### **Stage 2: Identification** (`renamer.py`)
- **Action:** An interactive CLI wizard that pops open every sanitized asset in macOS Preview for visual identification.
- **Namespacing:** Automatically applies your custom `{PREFIX}{name}{SUFFIX}` (e.g., `cy_...`) defined in your environment.

### **Stage 3: Deployment** (`uploader.py`)
- **Action:** A Playwright-based robot that takes control of a persistent Brave browser profile to perform the manual upload work.
- **API Guard:** Queries the Slack workspace before every action to skip duplicates and verify server-side success.

---

## 🚀 Quick Start

### **1. Setup Environment**
This project uses [**uv**](https://github.com/astral-sh/uv) for ultra-fast, modern Python management.
```bash
# Install dependencies and setup venv
uv sync
# Install browser binaries
uv run playwright install chromium
```

### **2. Prepare Your Emojis**
Create the intake folder and drop your raw files inside:
```bash
mkdir emojis
# [Action] Drop your raw PNG/GIF/WebP files into /emojis
```

### **3. Configuration**
Copy the environment template and set your Slack workspace domain:
```bash
cp .env.example .env
# Edit .env to set SLACK_WORKSPACE and NAMESPACE_PREFIX
```

### **4. Run the Pipeline**
```bash
uv run sanitizer.py
uv run renamer.py
uv run uploader.py
```

---

## 🧪 Testing
To verify the engine logic:
```bash
uv run python -m unittest discover tests
```

---

## 📂 Project Structure
- `/emojis`: **[INTAKE]** Your raw, unprocessed source files.
- `/emojis_ready`: **[WORK]** Sanitized files waiting for a human name.
- `/emojis_named`: **[DEPLOY]** Final assets ready for Slack upload.
- `/notes`: **[DOCS]** Full engineering journals and forensic reports.

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
