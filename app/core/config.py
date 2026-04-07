"""Application configuration for desktop app."""

import os
from pathlib import Path


class Settings:
    """Desktop application settings."""
    
    APP_NAME = "HP Police ReportStream"
    VERSION = "4.0.0"
    
    DB_FILE = "phq_reports.db"
    
    AUTO_SAVE_ENABLED = True
    AUTO_SAVE_DELAY = 1
    
    AI_MODE = "fast"
    AI_MODES = ["fast", "accurate", "llm"]
    AI_ENABLED = False
    AI_MODEL = "all-MiniLM-L6-v2"
    SPACY_MODEL = "en_core_web_trf"
    OLLAMA_MODEL = "mistral"
    OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
    
    BATCH_SEPARATOR_PATTERNS = [
        r'^\d+\.',
        r'^Report\s*\d+',
        r'---',
    ]
    
    DEFAULT_EXPORT_PATH = ""
    PDF_STYLE = "police"
    
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    THEME = "light"
    
    SEARCH_DEBOUNCE = 300
    MAX_SEARCH_RESULTS = 100
    
    @classmethod
    def get_db_path(cls) -> str:
        return cls.DB_FILE
    
    @classmethod
    def get_template_path(cls) -> str:
        return str(Path(__file__).parent.parent / "data" / "templates.json")
    
    @classmethod
    def set_ai_mode(cls, mode: str) -> bool:
        if mode in cls.AI_MODES:
            cls.AI_MODE = mode
            return True
        return False


settings = Settings()
