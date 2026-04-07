"""Validation Service - Cross-field validation with HP-specific rules."""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


VALID_HP_DISTRICTS = {
    "shimla", "kangra", "mandi", "bilaspur", "hamirpur", "una",
    "chamba", "kullu", "solan", "sirmaur", "kinnaur", "lahaul", "spiti"
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
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    severity: str  # error, warning, info


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


class ValidationService:
    """Cross-field validation with HP-specific rules."""
    
    def __init__(self):
        self.required_fields = ["unit_name", "districts"]
        self.nil_fields = [
            "disciplinary_issues", "reserves_detained", "training",
            "welfare", "issues_for_phq"
        ]
        self.date_fields = ["co_interaction_date"]
    
    def validate(self, extracted: Dict, confidence: Dict) -> ValidationResult:
        """Validate all extracted fields."""
        errors = []
        warnings = []
        suggestions = []
        
        for field_key in self.required_fields:
            value = extracted.get(field_key, "")
            if not value or not value.strip():
                errors.append(ValidationError(
                    field=field_key,
                    message=f"Required field '{field_key}' is empty",
                    severity="error"
                ))
        
        districts = extracted.get("districts", "")
        if districts:
            invalid = self._get_invalid_districts(districts)
            if invalid:
                errors.append(ValidationError(
                    field="districts",
                    message=f"Invalid district names: {', '.join(invalid)}",
                    severity="error"
                ))
        
        date_value = extracted.get("co_interaction_date", "")
        if date_value:
            date_validation = self._validate_date(date_value)
            if date_validation["status"] == "invalid":
                errors.append(ValidationError(
                    field="co_interaction_date",
                    message=f"Invalid date format: {date_value}",
                    severity="error"
                ))
            elif date_validation["status"] == "future":
                warnings.append(ValidationError(
                    field="co_interaction_date",
                    message=f"Date is in the future: {date_value}",
                    severity="warning"
                ))
        
        if extracted.get("reserves_deployed") and not districts:
            warnings.append(ValidationError(
                field="districts",
                message="Reserves deployed but no districts specified",
                severity="warning"
            ))
        
        if districts and not extracted.get("reserves_deployed"):
            warnings.append(ValidationError(
                field="reserves_deployed",
                message="Districts specified but reserves deployment not clear",
                severity="warning"
            ))
        
        for nil_field in self.nil_fields:
            value = extracted.get(nil_field, "")
            if value and value.lower() not in ["nil", "none", "n/a", ""]:
                if len(value) > 100:
                    suggestions.append(f"Consider abbreviating detailed response in '{nil_field}'")
        
        confidence_score = self._calculate_confidence_score(extracted, confidence, errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            confidence_score=confidence_score
        )
    
    def _get_invalid_districts(self, districts_text: str) -> List[str]:
        """Get list of invalid district names."""
        if not districts_text:
            return []
        
        district_list = [d.strip() for d in districts_text.split(',')]
        invalid = []
        
        for d in district_list:
            d_lower = d.lower().strip()
            if d_lower and d_lower not in VALID_HP_DISTRICTS:
                if d_lower not in HP_DISTRICT_CANONICAL:
                    invalid.append(d)
        
        return invalid
    
    def _validate_date(self, date_text: str) -> Dict[str, Any]:
        """Validate date format and value."""
        patterns = [
            (r'(\d{1,2})[.\-/\s](\d{1,2})[.\-/\s](\d{4})', "%d.%m.%Y"),
            (r'(\d{1,2})[.\-/\s](\d{1,2})[.\-/\s](\d{2})', "%d.%m.%y"),
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if len(match.group(3)) == 2:
                        year = int(match.group(3))
                        year = 2000 + year if year < 50 else 1900 + year
                    else:
                        year = int(match.group(3))
                    
                    day = int(match.group(1))
                    month = int(match.group(2))
                    
                    if month > 12 or day > 31:
                        return {"status": "invalid"}
                    
                    date_obj = datetime(year, month, day)
                    today = datetime.now()
                    
                    if date_obj > today + timedelta(days=1):
                        return {"status": "future", "date": date_obj}
                    
                    return {"status": "valid", "date": date_obj}
                except ValueError:
                    pass
        
        return {"status": "invalid"}
    
    def _calculate_confidence_score(
        self, 
        extracted: Dict, 
        confidence: Dict,
        errors: List[ValidationError]
    ) -> float:
        """Calculate overall confidence score."""
        if confidence:
            avg = sum(confidence.values()) / len(confidence)
            error_penalty = len(errors) * 0.1
            return max(0, min(1, avg - error_penalty))
        
        filled = sum(1 for v in extracted.values() if v and v.strip())
        total = len(extracted)
        
        return filled / total if total > 0 else 0
    
    def fix_districts(self, districts_text: str) -> str:
        """Fix invalid district names to canonical form."""
        if not districts_text:
            return districts_text
        
        district_list = [d.strip() for d in districts_text.split(',')]
        fixed = []
        
        for d in district_list:
            d_lower = d.lower().strip()
            if d_lower in HP_DISTRICT_CANONICAL:
                fixed.append(HP_DISTRICT_CANONICAL[d_lower])
            elif d_lower in VALID_HP_DISTRICTS:
                fixed.append(d.title())
            else:
                fixed.append(d)
        
        return ", ".join(fixed)
    
    def standardize_date(self, date_text: str) -> str:
        """Standardize date to DD.MM.YYYY format."""
        validation = self._validate_date(date_text)
        
        if validation.get("status") == "valid":
            date_obj = validation.get("date")
            if date_obj:
                return date_obj.strftime("%d.%m.%Y")
        
        return date_text
    
    def suggest_corrections(self, extracted: Dict) -> List[str]:
        """Generate suggestions for improving extraction."""
        suggestions = []
        
        if not extracted.get("unit_name"):
            suggestions.append("Unit name not found - ensure report starts with battalion name")
        
        if not extracted.get("districts"):
            suggestions.append("No districts found - check if deployment details are included")
        
        if extracted.get("reserves_deployed") and "yes" in extracted["reserves_deployed"].lower():
            if not extracted.get("districts"):
                suggestions.append("Reserves deployed but districts not specified")
        
        nil_count = sum(
            1 for k, v in extracted.items() 
            if k in self.nil_fields and v.lower() == "nil"
        )
        if nil_count < len(self.nil_fields):
            suggestions.append(f"Only {nil_count} of {len(self.nil_fields)} nil fields are properly set")
        
        return suggestions


validation_service = ValidationService()


def get_validation_service() -> ValidationService:
    """Get the global validation service instance."""
    return validation_service
