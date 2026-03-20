import asyncio
import re
import httpx
from typing import List, Dict, Any
from logging import info, error

from src.schema import RawJobMatchList, RawJobMatch, PipelineSettings, WorkSetting, SeniorityLevel, SearchStep, LocationData
from src.utils.query_compiler import JobQueryCompiler

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

    async def run_research(self, queries: List[SearchStep], location: LocationData) -> RawJobMatchList:
        """Primary entry point to gather jobs from all enabled sources."""
        if not (self.api_cfg.use_google or self.api_cfg.use_linkedin):
            info("⚠️ No scrapers enabled. Skipping search.")
            return RawJobMatchList(jobs=[])


        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for q in queries:
                if self.api_cfg.use_google:
                    tasks.append(self._scrape_google(client, q, location))
                if self.api_cfg.use_linkedin:
                    tasks.append(self._scrape_linkedin(client, q, location))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)
            elif isinstance(res, Exception):
                error(f"⚠️ Task failed during gather: {res}")

        return self._process_and_deduplicate(all_jobs)

    async def _scrape_google(
        self, client: httpx.AsyncClient, query: SearchStep, location: LocationData
    ) -> List[RawJobMatch]:
        """Internal handler for SerpAPI (Google Jobs)."""
        optimised_query = JobQueryCompiler.to_google(query)
        params = {
            "engine": "google_jobs",
            "q": optimised_query,
            "location": location.google_string,
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

    async def _scrape_linkedin(self, client, query_obj: SearchStep, location: LocationData):
        """Internal handler for RapidAPI (LinkedIn). Uses semaphore for rate limiting."""
        async with self._semaphore:
            headers = {
                "X-RapidAPI-Key": self.api_cfg.rapidapi_key,
                "X-RapidAPI-Host": "linkedin-job-search-api.p.rapidapi.com",
            }
            compiled = JobQueryCompiler.to_linkedin(query_obj)
        
            params = {
                "limit": self.scrap_cfg.max_jobs,
                "location_filter": location.linkedin_string,
                "advanced_title_filter": compiled["title"], 
                "description_filter": compiled["skills"],
                "description_type": "text",
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
                error(f"LinkedIn Scrape Error for query '{query_obj}': {e}")
                return []

    def _get_highlights(self, highlights: list[dict]) -> list[dict]:
        return {
            highlight.get("title"): highlight.get("items", [])
            for highlight in highlights
            if isinstance(highlight, dict) and "title" in highlight
        }

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
        print
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
        """Standardizes LinkedIn API results with robust None-handling."""
        sal_raw = item.get("salary_raw") or {}
        val = sal_raw.get("value") or {}
        contract = False
        schedule = "Unknown"
        
        emp_types = item.get("employment_type") or []
        if isinstance(emp_types, str): 
            emp_types = [emp_types]
        for et in emp_types:
            e_type = str(et).upper()
            if "CONTRACT" in e_type:
                contract = True
            if "FULL" in e_type:
                schedule = "Full-Time"
            elif "PART" in e_type:
                schedule = "Part-Time"
            elif "INTERN" in e_type:
                schedule = "Internship"

        if not contract:
            contract = any("contract" in str(et).lower() for et in emp_types)

        title_lower = (item.get("title") or "").lower()
        
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
        except (ValueError, TypeError):
            seniority = SeniorityLevel.NOT_SPECIFIED

        locations = item.get("locations_derived") or ["Unknown"]
        primary_location = locations[0] if locations else "Unknown"

        return RawJobMatch(
            title=item.get("title") or "Unknown",
            company_name=item.get("organization") or "Unknown",
            location=primary_location,
            job_url=item.get("url") or "",
            salary_min=val.get("minValue"),
            salary_max=val.get("maxValue"),
            work_setting=setting,
            description=item.get("description_text") or item.get("linkedin_org_description") or item.get("organization_description") or "No description provided.",
            posted_at=item.get("date_posted") or "",
            qualifications=item.get("linkedin_org_specialties") or [],
            seniority_level=seniority,
            is_contract=contract,
            schedule_type=schedule,
        )

    def _process_and_deduplicate(self, flat_list: List[RawJobMatch]) -> RawJobMatchList:
        unique_jobs = {j.job_url: j for j in flat_list if j.job_url}
        return RawJobMatchList(jobs=list(unique_jobs.values()))
