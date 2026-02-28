"""Tools to be used by the agents"""
from os import environ as ENV

from langchain_core.tools import tool
import serpapi

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

@tool
def scrape_for_jobs(
    role_keywords: str, location: str, distance: int = 40
) -> ListRawJobMatch:
    """Uses the SerpAPI to get a list of jobs"""
    location = location.lower().replace("uk", "united kingdom")
    print(
        f"Searching for {role_keywords} roles in {location} within {distance} miles/km"
    )
    client = serpapi.Client(api_key=ENV.get("SERPAPI_KEY"))
    results = client.search(
        {
            "engine": "google_jobs",
            "q": role_keywords,
            "location": location,
            "hl": "en",
            "lrad": str(distance),
            "gl": "uk",
        }
    )

    if "jobs_results" in results:
        print(f"Found {len(results["jobs_results"])} {role_keywords} jobs!")
        acceptable_jobs = []
        for job in results.get("jobs_results", []):
            extensions = job.get("detected_extensions", {})
            qualifications = extensions.get(
                "qualifications", ["No qualifications specified"]
            )
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
                posted_at=extensions.get("posted_at", "")

            )
            if parsed_job.title and parsed_job.description:
                acceptable_jobs.append(parsed_job)

        return ListRawJobMatch(jobs=acceptable_jobs)
    return "Could not find any matching jobs"
