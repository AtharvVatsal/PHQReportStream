"""Core extraction service - Enhanced with maximum patterns and validation."""

import re
import time
from typing import Dict, List, Tuple, Optional


# HP Template Fields
HP_FIELDS = [
    "unit_name",
    "reserves_deployed", 
    "districts",
    "stay_arrangement",
    "messing",
    "co_interaction_date",
    "disciplinary_issues",
    "reserves_detained",
    "training",
    "welfare",
    "reserves_available",
    "issues_for_phq"
]

# Field display names mapping
FIELD_DISPLAY_NAMES = {
    "unit_name": "Name of IRBn/Bn",
    "reserves_deployed": "Reserves Deployed",
    "districts": "Districts where force deployed",
    "stay_arrangement": "Stay Arrangement/Bathrooms",
    "messing": "Messing Arrangements",
    "co_interaction_date": "CO's last Interaction with SP",
    "disciplinary_issues": "Disciplinary Issues",
    "reserves_detained": "Reserves Detained",
    "training": "Training",
    "welfare": "Welfare Initiative in Last 24 Hrs",
    "reserves_available": "Reserves Available in Bn",
    "issues_for_phq": "Issue for AP&T/PHQ"
}

# HP Districts with all possible variations/aliases
HP_DISTRICTS = {
    'shimla': 'Shimla', 'simla': 'Shimla', 'shimla hills': 'Shimla',
    'kangra': 'Kangra', 'kangra': 'Kangra', 
    'mandi': 'Mandi',
    'bilaspur': 'Bilaspur',
    'hamirpur': 'Hamirpur', 'hamir pur': 'Hamirpur',
    'una': 'Una',
    'chamba': 'Chamba',
    'kullu': 'Kullu', 'kulhu': 'Kullu',
    'solan': 'Solan', 'solan': 'Solan',
    'sirmaur': 'Sirmaur', 'sirmour': 'Sirmaur', 'sirmour': 'Sirmaur',
    'kinnaur': 'Kinnaur', 'kinnour': 'Kinnaur',
    'lahaul': 'Lahaul', 'lahol': 'Lahaul', 'lahaul & spiti': 'Lahaul',
    'spiti': 'Spiti', 'spithi': 'Spiti'
}

# Nil variants
NIL_VALUES = ['nil', 'nill', 'none', 'no', 'n/a', 'na', '-', 'ni', 'nil.', 'none.', 'n/a.', '']

# Quality ratings
QUALITY_WORDS = ['good', 'excellent', 'very good', 'satisfactory', 'fair', 'poor', 'bad', 'average', 'avg', 'nice', 'great']


