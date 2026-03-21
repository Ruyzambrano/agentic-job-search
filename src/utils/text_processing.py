"""Generic String Manipulation"""
import re
from typing import List
from rapidfuzz import fuzz

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
