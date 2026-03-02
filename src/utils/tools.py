"""Tools to be used by the agents"""
from os import environ as ENV
from logging import info
import asyncio
import httpx
from typing import List

from langchain_core.tools import tool

from src.schema import ListRawJobMatch, RawJobMatch


def extract_best_url(job_result: dict | None) -> str:
    if not job_result or not isinstance(job_result, dict):
        return "Not specified"

    apply_options = job_result.get("apply_options")

    if isinstance(apply_options, list) and len(apply_options) > 0:
        first_link = apply_options[0].get("link")
        if first_link:
            return first_link

    return job_result.get("link") or "Not specified"


async def scrape_for_jobs(client: httpx.Client,
    role_keywords: str, location: str, distance: int = 40) -> list[RawJobMatch]:
    """Uses the SerpAPI to get a list of jobs"""
    print(f"Searching for {role_keywords} roles in {location} within {distance} miles/km")
    params = {
            "engine": "google_jobs",
            "q": role_keywords,
            "location": location,
            "hl": "en",
            "lrad": str(distance),
            "gl": "uk",
            "api_key": ENV.get("SERPAPI_KEY")
        }
    response = await client.get("https://serpapi.com/search?", params=params)
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

    return "Not acceptable"


@tool
async def batch_scrape_jobs(
    queries: List[str], location: str, distance: int = 40
) -> ListRawJobMatch:
    """Performs multiple Asynchronous SerpAPI calls and returns a single ListRawJobMatch.
    Queries should be a list of search strings"""
    all_results = []
    location = location.lower().replace("uk", "united kingdom")

    async with httpx.AsyncClient() as client:
        tasks = [scrape_for_jobs(client, q, location, distance) for q in queries]
        results = await asyncio.gather(*tasks)
    for search_result in results:
        for job in search_result:
            all_results.append(format_results(job))

    unique_map = {j.job_url: j for j in all_results if j.job_url}
    final_jobs = list(unique_map.values())
    print(f"BATCH SCRAPE COMPLETE: found {len(final_jobs)}")
    return ListRawJobMatch(jobs=final_jobs)
