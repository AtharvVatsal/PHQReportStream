# Installer Scripts

This folder contains the Inno Setup script to build the Windows installer.

## Contents

| File/Folder | Description |
|-------------|-------------|
| `HPReportStream.iss` | Inno Setup script |
| `assets/` | Logo images for installer |
| `build_installer.bat` | Build script |
| `installer/` | (Empty - for Inno Setup output) |
| `models/` | (Ignored - spaCy model downloaded during install) |

## Building the Installer

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Open `HPReportStream.iss` in Inno Setup
3. Click Build → Compile
4. Installer will be created in `../output/`

## Model Download

The spaCy model (~100MB) is **downloaded automatically** during installation when the user selects "Download spaCy AI Model" in the installer.

The LLM model (~4GB) is downloaded separately via Ollama.

## Notes

- `installer/models/` folder is excluded from git (478MB spaCy model)
- The model is downloaded via the installer script
- Users can also download models manually if needed
