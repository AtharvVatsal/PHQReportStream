"""AI Coordinator - Orchestrates all AI services for seamless extraction."""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from app.services.typo_service import get_typo_service, TypoService
from app.services.ner_service import get_ner_service, NERService, ExtractionResult as NERResult
from app.services.bert_extractor import get_bert_extractor, BERTExtractor, BertExtractionResult
from app.services.llm_service import get_llm_service, LLMService, LLMExtractionResult
from app.services.validation_service import get_validation_service, ValidationService, ValidationResult


AI_MODES = ["fast", "accurate", "llm"]


@dataclass
class ExtractionResult:
    """Final extraction result from AI coordinator."""
    extracted: Dict[str, str]
    confidences: Dict[str, float]
    processing_time: float
    mode_used: str
    validation: Optional[ValidationResult] = None
    entities: Optional[NERResult] = None
    corrections: List[Dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AICoordinator:
    """Orchestrates all AI services for seamless extraction."""
    
    def __init__(self, mode: str = "fast"):
        self._mode = mode
        self._typo_service: Optional[TypoService] = None
        self._ner_service: Optional[NERService] = None
        self._bert_extractor: Optional[BERTExtractor] = None
        self._llm_service: Optional[LLMService] = None
        self._validation_service: Optional[ValidationService] = None
        self._initialized = False
    
    @property
    def mode(self) -> str:
        return self._mode
    
    @mode.setter
    def mode(self, value: str):
        if value in AI_MODES:
            self._mode = value
    
    @property
    def is_available(self) -> Dict[str, bool]:
        """Check availability of AI services."""
        return {
            "typo": self._typo_service is not None,
            "ner": self._ner_service is not None and self._ner_service.is_available,
            "bert": self._bert_extractor is not None and self._bert_extractor.is_available,
            "llm": self._llm_service is not None and self._llm_service.is_available
        }
    
    def initialize(self):
        """Initialize all AI services based on mode."""
        if self._initialized:
            return
        
        print(f"Initializing AI services in '{self._mode}' mode...")
        
        self._typo_service = get_typo_service()
        
        if self._mode in ["accurate", "llm"]:
            try:
                self._ner_service = get_ner_service()
                ner_result = self._ner_service.initialize()
                if not ner_result:
                    print("Warning: NER service using fallback mode")
            except Exception as e:
                print(f"NER service initialization failed: {e}")
                self._ner_service = None
            
            try:
                self._bert_extractor = get_bert_extractor()
                bert_result = self._bert_extractor.initialize()
                if not bert_result:
                    print("Warning: BERT service using fallback mode")
            except Exception as e:
                print(f"BERT service initialization failed: {e}")
                self._bert_extractor = None
        
        if self._mode == "llm":
            try:
                self._llm_service = get_llm_service()
            except Exception as e:
                print(f"LLM service initialization failed: {e}")
                self._llm_service = None
        
        self._validation_service = get_validation_service()
        
        self._initialized = True
        
        availability = self.is_available
        print(f"AI Services initialized: {availability}")
    
    def extract(self, text: str) -> ExtractionResult:
        """Main extraction pipeline."""
        start_time = time.time()
        
        if not self._initialized:
            self.initialize()
        
        original_text = text
        
        cleaned = self._preprocess(text)
        
        extracted, confidences = self._extract(cleaned)
        
        corrections = self._get_corrections(extracted)
        
        validation = self._validate(extracted, confidences)
        
        if validation and validation.warnings:
            warnings = [w.message for w in validation.warnings]
        else:
            warnings = []
        
        suggestions = []
        if validation:
            suggestions = validation.suggestions
        
        processing_time = time.time() - start_time
        
        return ExtractionResult(
            extracted=extracted,
            confidences=confidences,
            processing_time=processing_time,
            mode_used=self._mode,
            validation=validation,
            corrections=corrections,
            suggestions=suggestions,
            warnings=warnings
        )
    
    def _preprocess(self, text: str) -> str:
        """Preprocess text - fix typos."""
        if self._typo_service:
            text = self._typo_service.correct(text)
        return text
    
    def _extract(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract fields based on mode."""
        extracted = {k: "" for k in [
            "unit_name", "reserves_deployed", "districts", "stay_arrangement",
            "messing", "co_interaction_date", "disciplinary_issues",
            "reserves_detained", "training", "welfare", "reserves_available",
            "issues_for_phq"
        ]}
        confidences = {k: 0.5 for k in extracted.keys()}
        
        if self._mode == "fast":
            extracted, confidences = self._extract_fast(text)
        
        elif self._mode == "accurate":
            extracted, confidences = self._extract_accurate(text)
        
        elif self._mode == "llm":
            extracted, confidences = self._extract_llm(text)
        
        extracted = self._postprocess(extracted)
        
        return extracted, confidences
    
    def _extract_fast(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Fast extraction using regex (original method)."""
        from app.services.extractor import extraction_service
        result = extraction_service.extract(text, ai_enhance=False)
        return result[0], result[1]
    
    def _extract_accurate(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Accurate extraction using NER + DistilBERT semantic matching."""
        extracted = {}
        confidences = {}
        
        # Step 1: Use NER service for entity extraction (districts, dates, unit names)
        if self._ner_service:
            try:
                ner_result = self._ner_service.extract_entities(text)
                
                if ner_result.unit_name:
                    extracted["unit_name"] = ner_result.unit_name
                    confidences["unit_name"] = 0.9
                
                if ner_result.districts:
                    extracted["districts"] = ", ".join(ner_result.districts)
                    confidences["districts"] = 0.9
                
                # Only use NER dates if we don't have a valid date pattern from the text
                if ner_result.dates:
                    # Check if text contains a date pattern
                    import re
                    date_pattern = r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}'
                    if not re.search(date_pattern, text):
                        # Use NER date only if no date pattern found in text
                        extracted["co_interaction_date"] = ner_result.dates[0]
                        confidences["co_interaction_date"] = 0.85
            except Exception as e:
                print(f"NER extraction error: {e}")
        
        # Step 2: Use DistilBERT for semantic field extraction
        if self._bert_extractor and self._bert_extractor.is_available:
            try:
                bert_result = self._bert_extractor.extract_with_context(text)
                
                # Merge BERT results (only fill empty fields or if BERT is more confident)
                for field_key, value in bert_result.extracted.items():
                    if value and (not extracted.get(field_key) or confidences.get(field_key, 0) < 0.7):
                        # For date field, only use BERT if it looks like a date
                        if field_key == "co_interaction_date":
                            import re
                            date_pattern = r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}'
                            if re.search(date_pattern, value):
                                extracted[field_key] = value
                                confidences[field_key] = bert_result.confidences.get(field_key, 0.8)
                        else:
                            extracted[field_key] = value
                            confidences[field_key] = bert_result.confidences.get(field_key, 0.8)
                
                for field_key, conf in bert_result.confidences.items():
                    if field_key in confidences:
                        confidences[field_key] = max(confidences[field_key], conf)
                    else:
                        confidences[field_key] = conf
            except Exception as e:
                print(f"BERT extraction error: {e}")
        
        # Step 3: Use fast extractor as fallback for remaining fields
        from app.services.extractor import extraction_service
        fast_result = extraction_service.extract(text, ai_enhance=False)
        fast_extracted, fast_confidences = fast_result[0], fast_result[1]
        
        for field_key, value in fast_extracted.items():
            if value and not extracted.get(field_key):
                extracted[field_key] = value
                confidences[field_key] = fast_confidences.get(field_key, 0.6)
        
        # Ensure all fields exist
        for key in ["unit_name", "reserves_deployed", "districts", "stay_arrangement",
                    "messing", "co_interaction_date", "disciplinary_issues",
                    "reserves_detained", "training", "welfare", "reserves_available", "issues_for_phq"]:
            if key not in extracted:
                extracted[key] = ""
            if key not in confidences:
                confidences[key] = 0.5
        
        # Boost overall confidence since we're using advanced AI
        for key in confidences:
            if confidences[key] > 0:
                confidences[key] = min(confidences[key] + 0.05, 1.0)
        
        return extracted, confidences
    
    def _extract_llm(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """LLM-based extraction."""
        if self._llm_service and self._llm_service.is_available:
            llm_result = self._llm_service.extract_with_llm(text)
            
            if llm_result.extracted:
                return llm_result.extracted, {k: llm_result.confidence for k in llm_result.extracted}
        
        return self._extract_accurate(text)
    
    def _postprocess(self, extracted: Dict) -> Dict:
        """Post-process extracted fields."""
        if self._validation_service:
            if extracted.get("districts"):
                extracted["districts"] = self._validation_service.fix_districts(extracted["districts"])
            
            if extracted.get("co_interaction_date"):
                extracted["co_interaction_date"] = self._validation_service.standardize_date(
                    extracted["co_interaction_date"]
                )
        
        nil_fields = [
            "disciplinary_issues", "reserves_detained", "training",
            "welfare", "issues_for_phq"
        ]
        
        for field in nil_fields:
            if field in extracted and extracted[field]:
                if self._typo_service:
                    extracted[field] = self._typo_service.normalize_nil(extracted[field])
                elif extracted[field].lower().strip() in ["nil", "none", "n/a", "-", ""]:
                    extracted[field] = "Nil"
        
        for key, value in extracted.items():
            if not value:
                extracted[key] = "Nil" if key in nil_fields else ""
        
        return extracted
    
    def _get_corrections(self, extracted: Dict) -> List[Dict]:
        """Get text corrections."""
        corrections = []
        
        if not self._typo_service:
            return corrections
        
        for field_key, value in extracted.items():
            if value and len(value) > 2:
                field_corrections = self._typo_service.get_corrections(value, field_key)
                for corr in field_corrections:
                    if corr.has_change():
                        corrections.append({
                            'field_key': field_key,
                            'field_name': field_key.replace('_', ' ').title(),
                            'original': corr.original,
                            'corrected': corr.corrected,
                            'type': corr.type
                        })
        
        return corrections
    
    def _validate(self, extracted: Dict, confidences: Dict) -> Optional[ValidationResult]:
        """Validate extracted fields."""
        if self._validation_service:
            return self._validation_service.validate(extracted, confidences)
        return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all AI services."""
        status = {
            "mode": self._mode,
            "initialized": self._initialized,
            "services": self.is_available
        }
        
        if self._llm_service:
            status["llm_health"] = self._llm_service.check_health()
        
        if self._typo_service:
            status["typo_dictionary_size"] = self._typo_service.get_dictionary_size()
        
        return status
    
    def switch_mode(self, mode: str) -> bool:
        """Switch AI extraction mode."""
        if mode not in AI_MODES:
            return False
        
        print(f"Switching to '{mode}' mode...")
        self._mode = mode
        self._initialized = False
        
        try:
            self.initialize()
        except Exception as e:
            print(f"Error during mode switch: {e}")
            import traceback
            traceback.print_exc()
            # Try to recover with fast mode
            if mode != "fast":
                print("Falling back to fast mode...")
                self._mode = "fast"
                self._initialized = False
                try:
                    self.initialize()
                except:
                    pass
        
        return True


ai_coordinator = AICoordinator()


def get_ai_coordinator() -> AICoordinator:
    """Get the global AI coordinator instance."""
    return ai_coordinator
