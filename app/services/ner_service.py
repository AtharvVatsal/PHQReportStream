"""NER Service - ML-based Named Entity Recognition using spaCy."""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


HP_DISTRICTS = {
    "shimla", "simla", "kangra", "mandi", "bilaspur", "hamirpur", "una",
    "chamba", "kullu", "solan", "sirmaur", "sirmour", "kinnaur", "lahaul",
    "lahol", "spiti", "spithi"
}

HP_DISTRICT_CANONICAL = {
    "shimla": "Shimla", "simla": "Shimla",
    "kangra": "Kangra",
    "mandi": "Mandi",
    "bilaspur": "Bilaspur",
    "hamirpur": "Hamirpur", "hamir pur": "Hamirpur",
    "una": "Una",
    "chamba": "Chamba",
    "kullu": "Kullu", "kulhu": "Kullu",
    "solan": "Solan",
    "sirmaur": "Sirmaur", "sirmour": "Sirmaur",
    "kinnaur": "Kinnaur", "kinnour": "Kinnaur",
    "lahaul": "Lahaul", "lahol": "Lahaul",
    "spiti": "Spiti", "spithi": "Spiti"
}


@dataclass
class Entity:
    """Represents a named entity."""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    """Result of NER extraction."""
    unit_name: str = ""
    districts: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    numbers: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    raw_entities: List[Entity] = field(default_factory=list)


