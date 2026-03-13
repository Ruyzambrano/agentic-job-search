"""Tools to be used by the agents"""

from logging import info
import asyncio
from typing import List
import re

import httpx
from rapidfuzz import fuzz

from src.schema import ListRawJobMatch, RawJobMatch, PipelineSettings


def extract_best_url(job_result: dict | None) -> str:
    if not job_result or not isinstance(job_result, dict):
        return "Not specified"

    apply_options = job_result.get("apply_options")

    if isinstance(apply_options, list) and len(apply_options) > 0:
        first_link = apply_options[0].get("link")
        if first_link:
            return first_link

    return job_result.get("link") or "Not specified"


async def scrape_for_jobs(
    client: httpx.Client,
    role_keywords: str,
    location: str,
    pipeline_settings: PipelineSettings,
) -> list[RawJobMatch]:
    """Uses the SerpAPI to get a list of jobs"""
    scraper_settings = pipeline_settings.scraper_settings
    print(f"Searching for {role_keywords} roles in {location} within {scraper_settings.distance_param} km")
    
    params = {
        "engine": "google_jobs",
        "q": role_keywords,
        "location": location,
        "hl": "en",
        "lrad": str(scraper_settings.distance_param),
        "gl": scraper_settings.region,
        "api_key": pipeline_settings.api_settings.serpapi_key,
    }
    response = await client.get(
        "https://serpapi.com/search?", params=params, timeout=30.0
    )
    data = response.json()
    return data.get("jobs_results", [])


def format_results(job: dict) -> list[RawJobMatch]:
    extensions = job.get("detected_extensions", {})
    qualifications = extensions.get("qualifications", ["No qualifications specified"])
    if isinstance(qualifications, str):
        qualifications = [qualifications]

    parsed_job = RawJobMatch(
        title=job.get("title", "No title given"),
        company_name=job.get("company_name", "No name given"),
        description=job.get("description", "No description given"),
        job_url=extract_best_url(job),
        location=job.get("location", ""),
        salary_string=extensions.get("salary", ""),
        schedule_type=extensions.get("schedule_type"),
        qualifications=qualifications,
        posted_at=extensions.get("posted_at", ""),
    )
    info(f"Found {parsed_job.title}: {parsed_job.job_url}")
    if parsed_job.title and parsed_job.description:
        info(f"{parsed_job.title} is ACCEPTABLE")
        return parsed_job



async def batch_scrape_jobs(
    queries: List[str], 
    location: str, 
    pipeline_settings: PipelineSettings
) -> ListRawJobMatch:
    """
    Performs multiple Asynchronous calls and returns a single ListRawJobMatch.
    Allows toggling between Google (SerpAPI) and LinkedIn (RapidAPI).
    """
    all_results = []
    location_clean = location.lower().replace("uk", "united kingdom")
    sem = asyncio.Semaphore(1)
    async with httpx.AsyncClient() as client:
        tasks = []
        
        for q in queries:
            if pipeline_settings.api_settings.use_google:
                tasks.append(scrape_for_jobs(client, q, location_clean, pipeline_settings))
            
            if pipeline_settings.api_settings.use_linkedin:
                tasks.append(safe_get_linkedin_jobs(sem, client, q, location_clean, pipeline_settings))
        if not tasks:
            print("⚠️ No scrapers enabled. Skipping search.")
            return ListRawJobMatch(jobs=[])

        results = await asyncio.gather(*tasks)

    for search_result in results:
        for job in search_result:
            if isinstance(job, RawJobMatch):
                all_results.append(job)
            else:
                parsed = format_results(job)
                if parsed:
                    all_results.append(parsed)

    unique_map = {j.job_url: j for j in all_results if j.job_url}
    final_jobs = list(unique_map.values())
    
    print(f"BATCH COMPLETE: Found {len(final_jobs)} jobs using "
          f"Google={'✅' if pipeline_settings.api_settings.use_google else '❌'} | LinkedIn={'✅' if pipeline_settings.api_settings.use_linkedin else '❌'}")
    
    return ListRawJobMatch(jobs=final_jobs)


