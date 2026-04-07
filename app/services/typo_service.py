"""Enhanced Typo Service - Field-specific typo correction using large dictionary."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Correction:
    """Represents a single text correction."""
    original: str
    corrected: str
    type: str
    field_key: str
    
    def has_change(self) -> bool:
        return self.original.strip().lower() != self.corrected.strip().lower()


class TypoService:
    """Enhanced typo correction service with field-specific context."""
    
    def __init__(self, dictionary_path: Optional[str] = None):
        self.dictionary: Dict[str, Dict[str, str]] = {}
        self.field_contexts = {
            "unit_name": ["police", "districts"],
            "reserves_deployed": ["police"],
            "districts": ["districts"],
            "stay_arrangement": ["quality"],
            "messing": ["quality"],
            "co_interaction_date": ["dates"],
            "disciplinary_issues": ["nil_values", "police"],
            "reserves_detained": ["nil_values", "police"],
            "training": ["nil_values", "police"],
            "welfare": ["nil_values", "police"],
            "reserves_available": ["nil_values", "police"],
            "issues_for_phq": ["nil_values", "police"]
        }
        self._load_dictionary(dictionary_path)
    
    def _load_dictionary(self, dictionary_path: Optional[str] = None):
        """Load typo dictionary from JSON file."""
        if dictionary_path is None:
            dictionary_path = str(Path(__file__).parent.parent / "data" / "typo_dictionary.json")
        
        try:
            with open(dictionary_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
        except FileNotFoundError:
            self.dictionary = self._get_builtin_dictionary()
    
    def _get_builtin_dictionary(self) -> Dict[str, Dict[str, str]]:
        """Fallback builtin dictionary."""
        return {
            "general": {
                "recieve": "receive",
                "occured": "occurred",
                "seperate": "separate"
            },
            "districts": {
                "simla": "Shimla",
                "sirmour": "Sirmaur"
            }
        }
    
    def correct(self, text: str, field_key: Optional[str] = None) -> str:
        """Correct typos in text with optional field context."""
        if not text or len(text) < 2:
            return text
        
        corrected = text
        
        contexts = self.field_contexts.get(field_key, ["general"]) if field_key else ["general"]
        if "nil_values" in contexts and field_key:
            contexts = [field_key] + contexts
        
        categories_to_check = set(contexts)
        
        for category in categories_to_check:
            if category in self.dictionary:
                for typo, correction in self.dictionary[category].items():
                    pattern = re.compile(r'\b' + re.escape(typo) + r'\b', re.IGNORECASE)
                    corrected = pattern.sub(correction, corrected)
        
        corrected = self._fix_common_patterns(corrected)
        
        return corrected
    
    def _fix_common_patterns(self, text: str) -> str:
        """Fix common patterns like multiple spaces, capitalization."""
        # Preserve newlines - only fix multiple spaces within lines
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            line = re.sub(r'\s+', ' ', line)
            line = re.sub(r'\.{2,}', '.', line)
            line = re.sub(r',{2,}', ',', line)
            line = re.sub(r'-{2,}', '-', line)
            line = re.sub(r'\(\s+', '(', line)
            line = re.sub(r'\s+\)', ')', line)
            fixed_lines.append(line)
        
        text = '\n'.join(fixed_lines)
        
        if text and text[0].islower() and len(text) > 0:
            text = text[0].upper() + text[1:]
        
        return text.strip()
    
    def get_corrections(self, text: str, field_key: Optional[str] = None) -> List[Correction]:
        """Get list of corrections for text."""
        corrections = []
        
        if not text or len(text) < 2:
            return corrections
        
        original = text
        corrected = self.correct(text, field_key)
        
        if corrected != original:
            corrections.append(Correction(
                original=original,
                corrected=corrected,
                type='typo',
                field_key=field_key or "general"
            ))
        
        return corrections
    
    def normalize_nil(self, value: str) -> str:
        """Normalize nil/none values."""
        if not value:
            return "Nil"
        
        value_lower = value.lower().strip()
        
        if "nil_values" in self.dictionary:
            nil_dict = self.dictionary["nil_values"]
            if value_lower in nil_dict:
                return nil_dict[value_lower]
        
        nil_variants = ['nil', 'nill', 'none', 'n/a', 'na', '-', 'ni', 'no', 'nothing', 'zero', '0']
        if value_lower in nil_variants:
            return "Nil"
        
        return value
    
    def normalize_district(self, text: str) -> str:
        """Normalize HP district names."""
        if not text:
            return text
        
        text_lower = text.lower().strip()
        
        if "districts" in self.dictionary:
            district_dict = self.dictionary["districts"]
            for typo, proper in district_dict.items():
                if typo in text_lower:
                    return proper
        
        return text
    
    def get_dictionary_size(self) -> int:
        """Get total number of typo corrections."""
        total = 0
        for category in self.dictionary.values():
            total += len(category)
        return total


typo_service = TypoService()


def get_typo_service() -> TypoService:
    """Get the global typo service instance."""
    return typo_service
