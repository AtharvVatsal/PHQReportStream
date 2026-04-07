"""BERT Extractor Service - Context-aware extraction using DistilBERT sentence transformers."""

import re
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

# Disable tokenizer parallelism to avoid warnings
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

FIELD_TEMPLATES = {
    "unit_name": "Name of IRBn/Bn Battalion in Himachal Pradesh Police including location and unit designation",
    "reserves_deployed": "Reserves deployed with district name, strength (number of personnel), duration and in-charge details",
    "districts": "Districts in Himachal Pradesh where police force is deployed",
    "stay_arrangement": "Stay arrangement and bathroom quality for deployed forces",
    "messing": "Messing arrangements and food arrangements for personnel",
    "co_interaction_date": "Date of Commanding Officer's last interaction with Superintendent of Police",
    "disciplinary_issues": "Any disciplinary issues or misconduct cases or Nil",
    "reserves_detained": "Reserves detained or under arrest or Nil",
    "training": "Training programs conducted or Nil",
    "welfare": "Welfare initiatives for personnel in the last 24 hours",
    "reserves_available": "Number of reserves available in the battalion",
    "issues_for_phq": "Issues requiring attention from AP&T or PHQ headquarters"
}

HP_FIELDS = [
    "unit_name", "reserves_deployed", "districts", "stay_arrangement",
    "messing", "co_interaction_date", "disciplinary_issues",
    "reserves_detained", "training", "welfare", "reserves_available", "issues_for_phq"
]


@dataclass
class BertExtractionResult:
    """Result from BERT extraction."""
    extracted: Dict[str, str] = field(default_factory=dict)
    confidences: Dict[str, float] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