class ExtractionService:
    """Enhanced service with maximum extraction accuracy."""
    
    def __init__(self):
        self.fields = HP_FIELDS
        from app.services.text_corrector import get_text_corrector
        self.corrector = get_text_corrector()
        self.ai_service = None
        self._ai_initialized = False
    
    def _init_ai(self):
        """Initialize AI service if enabled."""
        if self._ai_initialized:
            return
        try:
            from app.services.ai_service import AIService
            self.ai_service = AIService()
            if self.ai_service.initialize():
                self._ai_initialized = True
                print("AI Service initialized successfully")
        except Exception as e:
            print(f"AI Service initialization failed: {e}")
            self.ai_service = None
    
    def extract(self, text: str, ai_enhance: bool = False) -> Tuple[Dict[str, str], Dict[str, float], float, List[Dict]]:
        """Extract all fields with enhanced patterns - line by line approach."""
        start_time = time.time()
        
        # Split into lines for cleaner extraction
        lines = text.strip().split('\n')
        
        extracted = {field: "" for field in self.fields}
        confidences = {field: 0.0 for field in self.fields}
        
        # Process each line
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Unit name - usually first line or has "name of"
            if not extracted["unit_name"]:
                if re.match(r'(?:name\s+of\s+)?irbn/?bn', line, re.IGNORECASE) or re.match(r'name\s+of\s+battalion', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val and len(val) > 3:
                        extracted["unit_name"] = val
                        confidences["unit_name"] = 0.9
                elif not extracted["unit_name"] and len(line) > 5 and len(line) < 70:
                    # First non-empty line that's not just a number
                    if 'bn' in line.lower() or 'hpap' in line.lower():
                        # Clean leading numbers but keep the content
                        clean_line = re.sub(r'^\d+\.\s*', '', line)
                        extracted["unit_name"] = clean_line
                        confidences["unit_name"] = 0.6
            
            # Reserves deployed
            if not extracted["reserves_deployed"]:
                if re.search(r'reserves?\s+deployed', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["reserves_deployed"] = val
                        confidences["reserves_deployed"] = 0.9
            
            # Districts
            if not extracted["districts"]:
                if re.search(r'districts?\s+where\s+force', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        # Normalize districts
                        normalized = self._normalize_districts(val)
                        if normalized:
                            extracted["districts"] = normalized
                            confidences["districts"] = 0.95
                        else:
                            extracted["districts"] = val
                            confidences["districts"] = 0.7
            
            # Stay arrangement
            if not extracted["stay_arrangement"]:
                if re.search(r'stay\s+arrangement', line, re.IGNORECASE) or re.search(r'stay\s+accommodation', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["stay_arrangement"] = val
                        confidences["stay_arrangement"] = 0.85
            
            # Messing
            if not extracted["messing"]:
                if re.search(r'mess(?:ing)?', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["messing"] = val
                        # Boost if contains quality word
                        if any(q in val.lower() for q in QUALITY_WORDS):
                            confidences["messing"] = 0.9
                        else:
                            confidences["messing"] = 0.8
            
            # CO interaction date
            if not extracted["co_interaction_date"]:
                if re.search(r"co['\u2019]?s?\s+last\s+interaction", line, re.IGNORECASE) or re.search(r"co['\u2019]?\s*interaction", line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["co_interaction_date"] = val
                        # Check if it's a valid date
                        if self._is_valid_date(val):
                            confidences["co_interaction_date"] = 0.95
                        else:
                            confidences["co_interaction_date"] = 0.6
            
            # Disciplinary issues
            if not extracted["disciplinary_issues"]:
                if re.search(r'disciplinary\s+issues?', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["disciplinary_issues"] = self._standardize_nil(val)
                        confidences["disciplinary_issues"] = 0.9
            
            # Reserves detained
            if not extracted["reserves_detained"]:
                if re.search(r'reserves?\s+detained', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["reserves_detained"] = self._standardize_nil(val)
                        confidences["reserves_detained"] = 0.9
            
            # Training
            if not extracted["training"]:
                if re.search(r'\btraining\b', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["training"] = self._standardize_nil(val)
                        confidences["training"] = 0.9
            
            # Welfare
            if not extracted["welfare"]:
                if re.search(r'\bwelfare\b', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["welfare"] = self._standardize_nil(val)
                        confidences["welfare"] = 0.9
            
            # Reserves available
            if not extracted["reserves_available"]:
                if re.search(r'reserves?\s+available', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["reserves_available"] = val
                        if re.match(r'^yes\b', val, re.IGNORECASE) or re.match(r'^no\b', val, re.IGNORECASE):
                            confidences["reserves_available"] = 0.95
                        elif re.search(r'\d+\s*reserves?', val, re.IGNORECASE):
                            confidences["reserves_available"] = 0.9
                        else:
                            confidences["reserves_available"] = 0.75
            
            # Issues for PHQ
            if not extracted["issues_for_phq"]:
                if re.search(r'issue\s+for\s+(?:ap&t|phq)', line, re.IGNORECASE):
                    val = self._extract_value_at_colon(line)
                    if val:
                        extracted["issues_for_phq"] = self._standardize_nil(val)
                        confidences["issues_for_phq"] = 0.9
        
        # Post-processing
        extracted, confidences = self._apply_improvements(extracted, confidences)
        
        # Boost confidences based on cross-field validation
        confidences = self._boost_confidence(extracted, confidences)
        
        # AI Enhancement
        if ai_enhance:
            self._init_ai()
            if self.ai_service and self.ai_service.is_available:
                for field_key in self.fields:
                    field_value = extracted.get(field_key, "")
                    if field_value:
                        # Enhance confidence using semantic similarity
                        enhanced_conf = self.ai_service.enhance_confidence(
                            field_value, field_key, confidences.get(field_key, 0.0)
                        )
                        confidences[field_key] = max(confidences[field_key], enhanced_conf)
                
                # Extract advanced entities
                try:
                    entities = self.ai_service.extract_advanced_entities(text)
                    if entities:
                        for entity in entities:
                            # Could use entities to improve extraction
                            pass
                except Exception as e:
                    print(f"Entity extraction error: {e}")
        
        # Generate text corrections
        corrections = []
        for field_key, field_value in extracted.items():
            if field_value and len(field_value) > 2:
                field_corrections = self.corrector.get_corrections(field_value, field_key)
                for corr in field_corrections:
                    if corr.has_change():
                        corrections.append({
                            'field_key': field_key,
                            'field_name': FIELD_DISPLAY_NAMES.get(field_key, field_key),
                            'original': corr.original,
                            'corrected': corr.corrected,
                            'type': corr.type
                        })
        
        processing_time = time.time() - start_time
        
        return extracted, confidences, processing_time, corrections
    
    def _extract_value_at_colon(self, line: str) -> str:
        """Extract value after colon in a line, stopping at next section."""
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) > 1:
                val = parts[1].strip()
                # Stop at next numbered section (e.g., " 4. Messing:", "10. Reserves")
                val = re.sub(r'\s+\d+\.\s+[A-Za-z]', '', val)
                # Remove leading numbers and dots only if not followed by digits (avoid dates)
                val = re.sub(r'^(\d+\.\s*)+(?!\d)', '', val)
                val = val.strip()
                if val and len(val) > 0:
                    return val
        return ""
    
    def _normalize_districts(self, value: str) -> str:
        """Normalize district names with alias handling."""
        value_lower = value.lower()
        found_districts = []
        
        for alias, proper in HP_DISTRICTS.items():
            if alias in value_lower:
                if proper not in found_districts:
                    found_districts.append(proper)
        
        if found_districts:
            return ", ".join(found_districts)
        return ""
    
    def _standardize_nil(self, value: str) -> str:
        """Standardize nil/none responses."""
        value_lower = value.lower().strip()
        
        if value_lower in NIL_VALUES:
            return "Nil"
        
        for nil_variant in NIL_VALUES:
            if value_lower == nil_variant or value_lower.startswith(nil_variant + ' '):
                return "Nil"
        
        return value
    
    def _is_valid_date(self, value: str) -> bool:
        """Check if value is a valid date."""
        date_patterns = [
            r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}',
            r'\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}',
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    def _apply_improvements(self, extracted: Dict[str, str], confidences: Dict[str, float]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Apply post-processing improvements."""
        
        # Auto-fill empty nil fields
        nil_fields = ["disciplinary_issues", "reserves_detained", "training", "welfare", "issues_for_phq"]
        for field in nil_fields:
            if not extracted.get(field) or not extracted[field].strip():
                extracted[field] = "Nil"
                confidences[field] = 0.9
        
        return extracted, confidences
    
    def _boost_confidence(self, extracted: Dict[str, str], confidences: Dict[str, float]) -> Dict[str, float]:
        """Boost confidence based on cross-field validation."""
        
        # If reserves deployed and districts both present
        if extracted.get("reserves_deployed") and extracted.get("districts"):
            reserves_val = extracted["reserves_deployed"].lower()
            if 'yes' in reserves_val or re.search(r'\d+', reserves_val):
                confidences["reserves_deployed"] = min(confidences["reserves_deployed"] + 0.1, 1.0)
                confidences["districts"] = min(confidences["districts"] + 0.1, 1.0)
        
        # If CO date is valid date format
        if extracted.get("co_interaction_date"):
            if self._is_valid_date(extracted["co_interaction_date"]):
                confidences["co_interaction_date"] = min(confidences["co_interaction_date"] + 0.1, 1.0)
        
        # If unit name contains HPAP BN
        if extracted.get("unit_name"):
            if 'hpap' in extracted["unit_name"].lower() and 'bn' in extracted["unit_name"].lower():
                confidences["unit_name"] = min(confidences["unit_name"] + 0.1, 1.0)
        
        return confidences
    
    def validate_structure(self, text: str) -> Dict:
        """Validate report structure and detect format."""
        text_lower = text.lower()
        
        detected_format = self.detect_format(text)
        
        required = {
            "unit_name": r'name\s+of',
            "reserves_deployed": r'reserves?\s+deployed',
            "districts": r'districts?\s+where',
            "co_interaction_date": r'interaction',
            "disciplinary_issues": r'disciplinary',
            "welfare": r'welfare',
            "reserves_available": r'reserves?\s+available',
        }
        
        found = []
        missing = []
        
        for section, pattern in required.items():
            if re.search(pattern, text_lower):
                found.append(FIELD_DISPLAY_NAMES.get(section, section))
            else:
                missing.append(FIELD_DISPLAY_NAMES.get(section, section))
        
        score = len(found) / len(required) if required else 0
        
        return {
            "score": score,
            "found_sections": found,
            "missing_sections": missing,
            "confidence": "high" if score > 0.8 else "medium" if score > 0.5 else "low",
            "detected_format": detected_format
        }
    
    def detect_format(self, text: str) -> str:
        """Detect report format (v1, v2, or unknown)."""
        text_lower = text.lower()
        
        v2_patterns = [
            r'name\s+of\s+irbn/?bn',
            r'reserves?\s+deployed.*:',
            r'stay\s+arrangement/?bathrooms',
            r"co['\u2019\"]?s\s+last\s+interaction",
            r'issue\s+for\s+(?:ap&t|phq)',
        ]
        
        v1_patterns = [
            r'^\d+\.\s*name\s+of\s+irbn',
            r'^\d+\.\s*reserves?\s+deployed',
            r'^\d+\.\s*districts?\s+where',
        ]
        
        v2_score = sum(1 for p in v2_patterns if re.search(p, text_lower))
        v1_score = sum(1 for p in v1_patterns if re.search(p, text_lower, re.MULTILINE))
        
        if v2_score >= 3:
            return "v2"
        elif v1_score >= 2:
            return "v1"
        else:
            return "unknown"
    
    def generate_suggestions(self, extracted: Dict[str, str], confidences: Dict[str, float]) -> List[str]:
        """Generate suggestions based on extraction results."""
        suggestions = []
        
        for field, confidence in confidences.items():
            display_name = FIELD_DISPLAY_NAMES.get(field, field)
            value = extracted.get(field, '')
            
            if confidence < 0.3 and not value:
                suggestions.append(f"Field '{display_name}' not extracted")
            elif confidence < 0.5 and value:
                suggestions.append(f"Field '{display_name}' has low confidence")
        
        critical = ["unit_name", "reserves_deployed", "districts"]
        missing = [f for f in critical if not extracted.get(f) or not extracted[f].strip()]
        if missing:
            names = [FIELD_DISPLAY_NAMES.get(f, f) for f in missing]
            suggestions.append(f"Critical fields missing: {', '.join(names)}")
        
        high_conf = sum(1 for c in confidences.values() if c >= 0.7)
        total = len(confidences)
        
        if high_conf >= total * 0.8:
            suggestions.append("Excellent extraction quality!")
        elif high_conf >= total * 0.6:
            suggestions.append("Good extraction quality.")
        
        if not suggestions:
            suggestions.append("All fields extracted successfully.")
        
        return suggestions[:8]
    
    def split_reports(self, text: str) -> List[str]:
        """Split text into multiple reports."""
        if not text or not text.strip():
            return []
        
        reports = []
        
        # Try splitting by numbered format: 1., 2., 3. or Report 1, Report 2
        numbered_pattern = r'(?:^|\n)(?:\d+\.|Report\s*\d+)'
        parts = re.split(numbered_pattern, text, flags=re.MULTILINE)
        
        for part in parts:
            part = part.strip()
            if len(part) > 50:  # Minimum valid report length
                reports.append(part)
        
        # If no numbered reports found, try double newlines
        if len(reports) < 2:
            reports = []
            double_newline_parts = text.split('\n\n')
            for part in double_newline_parts:
                part = part.strip()
                if len(part) > 50:
                    reports.append(part)
        
        # If still only one report, treat as single report
        if len(reports) < 2:
            reports = [text.strip()] if text.strip() else []
        
        return reports
    
    def extract_batch(self, texts: List[str], ai_enhance: bool = False) -> List[Tuple[Dict, Dict, float, List]]:
        """Extract multiple reports in batch."""
        results = []
        for text in texts:
            if text and text.strip():
                result = self.extract(text.strip(), ai_enhance)
                results.append(result)
        return results
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities."""
        entities = []
        
        for match in re.finditer(r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}', text):
            entities.append({"word": match.group(), "type": "DATE", "score": 0.95})
        
        for district, proper in HP_DISTRICTS.items():
            for match in re.finditer(rf'\b{district}\b', text, re.IGNORECASE):
                entities.append({"word": proper, "type": "LOC", "score": 0.9})
        
        for match in re.finditer(r'\b\d+(?:st|nd|rd|th)?\s+HPAP\s+BN\b', text, re.IGNORECASE):
            entities.append({"word": match.group(), "type": "ORG", "score": 0.95})
        
        return entities


extraction_service = ExtractionService()