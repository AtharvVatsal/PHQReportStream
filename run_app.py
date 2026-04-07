#!/usr/bin/env python
"""
HP Police ReportStream - Desktop Application Launcher

Usage:
    python run_app.py

This launches the PyQt5 desktop application.
"""

import sys
import os
from pathlib import Path

# Add current directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Launch the desktop application."""
    print("=" * 60)
    print("  HP Police ReportStream v3.0.0")
    print("  Desktop Application")
    print("=" * 60)
    print()
    
    # Import and run the GUI
    from app.gui.main_window import run_app
    
    run_app()


if __name__ == "__main__":
    main()
