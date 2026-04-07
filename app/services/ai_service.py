"""AI Service - Enhanced optional lazy-loaded AI features.

Supports optional sentence-transformers for semantic similarity.
Disabled by default for fast startup.
"""

from typing import Dict, List, Optional
import numpy as np


class AIService:
    """Enhanced AI enhancement service."""
    
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._vectorizer = None
        self._initialized = False
        self._embedding_dim = 384  # all-MiniLM-L6-v2 dimension
    
    @property
    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self._initialized
    
    def initialize(self) -> bool:
        """Lazy initialization of AI models."""
        if self._initialized:
            return True
        
        # First try to load TF-IDF (always works)
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            self._vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            print("AI Service: TF-IDF similarity initialized")
        except ImportError:
            print("AI Service: sklearn not available")
            return False
        
        # Try to load sentence-transformers (optional, more powerful)
        try:
            from sentence_transformers import SentenceTransformer
            
            # Use lightweight model (~80MB instead of 2GB)
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            self._initialized = True
            print("AI Service: Sentence-transformers loaded (all-MiniLM-L6-v2)")
            return True
            
        except ImportError:
            print("AI Service: sentence-transformers not available, using TF-IDF only")
            self._initialized = True
            return True
        except Exception as e:
            print(f"AI Service: Error loading sentence-transformers: {e}")
            self._initialized = True
            return True
    
    def get_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """Get embeddings using sentence-transformers."""
        if self._model is None:
            return None
        
        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    def get_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        # Try sentence-transformers first (more accurate)
        if self._model is not None:
            try:
                embeddings = self.get_embeddings([text1, text2])
                if embeddings is not None and len(embeddings) == 2:
                    # Cosine similarity
                    dot = np.dot(embeddings[0], embeddings[1])
                    norm1 = np.linalg.norm(embeddings[0])
                    norm2 = np.linalg.norm(embeddings[1])
                    if norm1 > 0 and norm2 > 0:
                        return float(dot / (norm1 * norm2))
            except Exception:
                pass
        
        # Fallback to TF-IDF
        if self._vectorizer is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                tfidf_matrix = self._vectorizer.fit_transform([text1, text2])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(similarity * 0.5)  # Reduce TF-IDF weight
            except Exception:
                pass
        
        return 0.0
    
    def enhance_confidence(self, text: str, field_name: str, base_confidence: float) -> float:
        """Enhance confidence score using semantic similarity."""
        if not self._initialized or not text:
            return base_confidence
        
        # Template field descriptions (semantic anchors)
        templates = {
            "unit_name": "Name of IRBn/Bn Battalion in Himachal Pradesh Police including location",
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
        
        template = templates.get(field_name, field_name)
        
        try:
            # Get semantic similarity
            similarity = self.get_semantic_similarity(text, template)
            
            # Use different boost strategies based on base confidence
            if base_confidence >= 0.6:
                # High base confidence - small boost
                boost = min(similarity * 0.1, 0.1)
            elif base_confidence >= 0.3:
                # Medium base confidence - moderate boost
                boost = min(similarity * 0.15, 0.15)
            else:
                # Low base confidence - larger boost
                boost = min(similarity * 0.2, 0.2)
            
            enhanced = base_confidence + boost
            return min(enhanced, 1.0)
        except Exception:
            return base_confidence
    
    def extract_advanced_entities(self, text: str) -> List[Dict]:
        """Extract entities using advanced NLP."""
        import re
        entities = []
        
        # Date patterns
        for match in re.finditer(r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}', text):
            entities.append({
                "word": match.group(),
                "type": "DATE",
                "score": 0.95
            })
        
        # HP Districts (Locations)
        hp_districts = {
            'shimla': 'Shimla', 'kangra': 'Kangra', 'mandi': 'Mandi',
            'bilaspur': 'Bilaspur', 'hamirpur': 'Hamirpur', 'una': 'Una',
            'chamba': 'Chamba', 'kullu': 'Kullu', 'solan': 'Solan',
            'sirmaur': 'Sirmaur', 'kinnaur': 'Kinnaur', 'lahaul': 'Lahaul',
            'spiti': 'Spiti'
        }
        
        for district_lower, district_proper in hp_districts.items():
            for match in re.finditer(rf'\b{district_lower}\b', text, re.IGNORECASE):
                entities.append({
                    "word": district_proper,
                    "type": "LOC",
                    "score": 0.9
                })
        
        # Organization patterns
        for match in re.finditer(r'\b(\d+)(?:st|nd|rd|th)?\s+HPAP\s+BN\b', text, re.IGNORECASE):
            entities.append({
                "word": match.group(),
                "type": "ORG",
                "score": 0.95
            })
        
        # Additional org patterns
        for match in re.finditer(r'\bHPAP\b', text, re.IGNORECASE):
            entities.append({
                "word": "HPAP",
                "type": "ORG",
                "score": 0.85
            })
        
        # Number patterns (strength)
        for match in re.finditer(r'\b(\d+)\s*(?:personnel|men|forces?|reserves?|strength)\b', text, re.IGNORECASE):
            entities.append({
                "word": match.group(1),
                "type": "NUMBER",
                "score": 0.8
            })
        
        # Rank patterns
        ranks = [
            (r'\bHC\b', 'HC'), (r'\bHead Constable\b', 'Head Constable'),
            (r'\bSI\b', 'SI'), (r'\bSub Inspector\b', 'Sub Inspector'),
            (r'\bInspector\b', 'Inspector'), (r'\bCT\b', 'CT'),
            (r'\bConstable\b', 'Constable'), (r'\bSP\b', 'SP'),
            (r'\bDSP\b', 'DSP'), (r'\bASP\b', 'ASP'),
        ]
        
        for pattern, rank_name in ranks:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "word": rank_name,
                    "type": "RANK",
                    "score": 0.85
                })
        
        # De-duplicate entities
        seen = set()
        unique_entities = []
        for e in entities:
            key = (e['word'].lower(), e['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(e)
        
        return unique_entities
    
    def analyze_text_quality(self, text: str) -> Dict:
        """Analyze text quality metrics."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        return {
            "length": len(text),
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        }


# Singleton instance
ai_service = AIService()
