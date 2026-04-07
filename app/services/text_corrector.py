"""Text Corrector - Spell and grammar correction for desktop app."""

import re
from typing import List, Dict
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


class TextCorrector:
    def __init__(self):
        self.grammar_patterns = self._load_grammar_patterns()
    
    def _load_grammar_patterns(self) -> List[Dict]:
        return [
            {'pattern': r'\bi\s+', 'replacement': 'I ', 'description': 'Capitalize standalone "i"'},
            {'pattern': r'\s+', 'replacement': ' ', 'description': 'Fix multiple spaces'},
            {'pattern': r'\.{2,}', 'replacement': '.', 'description': 'Fix multiple periods'},
            {'pattern': r',{2,}', 'replacement': ',', 'description': 'Fix multiple commas'},
            {'pattern': r'-{2,}', 'replacement': '-', 'description': 'Fix multiple hyphens'},
            {'pattern': r'\(\s+', 'replacement': '(', 'description': 'Fix space after opening paren'},
            {'pattern': r'\s+\)', 'replacement': ')', 'description': 'Fix space before closing paren'},
            {'pattern': r'^([a-z])', 'replacement': lambda m: m.group(1).upper(), 'description': 'Capitalize first letter'},
            {'pattern': r'(?<=[.!?])\s*([a-z])', 'replacement': lambda m: ' ' + m.group(1).upper(), 'description': 'Capitalize after sentence'},
        ]
    
    def correct_spelling(self, text: str) -> str:
        if not text or len(text) < 2:
            return text
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            if len(word) < 4:
                corrected_words.append(word)
                continue
            
            if word.isdigit():
                corrected_words.append(word)
                continue
            
            word_lower = word.lower()
            
            common_typos = {
                'teh': 'the',
                'recieve': 'receive',
                'definate': 'definite',
                'definately': 'definitely',
                'occured': 'occurred',
                'seperate': 'separate',
                'acommodate': 'accommodate',
                'begining': 'beginning',
                'beleive': 'believe',
                'belive': 'believe',
                'curtosy': 'courtesy',
                'enviroment': 'environment',
                'goverment': 'government',
                'grammer': 'grammar',
                'independant': 'independent',
                'intresting': 'interesting',
                'judgement': 'judgment',
                'knowlege': 'knowledge',
                'neccessary': 'necessary',
                'occassion': 'occasion',
                'oportunity': 'opportunity',
                'posession': 'possession',
                'prefered': 'preferred',
                'priviledge': 'privilege',
                'publically': 'publicly',
                'relevent': 'relevant',
                'succesful': 'successful',
                'tommorow': 'tomorrow',
                'tommorrow': 'tomorrow',
                'truely': 'truly',
                'writting': 'writing',
                'messing': 'mess',
                'passing': 'mess',
            }
            
            if word_lower in common_typos:
                corrected_words.append(common_typos[word_lower])
                continue
            
            if word in ['HPAP', 'BN', 'IRBn', 'PHQ', 'AP&T', 'CO', 'SP', 'HC', 'SI', 'CT']:
                corrected_words.append(word)
                continue
            
            if word_lower in ['shimla', 'kangra', 'mandi', 'bilaspur', 'hamirpur', 'una', 'chamba', 'kullu', 'solan', 'sirmaur', 'kinnaur', 'lahaul', 'spiti']:
                corrected_words.append(word)
                continue
            
            corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def fix_grammar_patterns(self, text: str) -> str:
        if not text:
            return text
        
        result = text
        
        for pattern in self.grammar_patterns:
            try:
                if callable(pattern.get('replacement')):
                    result = re.sub(pattern['pattern'], pattern['replacement'], result)
                else:
                    result = re.sub(pattern['pattern'], pattern['replacement'], result)
            except Exception:
                continue
        
        result = re.sub(r'\s+', ' ', result)
        return result.strip()
    
    def improve_readability(self, text: str) -> str:
        if not text or len(text) < 3:
            return text
        
        result = text
        result = re.sub(r'\s*-\s*', ' - ', result)
        result = re.sub(r'\s*,\s*', ', ', result)
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def get_corrections(self, text: str, field_key: str) -> List[Correction]:
        corrections = []
        
        if not text or len(text) < 2:
            return corrections
        
        original = text
        
        grammar_fixed = self.fix_grammar_patterns(text)
        if grammar_fixed != original:
            corrections.append(Correction(
                original=original,
                corrected=grammar_fixed,
                type='grammar',
                field_key=field_key
            ))
            text = grammar_fixed
        
        spell_corrected = self.correct_spelling(text)
        if spell_corrected != text:
            corrections.append(Correction(
                original=text,
                corrected=spell_corrected,
                type='spelling',
                field_key=field_key
            ))
            text = spell_corrected
        
        readability_fixed = self.improve_readability(text)
        if readability_fixed != text:
            corrections.append(Correction(
                original=text,
                corrected=readability_fixed,
                type='readability',
                field_key=field_key
            ))
        
        return corrections


text_corrector = TextCorrector()


def get_text_corrector() -> TextCorrector:
    return text_corrector
