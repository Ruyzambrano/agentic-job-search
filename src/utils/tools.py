"""Tools to be used by the agents"""
from os import environ as ENV

from langchain_core.tools import tool
import serpapi

from schema import ListRawJobMatch, RawJobMatch, JobAttributes


@tool
def scrape_for_jobs(
    role_keywords: str, location: str, distance: int = 40
) -> ListRawJobMatch:
    """Uses the SerpAPI to get a list of jobs"""
    location = location.lower().replace("uk", "united kingdom")
    print(
        f"LOG: Searching for {role_keywords} roles in {location} within {distance} miles/km"
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
        print(f"LOG: Found {len(results["jobs_results"])} {role_keywords} jobs!")
        acceptable_jobs = []
        for job in results.get("jobs_results", []):
            extensions = job.get("detected_extensions", {})
            qualifications = extensions.get(
                "qualifications", ["No qualifications specified"]
            )
            if isinstance(qualifications, str):
                qualifications = [qualifications]
            parsed_attributes = JobAttributes(
                salary=extensions.get("salary", ""),
                qualifications=qualifications,
                posted_at=extensions.get("posted_at", ""),
                schedule_type=extensions.get("schedule_type"),
            )
            parsed_job = RawJobMatch(
                title=job.get("title", "No title given"),
                company_name=job.get("company_name", "No name given"),
                attributes=parsed_attributes,
                description=job.get("description", "No description given"),
                job_url=job.get("share_link", ""),
                location=job.get("location", ""),
            )
            if parsed_job.title and parsed_job.description:
                acceptable_jobs.append(parsed_job)

        return ListRawJobMatch(jobs=acceptable_jobs)
    return "Could not find any matching jobs"