class NERService:
    """ML-based Named Entity Recognition using spaCy transformer models."""
    
    def __init__(self, model_name: str = "en_core_web_trf"):
        self._nlp = None
        self._model_name = model_name
        self._fallback_mode = False
    
    @property
    def is_available(self) -> bool:
        """Check if spaCy model is available."""
        return self._nlp is not None
    
    def initialize(self) -> bool:
        """Initialize spaCy model with safe fallback."""
        if self._nlp is not None:
            return True
        
        import spacy
        
        # Try loading smaller model first (faster, more reliable)
        for model in ["en_core_web_sm", self._model_name]:
            try:
                self._nlp = spacy.load(model)
                if model == self._model_name:
                    print(f"NER Service: Loaded {model}")
                else:
                    print(f"NER Service: Using fallback model {model}")
                    self._fallback_mode = True
                return True
            except OSError:
                continue
            except Exception as e:
                print(f"NER Service: Error loading {model}: {e}")
                continue
        
        print("NER Service: No spaCy models available, using regex fallback")
        self._nlp = None
        return False
    
    def extract_entities(self, text: str) -> ExtractionResult:
        """Extract all entity types from text."""
        if not text:
            return ExtractionResult()
        
        result = ExtractionResult()
        
        if self._nlp is not None:
            result = self._extract_with_spacy(text)
        else:
            result = self._extract_with_regex(text)
        
        result.districts = self._normalize_districts(result.districts)
        result.unit_name = self._extract_unit_name(text, result)
        
        return result
    
    def _extract_with_spacy(self, text: str) -> ExtractionResult:
        """Extract entities using spaCy model."""
        result = ExtractionResult()
        
        doc = self._nlp(text)
        
        for ent in doc.ents:
            entity = Entity(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=ent.ent_kb_id_ if hasattr(ent, 'ent_kb_id_') else 0.9
            )
            result.raw_entities.append(entity)
            
            if ent.label_ == "ORG":
                result.organizations.append(ent.text)
            elif ent.label_ == "GPE" or ent.label_ == "LOC":
                if ent.text.lower() in HP_DISTRICTS:
                    result.districts.append(ent.text)
            elif ent.label_ == "DATE":
                result.dates.append(ent.text)
            elif ent.label_ == "CARDINAL" or ent.label_ == "NUM":
                if ent.text.isdigit() or ent.text.replace(',', '').isdigit():
                    result.numbers.append(ent.text)
        
        result.districts.extend(self._extract_districts_regex(text))
        
        return result
    
    def _extract_with_regex(self, text: str) -> ExtractionResult:
        """Extract entities using regex patterns (fallback)."""
        result = ExtractionResult()
        
        result.dates = self._extract_dates(text)
        result.districts = self._extract_districts_regex(text)
        result.numbers = self._extract_numbers(text)
        result.organizations = self._extract_organizations(text)
        
        return result
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract date patterns."""
        date_patterns = [
            r'\d{1,2}[.\-/\s]\d{1,2}[.\-/\s]\d{2,4}',
            r'\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}',
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates
    
    def _extract_districts_regex(self, text: str) -> List[str]:
        """Extract HP districts using regex."""
        text_lower = text.lower()
        found = []
        
        for district in HP_DISTRICTS:
            if re.search(rf'\b{district}\b', text_lower):
                canonical = HP_DISTRICT_CANONICAL.get(district, district.title())
                if canonical not in found:
                    found.append(canonical)
        
        return found
    
    def _extract_numbers(self, text: str) -> List[str]:
        """Extract numeric values."""
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\s*(?:personnel|men|forces?|reserves?|strength))?\b', text, re.IGNORECASE)
        simple_numbers = re.findall(r'\b\d+\b', text)
        
        combined = list(set(numbers + [n for n in simple_numbers if int(n) > 0 and int(n) < 10000]))
        return combined[:20]
    
    def _extract_organizations(self, text: str) -> List[str]:
        """Extract organization patterns (battalions)."""
        orgs = []
        
        bn_patterns = [
            r'\b(\d+(?:st|nd|rd|th)?\s*HPAP\s*BN[,\s\w]*)\b',
            r'\b(\d+(?:st|nd|rd|th)?\s*IRBn[,\s\w]*)\b',
            r'\b(\d+(?:st|nd|rd|th)?\s*HP Police[,\s\w]*)\b',
            r'\b(HPAP\s*BN[,\s\w]*)\b',
        ]
        
        for pattern in bn_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            orgs.extend(matches)
        
        return list(set(orgs))
    
    def _normalize_districts(self, districts: List[str]) -> List[str]:
        """Normalize district names to canonical form."""
        normalized = []
        
        for d in districts:
            d_lower = d.lower().strip()
            if d_lower in HP_DISTRICT_CANONICAL:
                canonical = HP_DISTRICT_CANONICAL[d_lower]
                if canonical not in normalized:
                    normalized.append(canonical)
            elif d_lower in HP_DISTRICTS:
                canonical = d.title()
                if canonical not in normalized:
                    normalized.append(canonical)
            else:
                if d not in normalized:
                    normalized.append(d)
        
        return normalized
    
    def _extract_unit_name(self, text: str, result: ExtractionResult) -> str:
        """Extract battalion/unit name."""
        lines = text.strip().split('\n')
        
        for line in lines[:5]:
            line = line.strip()
            if not line:
                continue
            
            if re.match(r'(?:name\s+of\s+)?irbn/?bn', line, re.IGNORECASE):
                if ':' in line:
                    return line.split(':', 1)[1].strip()
            
            for org in result.organizations:
                if org.lower() in line.lower():
                    if len(line) > 5 and len(line) < 100:
                        return line
        
        if result.organizations:
            return result.organizations[0]
        
        if lines and len(lines[0]) > 5:
            return lines[0]
        
        return ""
    
    def get_battalion_name(self, text: str) -> Optional[str]:
        """Get battalion name from text."""
        result = self.extract_entities(text)
        return result.unit_name
    
    def get_districts(self, text: str) -> List[str]:
        """Get list of HP districts from text."""
        result = self.extract_entities(text)
        return result.districts
    
    def get_dates(self, text: str) -> List[str]:
        """Get list of dates from text."""
        result = self.extract_entities(text)
        return result.dates
    
    def get_reserve_strength(self, text: str) -> Optional[int]:
        """Extract reserve strength number."""
        result = self.extract_entities(text)
        
        for num_text in result.numbers:
            num_clean = num_text.replace(',', '').replace(' ', '')
            try:
                value = int(num_clean)
                if 1 <= value <= 5000:
                    return value
            except ValueError:
                continue
        
        return None


ner_service = NERService()


def get_ner_service() -> NERService:
    """Get the global NER service instance."""
    return ner_service
