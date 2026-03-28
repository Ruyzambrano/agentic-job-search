"""Generic String Manipulation"""
import re
from typing import List
from rapidfuzz import fuzz
from datetime import datetime

from src.schema import SearchStep


def clean_text_for_embedding(text: str) -> str:
    """Prevents LLM/Embedding errors by ensuring text is never empty or None."""
    if not text or not str(text).strip():
        return "No description provided."
    return text.strip()


def sanitize_query(q: str) -> str:
    """Cleans up Boolean queries for API compatibility (Google/LinkedIn)."""
    q = q.upper().strip()
    return re.sub(r"\s+", " ", q)




def filter_redundant_queries(plan: List[SearchStep], threshold: int = 80) -> List[SearchStep]:
    """
    Deduplicates SearchStep objects using fuzzy string matching on title clusters.
    """
    unique_queries = []
    
    for query_obj in plan:
        current_titles = " ".join(sorted([t.lower().strip() for t in query_obj.title_stems]))
        
        if not current_titles:
            continue

        is_redundant = False
        for seen_query in unique_queries:
            seen_titles = " ".join(sorted([t.lower().strip() for t in seen_query.title_stems]))
            
            score = fuzz.token_sort_ratio(current_titles, seen_titles)
            
            if score >= threshold:
                is_redundant = True
                break
        
        if not is_redundant:
            unique_queries.append(query_obj)
            
    return unique_queries


def extract_base_locations(location_str: str) -> list[str]:
    """
    Splits 'London / Hybrid / Telford' into ['London', 'Telford']
    and removes parentheticals.
    """
    if not location_str:
        return []

    normalized = location_str.replace("/", "|").replace(",", "|")
    parts = [p.strip() for p in normalized.split("|")]

    clean_cities = []
    for p in parts:
        p_clean = re.sub(r"[\(\[].*?[\)\]]", "", p)
        p_clean = p_clean.replace("(", "").replace(")", "").strip()
        if "remote" in p_clean.lower():
            clean_cities.append("Remote")
        elif "hybrid" in p_clean.lower():
            clean_cities.append("Hybrid")
        elif len(p_clean) > 2:
            clean_cities.append(p_clean.title())

    return sorted(list(set(clean_cities)))



def format_luxury_timestamp(date_val):
    """
    Standardizes any date input into: 28 March 2026 at 09:30
    """
    if not date_val:
        return "Pending Audit"
    
    if isinstance(date_val, datetime):
            return date_val.strftime("%d %B %Y")
        
    date_str = str(date_val).strip()

    if "/" in date_str:
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            return date_obj.strftime("%d %B %Y")
        except ValueError:
            pass
        
    try:
        clean_iso = date_str.replace('Z', '+00:00')
        date_obj = datetime.fromisoformat(clean_iso)
        return date_obj.strftime("%d %B %Y")
    except ValueError:
        return date_str.upper()