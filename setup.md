# HP Police ReportStream - Setup Guide

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Installation](#quick-installation)
3. [Setting Up AI Modes](#setting-up-ai-modes)
4. [Running the Application](#running-the-application)
5. [Quick Reference](#quick-reference)

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|--------------|
| OS | Windows 7 | Windows 10/11 |
| RAM | 4 GB | 8 GB |
| Disk Space | 200 MB | 500 MB |

---

## Quick Installation

### Step 1: Download Installer
Get `HPReportStream_Setup_v4.0.0.exe` from the output folder.

### Step 2: Run Installer
1. Double-click the installer
2. Click **Next** through all screens
3. Click **Install**
4. Click **Finish**

### Step 3: Launch Application
- Double-click **Desktop shortcut**, OR
- Go to **Start Menu** → **HP Police ReportStream**

**That's it! Fast mode works immediately!**

---

## Setting Up AI Modes

### Option A: Fast Mode (Default) ✓
- **No setup needed**
- Ready immediately
- Speed: ~1 second | Accuracy: ~70%

---

### Option B: Accurate Mode

```bash
# Open Command Prompt and run:
python -m spacy download en_core_web_trf
```

- Downloads ~100MB
- Speed: ~5 seconds | Accuracy: ~85%

---

### Option C: LLM Mode

#### Step 1: Install Ollama
1. Go to: https://ollama.com/download/windows
2. Download and run OllamaSetup.exe
3. Click Install → Close

#### Step 2: Download Model
```bash
# Open Command Prompt
ollama pull mistral
```
- Downloads ~4GB (takes 5-30 minutes)

#### Step 3: Start Ollama
```bash
# Before using LLM mode, run:
ollama serve
```

- Keep this window open while using LLM mode
- Speed: ~30 seconds | Accuracy: ~95%

---

## Running the Application

1. **Launch**: Double-click shortcut
2. **Select Mode**: Fast / Accurate / LLM
3. **Paste Report**: Enter IRBn/Bn report text
4. **Process**: Click "Process Report"
5. **Export**: Save as PDF/Excel/CSV/JSON

---

## Quick Reference

| Task | Action |
|------|--------|
| Start App | Double-click shortcut |
| Fast Mode | Select "Fast" - ready immediately |
| Accurate Mode | Select "Accurate" - needs spaCy |
| LLM Mode | Start Ollama first, then select "LLM" |
| Export PDF | Click "Export PDF" |
| Admin Settings | Settings → admin@123 |

---

**Version:** 4.0.0 | **Date:** April 7, 2026