def sanitize_query(q: str) -> str:
    q = q.upper().strip()
    q = re.sub(r"\s+", " ", q)
    
    raw_terms = re.split(r'\s+OR\s+(?![^\(]*\))', q)
    
    clean_terms = set()
    for term in raw_terms:
        t = term.strip(" -._")
        
        if t.startswith("(") and t.endswith(")"):
            if " AND " in t:
                clean_terms.add(t) 
            else:
                internal = t[1:-1].strip()
                for sub in re.split(r'\s+OR\s+', internal):
                    sub_t = sub.strip(" -._")
                    if sub_t: clean_terms.add(sub_t)
        else:
            if t: clean_terms.add(t)
            
    unique_terms = sorted(list(clean_terms))
    
    return " OR ".join(unique_terms).upper()

def filter_redundant_queries(queries, threshold=85):
    """
    filters queries that are similar to each other
    """
    unique_queries = []
    for q in queries:
        is_redundant = False
        for u in unique_queries:
            score = fuzz.token_sort_ratio(q, u)
            if score >= threshold:
                is_redundant = True
                break

        if not is_redundant:
            unique_queries.append(q)
    return unique_queries

async def safe_get_linkedin_jobs(sem, client, q, location, pipeline_settings):
    async with sem:
        result = await get_linkedin_jobs(client, q, location, pipeline_settings)
        await asyncio.sleep(1.5) 
        return result

async def get_linkedin_jobs(    
    client: httpx.AsyncClient, 
    role_keywords: str,
    location: str,
    pipeline_settings: PipelineSettings,
) -> list[RawJobMatch]:
    scraper_settings = pipeline_settings.scraper_settings 
    
    headers = {
        "X-RapidAPI-Key": pipeline_settings.api_settings.rapidapi_key,
        "X-RapidAPI-Host": "linkedin-job-search-api.p.rapidapi.com"
    }
    
    url_slug = "https://linkedin-job-search-api.p.rapidapi.com/active-jb-7d"
    
    params = {
        "limit": scraper_settings.max_jobs,
        "location_filter": location,
        "title_filter": role_keywords
    }
    
    try:
        response = await client.get(
            url_slug, params=params, headers=headers, timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        print(data)
        if isinstance(data, list):
            raw_results = data
        else:
            raw_results = data.get("jobs", []) or data.get("data", [])
        return [map_json_to_raw_job(job) for job in raw_results]
        
    except Exception as e:
        print(f"LinkedIn Scrape Error: {e}")
        return []

def map_json_to_raw_job(item: dict) -> RawJobMatch:
    work_setting = "Unknown"
    if item.get("remote_derived") is True:
        work_setting = "Remote"
    elif "onsite" in item.get("title", "").lower() or "on-site" in item.get("title", "").lower():
        work_setting = "On-site"
    elif "hybrid" in item.get("title", "").lower() or "hybrid" in item.get("description_text", "").lower():
        work_setting = "Hybrid"

    salary_raw = item.get("salary_raw") or {}
    val = salary_raw.get("value") or {}
    
    employment_types = item.get("employment_type") or []
    schedule = employment_types[0] if employment_types else "Unknown"
    is_contract = "CONTRACTOR" in employment_types

    return RawJobMatch(
        job_url=item.get("url"),
        title=item.get("title"),
        company_name=item.get("organization", "Unknown"),
        location=item.get("locations_derived", ["Unknown"])[0],
        salary_min=val.get("minValue"),
        salary_max=val.get("maxValue"),
        salary_string=f"{salary_raw.get('currency', '')} {val.get('minValue')}-{val.get('maxValue')} per {val.get('unitText')}" if val else "Not specified",
        work_setting=work_setting,
        schedule_type=schedule,
        is_contract=is_contract,
        description=item.get("description_text", ""),
        posted_at=item.get("date_posted", ""),
        qualifications=item.get("linkedin_org_specialties", []) # Example mapping
    )