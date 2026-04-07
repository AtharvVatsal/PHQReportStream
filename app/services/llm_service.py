"""LLM Service - Ollama integration for intelligent extraction."""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import time


SYSTEM_PROMPT = """You are an expert at extracting information from HP Police IRBn/Bn daily reports.

Extract the report into JSON with exactly these fields:
- unit_name: Name of IRBn/Bn (e.g., "1st HPAP BN Junga, Shimla")
- reserves_deployed: Details of reserves deployed with strength
- districts: Districts where force is deployed (comma separated)
- stay_arrangement: Quality of stay/accommodation
- messing: Quality of messing arrangements
- co_interaction_date: Date of CO's last interaction with SP (DD.MM.YYYY)
- disciplinary_issues: Any disciplinary issues or "Nil"
- reserves_detained: Any reserves detained or "Nil"
- training: Any training conducted or "Nil"
- welfare: Welfare initiatives or "Nil"
- reserves_available: Available reserves or "Nil"
- issues_for_phq: Issues for PHQ or "Nil"

Rules:
- Districts must be valid HP districts: Shimla, Kangra, Mandi, Bilaspur, Hamirpur, Una, Chamba, Kullu, Solan, Sirmaur, Kinnaur, Lahaul, Spiti
- Use "Nil" (capitalized) for empty or negative responses
- Date format: DD.MM.YYYY
- If a field is not found, use empty string ""
- If reserves are deployed but no number specified, just note "Yes" or details
- Response must be valid JSON only, no explanation text
- Do not include any markdown or code blocks"""


@dataclass
class LLMExtractionResult:
    """Result from LLM extraction."""
    extracted: Dict[str, str]
    confidence: float = 1.0
    model_used: str = "mistral"
    processing_time: float = 0.0
    raw_response: str = ""
    errors: List[str] = field(default_factory=list)


class LLMService:
    """Ollama LLM integration for intelligent extraction."""
    
    def __init__(self, model: str = "mistral", endpoint: str = "http://localhost:11434/api/generate"):
        self._model = model
        self._endpoint = endpoint
        self._available = False
        self._check_connection()
    
    @property
    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        return self._available
    
    def _check_connection(self):
        """Check if Ollama is running."""
        try:
            import requests
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                self._available = True
                print(f"LLM Service: Connected to Ollama (model: {self._model})")
            else:
                self._available = False
        except Exception:
            self._available = False
    
    def extract_with_llm(self, text: str) -> LLMExtractionResult:
        """Extract fields using LLM intelligence."""
        start_time = time.time()
        
        result = LLMExtractionResult(
            extracted={},
            model_used=self._model
        )
        
        if not self._available:
            result.errors.append("Ollama not available")
            return result
        
        try:
            import requests
            
            payload = {
                "model": self._model,
                "prompt": f"{SYSTEM_PROMPT}\n\nReport:\n{text}",
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                self._endpoint,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result.raw_response = response.json().get("response", "")
                result.extracted = self._parse_json_response(result.raw_response)
                result.confidence = 0.95
            else:
                result.errors.append(f"LLM error: {response.status_code}")
        
        except ImportError:
            result.errors.append("requests library not available")
        except Exception as e:
            result.errors.append(f"Extraction error: {str(e)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _parse_json_response(self, response_text: str) -> Dict[str, str]:
        """Parse JSON from LLM response."""
        extracted = {}
        
        try:
            cleaned = response_text.strip()
            
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?', '', cleaned)
                cleaned = re.sub(r'```$', '', cleaned)
            
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            for key in [
                "unit_name", "reserves_deployed", "districts", "stay_arrangement",
                "messing", "co_interaction_date", "disciplinary_issues",
                "reserves_detained", "training", "welfare", "reserves_available",
                "issues_for_phq"
            ]:
                value = data.get(key, "")
                if value:
                    extracted[key] = str(value)
                else:
                    extracted[key] = ""
        
        except json.JSONDecodeError:
            extracted = self._fallback_parse(response_text)
        
        return extracted
    
    def _fallback_parse(self, text: str) -> Dict[str, str]:
        """Fallback parsing when JSON fails."""
        extracted = {}
        
        field_patterns = {
            "unit_name": r'"unit_name"\s*:\s*"([^"]*)"',
            "reserves_deployed": r'"reserves_deployed"\s*:\s*"([^"]*)"',
            "districts": r'"districts"\s*:\s*"([^"]*)"',
            "stay_arrangement": r'"stay_arrangement"\s*:\s*"([^"]*)"',
            "messing": r'"messing"\s*:\s*"([^"]*)"',
            "co_interaction_date": r'"co_interaction_date"\s*:\s*"([^"]*)"',
            "disciplinary_issues": r'"disciplinary_issues"\s*:\s*"([^"]*)"',
            "reserves_detained": r'"reserves_detained"\s*:\s*"([^"]*)"',
            "training": r'"training"\s*:\s*"([^"]*)"',
            "welfare": r'"welfare"\s*:\s*"([^"]*)"',
            "reserves_available": r'"reserves_available"\s*:\s*"([^"]*)"',
            "issues_for_phq": r'"issues_for_phq"\s*:\s*"([^"]*)"',
        }
        
        for field, pattern in field_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1)
            else:
                extracted[field] = ""
        
        return extracted
    
    def validate_with_llm(self, extracted: Dict, original: str) -> Dict[str, Any]:
        """Use LLM to validate extracted fields."""
        if not self._available:
            return {"valid": True, "errors": [], "suggestions": []}
        
        validation_prompt = f"""Validate this extracted data from an HP Police report:

Extracted fields:
{json.dumps(extracted, indent=2)}

Original report:
{original[:1000]}

Check for:
1. Invalid HP district names
2. Incorrect date formats
3. Missing required fields
4. Inconsistent information

Respond with JSON:
{{
  "valid": true/false,
  "errors": ["list of errors"],
  "suggestions": ["list of suggestions to improve"]
}}"""
        
        try:
            import requests
            response = requests.post(
                self._endpoint,
                json={
                    "model": self._model,
                    "prompt": validation_prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "{}")
                return json.loads(result)
        except Exception:
            pass
        
        return {"valid": True, "errors": [], "suggestions": []}
    
    def generate_summary(self, extracted: Dict) -> str:
        """Generate a summary using LLM."""
        if not self._available:
            return ""
        
        summary_prompt = f"""Generate a brief summary (2-3 sentences) of this HP Police report:

{json.dumps(extracted, indent=2)}"""
        
        try:
            import requests
            response = requests.post(
                self._endpoint,
                json={
                    "model": self._model,
                    "prompt": summary_prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception:
            pass
        
        return ""
    
    def check_health(self) -> Dict[str, Any]:
        """Check Ollama service health."""
        health = {
            "available": self._available,
            "model": self._model,
            "endpoint": self._endpoint
        }
        
        if self._available:
            try:
                import requests
                response = requests.get(
                    "http://localhost:11434/api/tags",
                    timeout=5
                )
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    health["installed_models"] = [m.get("name", "") for m in models]
            except Exception:
                pass
        
        return health


llm_service = LLMService()


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    return llm_service
