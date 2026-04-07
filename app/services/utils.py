"""Additional utilities - Auto-fill, remarks generation, and helpers."""

import re
from typing import Dict, List, Tuple


# HP District coordinates for map visualization
HP_DISTRICT_COORDS = {
    "Lahaul": (20, 85),
    "Spiti": (35, 88),
    "Kinnaur": (60, 82),
    "Chamba": (15, 70),
    "Kullu": (30, 68),
    "Kangra": (15, 55),
    "Mandi": (35, 56),
    "Hamirpur": (28, 45),
    "Bilaspur": (35, 42),
    "Una": (18, 35),
    "Solan": (50, 40),
    "Sirmaur": (62, 32),
    "Shimla": (58, 55),
}


def normalize_district_name(name: str) -> str:
    """Normalize district name with common typo handling."""
    hp_districts = {
        'shimla': 'Shimla', 'kangra': 'Kangra', 'mandi': 'Mandi',
        'bilaspur': 'Bilaspur', 'hamirpur': 'Hamirpur', 'una': 'Una',
        'chamba': 'Chamba', 'kullu': 'Kullu', 'solan': 'Solan',
        'sirmaur': 'Sirmaur', 'kinnaur': 'Kinnaur', 'lahaul': 'Lahaul',
        'spiti': 'Spiti'
    }
    
    # Common typos/variants
    replacements = {
        "sirmour": "Sirmaur", "lahol": "Lahaul", "spithi": "Spiti",
        "kinnour": "Kinnaur", "kangara": "Kangra", "kullU": "Kullu",
    }
    
    n = (name or "").strip().lower()
    
    if n in hp_districts:
        return hp_districts[n]
    
    if n in replacements:
        return replacements[n]
    
    for k, v in hp_districts.items():
        if k.lower() == n:
            return v
    
    return (name or "").strip().title()


def extract_district_strength_from_reserves(reserves_text: str) -> Dict[str, int]:
    """Parse reserves deployed text to extract per-district strength."""
    if not reserves_text:
        return {}
    
    text = reserves_text.replace("\n", " ")
    parts = re.split(r";\s*", text)
    totals = {}
    
    for part in parts:
        if not part.strip():
            continue
        
        # Try "District: Number" pattern
        m = re.search(r"([A-Za-z][A-Za-z\s]+?):\s*(\d+)", part)
        if not m:
            # Try "District - Number" pattern
            m = re.search(r"([A-Za-z][A-Za-z\s]+?)[\-\u2013]\s*(\d+)", part)
        
        if m:
            dist = normalize_district_name(m.group(1))
            try:
                strength = int(m.group(2))
            except (ValueError, AttributeError):
                continue
            
            if dist not in totals:
                totals[dist] = 0
            totals[dist] += strength
    
    return totals


def auto_fill_missing_from_template(row: Dict) -> Dict:
    """Auto-fill missing fields using available information."""
    r = dict(row)
    
    # 1. Fill districts from reserves if empty
    if not r.get('districts') or not r['districts'].strip():
        if r.get('reserves_deployed'):
            totals = extract_district_strength_from_reserves(r['reserves_deployed'])
            if totals:
                r['districts'] = ", ".join(sorted(totals.keys()))
    
    # 2. Ensure Nil for common nil fields
    nil_fields = ['disciplinary_issues', 'reserves_detained', 'training', 'welfare', 'issues_for_phq']
    for field in nil_fields:
        if not r.get(field) or not r[field].strip():
            r[field] = "Nil"
        elif r[field].lower().strip() in ['nil', 'none', 'no', 'n/a', '-', '']:
            r[field] = "Nil"
    
    return r


def generate_remarks(row: Dict) -> str:
    """Generate a summary paragraph from extracted data."""
    # Auto-fill first
    filled = auto_fill_missing_from_template(row)
    
    parts = []
    
    # Unit name
    unit = (filled.get('unit_name') or "").strip()
    if unit:
        parts.append(f"{unit} submitted the daily status report.")
    
    # Reserves deployed
    reserves = filled.get('reserves_deployed', '')
    if reserves:
        dmap = extract_district_strength_from_reserves(reserves)
        if dmap:
            total = sum(dmap.values())
            dist_list = ", ".join([f"{k} ({v})" for k, v in dmap.items()])
            parts.append(f"Reserves deployed: {total} personnel across {len(dmap)} district(s) - {dist_list}.")
        else:
            parts.append(f"Reserves deployed as detailed in report.")
    
    # Districts
    dists = filled.get('districts', '')
    if dists and not parts[-1].startswith("Reserves deployed"):
        parts.append(f"Force deployed in: {dists}.")
    
    # CO interaction date
    date = filled.get('co_interaction_date', '')
    if date:
        parts.append(f"CO's last interaction with SP was on {date}.")
    
    # Disciplinary
    disc = filled.get('disciplinary_issues', 'Nil')
    if disc.lower() == 'nil':
        parts.append("No disciplinary issues reported.")
    else:
        parts.append(f"Disciplinary issues: {disc}.")
    
    # Welfare
    welfare = filled.get('welfare', 'Nil')
    if welfare and welfare.lower() != 'nil':
        parts.append(f"Welfare: {welfare}.")
    
    # Reserves available
    avail = filled.get('reserves_available', '')
    if avail:
        parts.append(f"Reserves available in Bn: {avail}.")
    
    # Issues for PHQ
    issues = filled.get('issues_for_phq', 'Nil')
    if issues and issues.lower() != 'nil':
        parts.append(f"Issues for PHQ: {issues}.")
    
    return " ".join(parts)


def generate_summary_statistics(row: Dict, confidences: Dict) -> Dict:
    """Generate summary statistics from extracted data."""
    stats = {
        "total_fields": len(row),
        "filled_fields": sum(1 for v in row.values() if v and str(v).strip()),
        "empty_fields": sum(1 for v in row.values() if not v or not str(v).strip()),
        "high_confidence": sum(1 for c in confidences.values() if c >= 0.7),
        "medium_confidence": sum(1 for c in confidences.values() if 0.5 <= c < 0.7),
        "low_confidence": sum(1 for c in confidences.values() if c < 0.5),
        "average_confidence": sum(confidences.values()) / len(confidences) if confidences else 0,
    }
    
    stats["fill_rate"] = stats["filled_fields"] / stats["total_fields"] if stats["total_fields"] > 0 else 0
    stats["confidence_rate"] = stats["high_confidence"] / stats["total_fields"] if stats["total_fields"] > 0 else 0
    
    return stats
