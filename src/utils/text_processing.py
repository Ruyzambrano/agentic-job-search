"""Generic String Manipulation"""

import re
import hashlib
from typing import List
from rapidfuzz import fuzz


def generate_safe_id(input_string: str) -> str:
    """Creates a deterministic, ASCII-only MD5 hash of any string (URL, Title, etc)."""
    if not input_string:
        return "unknown_id"
    return hashlib.md5(input_string.encode("utf-8")).hexdigest()


def clean_text_for_embedding(text: str) -> str:
    """Prevents LLM/Embedding errors by ensuring text is never empty or None."""
    if not text or not str(text).strip():
        return "No description provided."
    return text.strip()


def sanitize_query(q: str) -> str:
    """Cleans up Boolean queries for API compatibility (Google/LinkedIn)."""
    q = q.upper().strip()
    return re.sub(r"\s+", " ", q)


def filter_redundant_queries(queries: List[str], threshold: int = 85) -> List[str]:
    """Filters out queries that are semantically too similar via fuzzy matching."""
    unique = []
    for q in queries:
        if not any(fuzz.token_sort_ratio(q, u) >= threshold for u in unique):
            unique.append(q)
    return unique


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
