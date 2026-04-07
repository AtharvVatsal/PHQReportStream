# HP Police ReportStream v4.0.0

<p align="center">
  <img src="assets/Himachal_Pradesh_Police_Logo.png" alt="HP Police ReportStream" width="300"/>
</p>

<p align="center">
  <strong>One Report. Twelve Fields. Zero Manual Work.</strong>
</p>

---

> AI-Powered Desktop Application for Processing Himachal Pradesh Police IRBn/Bn Daily Reports

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [AI Modes](#ai-modes)
4. [Quick Start](#quick-start)
5. [Installation](#installation)
6. [Usage Guide](#usage-guide)
7. [Report Format](#report-format)
8. [System Requirements](#system-requirements)
9. [Technology Stack](#technology-stack)
10. [Project Structure](#project-structure)
11. [Troubleshooting](#troubleshooting)
12. [Contributing](#contributing)
13. [License](#license)
14. [Acknowledgments](#acknowledgments)

---

## Overview

HP Police ReportStream is a standalone desktop application designed to automate the extraction and processing of daily IRBn/Bn reports from Himachal Pradesh Police battalions. Using a multi-tier AI pipeline, it automatically extracts 12 critical fields from free-text reports, validates the data, and exports professional documents in multiple formats.

### The Problem

Every day, HP Police battalions submit daily status reports via WhatsApp. These reports contain 12 fields that traditionally require:
- **15-20 minutes** per report to process manually
- Error-prone manual data entry
- No standardized format across battalions
- Difficult to search or analyze historical data

### The Solution

HP Police ReportStream transforms this manual process into an automated workflow that processes reports in **seconds**, with accuracy rates up to **95%** when using LLM mode.

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **AI Modes** | Three extraction modes: Fast, Accurate, and LLM |
| **12-Field Extraction** | Automatically extracts all standard IRBn/Bn fields |
| **Format Detection** | Automatically detects report format (v1/v2) |
| **Typo Correction** | 10,000+ field-specific corrections |
| **Cross-field Validation** | Validates consistency between extracted fields |
| **PDF Export** | Professional HP Police styled documents |
| **Excel Export** | Color-coded confidence scores |
| **Batch Processing** | Process multiple reports at once |
| **Analytics Dashboard** | View statistics, search, and filter reports |
| **Template System** | Pre-defined report templates |
| **Offline Capability** | Works without internet (LLM mode optional) |

### Export Formats

- **PDF** - Professional document with HP Police branding
- **Excel** - Spreadsheet with color-coded confidence scores
- **CSV** - Plain text format for data analysis
- **JSON** - Machine-readable format for integration

---

## AI Modes

HP Police ReportStream offers three AI modes, each with different trade-offs between speed and accuracy:

| Mode | Technology | Speed | Accuracy | Setup Required |
|------|------------|-------|----------|----------------|
| **Fast** | Regex + Typo Dictionary | ~1 second | ~70% | None |
| **Accurate** | spaCy NER + BERT | ~5 seconds | ~85% | Download spaCy model |
| **LLM** | Ollama + Mistral | ~30 seconds | ~95% | Install Ollama + Mistral |

### Mode Selection

1. **Fast Mode (Default)** - Best for quick processing, no additional setup needed
2. **Accurate Mode** - Recommended for most users, requires downloading spaCy model (~100MB)
3. **LLM Mode** - Best accuracy, requires installing Ollama and downloading Mistral model (~4GB)

---

## Quick Start

### Option 1: Pre-built Installer (Recommended)

1. Download `HPReportStream_Setup_v4.0.0.exe` from the `output` folder
2. Run the installer
3. Launch from Desktop shortcut or Start Menu
4. Select AI mode and start processing reports!

### Option 2: Python Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/PHQReportStream.git
cd PHQReportStream

# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python run_app.py
```

---

## Installation

### Pre-built Installer

1. Navigate to the `output` folder
2. Run `HPReportStream_Setup_v4.0.0.exe`
3. Follow the installation wizard
4. Launch the application

### Setting Up AI Modes

#### Fast Mode (No Setup Required)
- Works out of the box
- No additional downloads needed

#### Accurate Mode

```bash
# Download spaCy transformer model
python -m spacy download en_core_web_trf
```

#### LLM Mode

1. **Download Ollama**: https://ollama.com/download/windows
2. **Pull Mistral Model**:
   ```bash
   ollama pull mistral
   ```
3. **Start Ollama Service** (before using LLM mode):
   ```bash
   ollama serve
   ```

---

## Usage Guide

### Processing a Report

1. **Launch the Application**
   - Double-click Desktop shortcut, OR
   - Go to Start Menu → HP Police ReportStream

2. **Select AI Mode**
   - Click the AI Mode dropdown
   - Choose: Fast | Accurate | LLM

3. **Enter Report Text**
   - Paste your IRBn/Bn report in the text area

4. **Process**
   - Click "Process Report" button

5. **View Results**
   - Extracted fields appear in the table
   - Confidence scores show reliability:
     - 🟢 Green: >=70% (high confidence)
     - 🟡 Yellow: 50-70% (medium)
     - 🔴 Red: <50% (low confidence)

6. **Export**
   - Click: PDF | Excel | CSV | JSON

### Using Batch Processing

1. Go to **Batch Processing** tab
2. Paste multiple reports (separated by double newlines or numbered format)
3. Click **Process All**

### Using Analytics

1. Go to **Analytics** tab
2. View statistics: Total reports, Average confidence, High confidence count
3. Search by keyword or filter by district/confidence

### Admin Settings

1. Click **Settings** → **Admin Settings**
2. Enter password: `admin@123`
3. Configure: AI defaults, auto-save, webhook URL

---

## Report Format

The application processes standard HP Police IRBn/Bn daily reports with the following structure:

```
Name of IRBn/Bn: 1st HPAP BN Junga, Shimla

1. Reserves Deployed: Yes
2. Districts where force deployed: Shimla, Kangra
3. Stay Arrangement/Bathrooms: Good
4. Messing: Good
5. CO's last Interaction with SP: 05.04.2026
6. Disciplinary Issues: Nil
7. Reserves Detained: Nil
8. Training: Nil
9. Welfare: Nil
10. Reserves Available: Yes
11. Issue for PHQ: Nil
```

### Supported Formats

- **v1 Format**: Numbered format (1., 2., 3.)
- **v2 Format**: Labeled format (Name of IRBn/Bn:, etc.)
- **Date Formats**: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
- **District Aliases**: Shimla/Simla, Sirmaur/Sirmour, etc.
- **Nil Variants**: Nil, None, N/A, -, empty

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|--------------|
| **Operating System** | Windows 7 | Windows 10/11 |
| **Processor** | Intel Core i3 | Intel Core i5+ |
| **RAM** | 4 GB | 8 GB |
| **Disk Space** | 200 MB | 500 MB |
| **Display** | 1024x768 | 1280x720 |

### Additional Requirements by Mode

| Mode | Additional Requirements |
|------|------------------------|
| Fast | None |
| Accurate | ~100 MB for spaCy models |
| LLM | ~4 GB for Ollama + Mistral, 8GB RAM recommended |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **GUI Framework** | PyQt5 |
| **Database** | SQLite |
| **ORM** | SQLAlchemy |
| **PDF Generation** | ReportLab |
| **Excel Export** | openpyxl |
| **NLP - Regex** | re / pattern |
| **NLP - NER** | spaCy |
| **NLP - BERT** | Transformers |
| **LLM** | Ollama + Mistral |
| **Build** | PyInstaller |
| **Installer** | Inno Setup |

---

## Project Structure

```
PHQReportStream/
├── app/
│   ├── core/           # Configuration
│   ├── data/           # Static data files
│   ├── gui/            # PyQt5 GUI components
│   ├── models/         # Data models/schemas
│   └── services/       # Business logic services
│       ├── ai_coordinator.py    # AI pipeline orchestration
│       ├── bert_extractor.py  # BERT extraction
│       ├── exporter_service.py # Export services
│       ├── extractor.py        # Regex extraction
│       ├── llm_service.py      # Ollama LLM
│       ├── ner_service.py      # spaCy NER
│       ├── pdf_service.py      # PDF generation
│       ├── typo_service.py     # Typo corrections
│       └── validation_service.py # Field validation
├── assets/              # Logo images
├── dist/               # Built executable
├── installer/          # Inno Setup scripts
├── output/             # Installer output
├── run_app.py          # Application entry point
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

---

## Troubleshooting

### Application Won't Start

- **Run as Administrator**: Right-click → Run as administrator
- **Install Visual C++ Redistributable**: Download from Microsoft

### Ollama Not Detected

- **Start Ollama Service**: Open Command Prompt, type `ollama serve`
- **Check Status**: Open browser, go to http://localhost:11434

### spaCy Model Not Found

```bash
python -m spacy download en_core_web_trf
```

### Slow Performance

- Use **Fast mode** for quicker processing
- Close other applications to free RAM

### PDF Export Error

```bash
pip install reportlab==4.2.5
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is developed for internal HP Police use.

---

## Acknowledgments

- Himachal Pradesh Police IT Department
- All battalions and units providing feedback
- Open source communities for PyQt5, spaCy, and other libraries

---

## Support

For issues and questions:
- Contact the IT Department
- Contact Atharv Vatsal
---

<p align="center">
  <strong>HP Police ReportStream v4.0.0</strong><br/>
  Made with ❤️ for Himachal Pradesh Police
</p>
