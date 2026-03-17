import asyncio
import re
import httpx
from typing import List, Dict, Any
from logging import info, error

from src.schema import RawJobMatchList, RawJobMatch, PipelineSettings, WorkSetting, SeniorityLevel


class JobScraperService:
    """
    A professional service to handle multi-source job scraping.
    Abstracts API complexity and provides unified data normalization.
    """

    def __init__(self, settings: PipelineSettings):
        self.settings = settings
        self.api_cfg = settings.api_settings
        self.scrap_cfg = settings.scraper_settings
        self._semaphore = (
            asyncio.Semaphore(1) if self.api_cfg.free_tier else asyncio.Semaphore(3)
        )

    async def run_research(self, queries: List[str], location: str) -> RawJobMatchList:
        """Primary entry point to gather jobs from all enabled sources."""
        if not (self.api_cfg.use_google or self.api_cfg.use_linkedin):
            info("⚠️ No scrapers enabled. Skipping search.")
            return RawJobMatchList(jobs=[])

        location_clean = location.lower().replace("uk", "united kingdom")

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for q in queries:
                if self.api_cfg.use_google:
                    tasks.append(self._scrape_google(client, q, location_clean))
                if self.api_cfg.use_linkedin:
                    tasks.append(self._scrape_linkedin(client, q, location_clean))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._process_and_deduplicate(results)

    async def _scrape_google(
        self, client: httpx.AsyncClient, query: str, location: str
    ) -> List[RawJobMatch]:
        """Internal handler for SerpAPI (Google Jobs)."""
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "hl": "en",
            "lrad": str(self.scrap_cfg.distance_param),
            "gl": self.scrap_cfg.region,
            "api_key": self.api_cfg.serpapi_key,
        }
        try:
            response = await client.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()
            raw_results = data.get("jobs_results", [])
            return [self._map_google_to_schema(job) for job in raw_results]
        except Exception as e:
            error(f"Google Scrape Error for query '{query}': {e}")
            return []

    async def _scrape_linkedin(
        self, client: httpx.AsyncClient, query: str, location: str
    ) -> List[RawJobMatch]:
        """Internal handler for RapidAPI (LinkedIn). Uses semaphore for rate limiting."""
        async with self._semaphore:
            headers = {
                "X-RapidAPI-Key": self.api_cfg.rapidapi_key,
                "X-RapidAPI-Host": "linkedin-job-search-api.p.rapidapi.com",
            }
            params = {
                "limit": self.scrap_cfg.max_jobs,
                "location_filter": f"{location} {self.scrap_cfg.region}",
                "title_filter": query,
            }
            try:
                response = await client.get(
                    "https://linkedin-job-search-api.p.rapidapi.com/active-jb-7d",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                jobs = data if isinstance(data, list) else data.get("jobs", [])

                if self.api_cfg.free_tier:
                    await asyncio.sleep(1.5)

                return [self._map_linkedin_to_schema(job) for job in jobs]
            except Exception as e:
                error(f"LinkedIn Scrape Error for query '{query}': {e}")
                return []

    def _get_highlights(self, highlights: list[dict]) -> list[dict]:
        if highlights:
            return {
                highlight["title"]: highlight["items", []]
                for highlight in highlights
                if "title" in highlight
            }
        return {}

    def _get_best_apply_link(self, apply_options: list[dict]) -> str:
        """Prioritizes LinkedIn, Indeed, and Reed in that order.
        Falls back to the first available link if no priority match is found."""
        if not apply_options:
            return ""

        options_map = {
            opt.get("title"): opt.get("link")
            for opt in apply_options
            if opt.get("link")
        }

        priority_order = ["LinkedIn", "Indeed", "Reed", "Glassdoor", "Totaljobs"]

        for site in priority_order:
            if site in options_map:
                return options_map[site]

        return apply_options[0].get("link", "")

    def _map_google_to_schema(self, item: Dict[str, Any]) -> RawJobMatch:
        """Standardizes Google Jobs results into our RawJobMatch schema."""
        ext = item.get("detected_extensions", {})

        apply_opts = item.get("apply_options", [])
        url = self._get_best_apply_link(apply_opts)
        highlights = self._get_highlights(item.get("highlights", {}))

        return RawJobMatch(
            title=item.get("title", "Unknown Title"),
            company_name=item.get("company_name", "Unknown Company"),
            location=item.get("location", "Unknown Location"),
            job_url=url,
            description=item.get("description", ""),
            salary_string=ext.get("salary", "Not specified"),
            posted_at=ext.get("posted_at", ""),
            qualifications=highlights.get("Qualifications", []),
            benefits=highlights.get("Benefits", []),
            responsibilities=highlights.get("Responsibilities", []),
        )

    def _map_linkedin_to_schema(self, item: Dict[str, Any]) -> RawJobMatch:
        """Standardizes LinkedIn API results into our RawJobMatch schema."""
        sal_raw = item.get("salary_raw", {})
        val = sal_raw.get("value", {})

        contract = False
        schedule = "Unknown"

        for employment_type in item.get("employment_type", []):
            e_type = employment_type.upper()
            if "CONTRACT" in e_type:
                contract = True
            if "FULL" in e_type:
                schedule = "Full-Time"
            if "PART" in e_type:
                schedule = "Part-Time"
            if "INTERN" in e_type:
                schedule = "Internship"

        contract = any(
            re.match(r".+contract.+", e_type)
            for e_type in item.get("employment_type", "").lower()
        )

        title_lower = item.get("title", "").lower()
        setting = WorkSetting.UNKNOWN
        if item.get("remote_derived") or "remote" in title_lower:
            setting = WorkSetting.REMOTE
        elif "hybrid" in title_lower:
            setting = WorkSetting.HYBRID
        elif "onsite" in title_lower:
            setting = WorkSetting.ONSITE

        raw_seniority = item.get("seniority")
        try:
            seniority = SeniorityLevel(raw_seniority) if raw_seniority else SeniorityLevel.NOT_SPECIFIED
        except ValueError:
            seniority = SeniorityLevel.NOT_SPECIFIED

        return RawJobMatch(
            title=item.get("title", "Unknown"),
            company_name=item.get("organization", "Unknown"),
            location=item.get("locations_derived", ["Unknown"])[0],
            job_url=item.get("url", ""),
            salary_min=val.get("minValue"),
            salary_max=val.get("maxValue"),
            work_setting=setting,
            description=item.get("description_text", ""),
            posted_at=item.get("date_posted", ""),
            qualifications=item.get("linkedin_org_specialties", []),
            seniority_level=seniority,
            is_contract=contract,
            schedule_type=schedule,
            
        )

    def _process_and_deduplicate(self, nested_results: List[Any]) -> RawJobMatchList:
        """Flattens results, handles potential errors from gather, and deduplicates by URL."""
        flat_list = []
        for res in nested_results:
            if isinstance(res, list):
                flat_list.extend(res)

        unique_jobs = {j.job_url: j for j in flat_list if j.job_url}
        return RawJobMatchList(jobs=list(unique_jobs.values()))