class BERTExtractor:
    """Context-aware extraction using DistilBERT sentence transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model = None
        self._tokenizer = None
        self._model_name = model_name
        self._initialized = False
        self._embedding_dim = 384
    
    @property
    def is_available(self) -> bool:
        """Check if BERT model is available."""
        return self._initialized and self._model is not None
    
    def initialize(self) -> bool:
        """Initialize DistilBERT sentence transformer model."""
        if self._initialized:
            return True
        
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            self._initialized = True
            print(f"BERTExtractor: Loaded {self._model_name}")
            return True
        except ImportError as e:
            print(f"BERTExtractor: sentence-transformers not available: {e}")
            return False
        except Exception as e:
            print(f"BERTExtractor: Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_with_context(self, text: str) -> BertExtractionResult:
        """Extract fields using semantic understanding with DistilBERT."""
        if not text:
            return BertExtractionResult()
        
        # Split text into clean lines
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 2:
                lines.append(line)
        
        if not lines:
            return BertExtractionResult()
        
        extracted = {}
        confidences = {}
        
        # Use BERT model for semantic matching
        if self._model is not None:
            for field_key in HP_FIELDS:
                template = FIELD_TEMPLATES.get(field_key, field_key)
                
                best_match = None
                best_score = 0.0
                
                for line in lines:
                    score = self._semantic_similarity(line, template)
                    
                    if score > best_score:
                        best_score = score
                        best_match = line
                
                if best_match:
                    extracted[field_key] = self._extract_value(best_match, field_key)
                    confidences[field_key] = min(best_score * 1.2, 1.0)
        else:
            # Fallback to keyword-based extraction
            return self._extract_with_keywords(text, lines)
        
        return BertExtractionResult(
            extracted=extracted,
            confidences=confidences
        )
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using DistilBERT."""
        try:
            embeddings = self._model.encode([text1, text2], convert_to_numpy=True)
            
            dot = np.dot(embeddings[0], embeddings[1])
            norm1 = np.linalg.norm(embeddings[0])
            norm2 = np.linalg.norm(embeddings[1])
            
            if norm1 > 0 and norm2 > 0:
                return float(dot / (norm1 * norm2))
        except Exception as e:
            print(f"Semantic similarity error: {e}")
        
        return 0.0
    
    def _keyword_similarity(self, text: str, field_key: str) -> float:
        """Fallback keyword-based similarity."""
        text_lower = text.lower()
        field_lower = field_key.lower().replace('_', ' ')
        
        keywords = FIELD_TEMPLATES.get(field_key, "").lower().split()
        
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        return matches / len(keywords) if keywords else 0.0
    
    def _extract_value(self, text: str, field_key: str) -> str:
        """Extract value from matched text line."""
        text = text.strip()
        
        # Split by colon and take the value after it
        if ':' in text:
            parts = text.split(':', 1)
            if len(parts) > 1:
                value = parts[1].strip()
                # Clean up leading numbers, dots, and extra text
                value = re.sub(r'^(\d+\.\s*)+', '', value)
                value = value.strip()
                if value:
                    return value
        
        # If no colon, return the text but truncate if it's too long
        if len(text) > 100:
            return text[:100]
        return text
    
    def _extract_with_keywords(self, text: str, lines: List[str]) -> BertExtractionResult:
        """Fallback extraction using keywords only (no ML)."""
        extracted = {}
        confidences = {}
        
        for line in lines:
            line_lower = line.lower()
            
            if not extracted.get("unit_name") and ("irbn" in line_lower or "bn" in line_lower or "hpap" in line_lower):
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["unit_name"] = val
                        confidences["unit_name"] = 0.8
            
            if not extracted.get("reserves_deployed") and "reserves" in line_lower and "deployed" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["reserves_deployed"] = val
                        confidences["reserves_deployed"] = 0.85
            
            if not extracted.get("districts") and "district" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["districts"] = val
                        confidences["districts"] = 0.85
            
            if not extracted.get("stay_arrangement") and "stay" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["stay_arrangement"] = val
                        confidences["stay_arrangement"] = 0.8
            
            if not extracted.get("messing") and "mess" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["messing"] = val
                        confidences["messing"] = 0.8
            
            if not extracted.get("co_interaction_date") and ("interaction" in line_lower or ("co" in line_lower and "sp" in line_lower)):
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["co_interaction_date"] = val
                        confidences["co_interaction_date"] = 0.8
            
            if not extracted.get("disciplinary_issues") and "disciplinary" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["disciplinary_issues"] = val
                        confidences["disciplinary_issues"] = 0.85
            
            if not extracted.get("reserves_detained") and "detained" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["reserves_detained"] = val
                        confidences["reserves_detained"] = 0.85
            
            if not extracted.get("training") and "training" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["training"] = val
                        confidences["training"] = 0.85
            
            if not extracted.get("welfare") and "welfare" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["welfare"] = val
                        confidences["welfare"] = 0.85
            
            if not extracted.get("reserves_available") and "available" in line_lower:
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["reserves_available"] = val
                        confidences["reserves_available"] = 0.85
            
            if not extracted.get("issues_for_phq") and ("phq" in line_lower or "issue for" in line_lower):
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val:
                        extracted["issues_for_phq"] = val
                        confidences["issues_for_phq"] = 0.85
        
        return BertExtractionResult(extracted=extracted, confidences=confidences)
    
    def enhance_confidence(self, extracted: Dict, confidences: Dict) -> Dict:
        """Enhance confidence scores using semantic analysis."""
        if not self._model:
            return confidences
        
        enhanced = dict(confidences)
        
        for field_key, value in extracted.items():
            if not value or value == "Nil":
                continue
            
            template = FIELD_TEMPLATES.get(field_key, "")
            
            score = self._semantic_similarity(value, template)
            
            boost = score * 0.15
            current = enhanced.get(field_key, 0)
            enhanced[field_key] = min(current + boost, 1.0)
        
        return enhanced
    
    def get_field_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text."""
        if self._model is None:
            return None
        
        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception:
            return None


bert_extractor = BERTExtractor()


def get_bert_extractor() -> BERTExtractor:
    """Get the global BERT extractor instance."""
    return bert_extractor
