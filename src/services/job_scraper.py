import asyncio
import re
import httpx
from typing import List, Dict, Any, Optional
from logging import info, error
from datetime import datetime

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
        if not any([self.api_cfg.use_google, self.api_cfg.use_linkedin, self.api_cfg.use_reed, self.api_cfg.use_indeed, self.api_cfg.use_theirstack]):
            print("No scrapers enabled. Skipping search.")
            return RawJobMatchList(jobs=[])


        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for count, q in enumerate(queries):
                if self.api_cfg.use_google:
                    tasks.append(self._scrape_google(client, q, location))
                if self.api_cfg.use_linkedin:
                    tasks.append(self._scrape_linkedin(client, q, location))
                if self.api_cfg.use_reed:
                    tasks.append(self._scrape_reed(client, q, location))
                if self.api_cfg.use_indeed:
                    if count < 1:
                        tasks.append(self._scrape_indeed(client, q, location))
                if self.api_cfg.use_theirstack:
                    tasks.append(self._scrape_theirstack(client, q, location))

            results = await asyncio.gather(*tasks, return_exceptions=True)
        all_jobs = []
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)
            elif isinstance(res, Exception):
                error(f"Task failed during gather: {res}")

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

    async def _scrape_linkedin(self, client: httpx.AsyncClient, query_obj: SearchStep, location: LocationData):
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

    async def _scrape_reed(self, client: httpx.AsyncClient, step: SearchStep, location: LocationData):
        query_strings = JobQueryCompiler.generate_reed_queries(step)

        search_tasks = []
        for qs in query_strings:
            params = {"keywords": qs, 
                      "locationName": location.reed_string, 
                      "resultsToTake": self.scrap_cfg.max_jobs
                      }

            search_tasks.append(client.get("https://www.reed.co.uk/api/1.0/search", 
                                        params=params, 
                                        auth=(self.api_cfg.reed_key, "")))
        responses = await asyncio.gather(*search_tasks, return_exceptions=True)
        all_job_metas = []
        for resp in responses:
            if isinstance(resp, httpx.Response):
                data = resp.json()
                all_job_metas.extend(data.get("results", []))
        unique_metas = {m['jobId']: m for m in all_job_metas}.values()
        detail_tasks = [self._get_full_reed_job(client, m) for m in unique_metas]
        final_jobs = await asyncio.gather(*detail_tasks, return_exceptions=True)
        return [j for j in final_jobs if isinstance(j, RawJobMatch)]
    
    async def _get_full_reed_job(self, client: httpx.AsyncClient, job: dict) -> dict:
        try:
            job_url = job.get("externalUrl") or job.get("jobUrl") or ""
            job_id = job.get("jobId")
            if not job_id:
                return None
            response = await client.get(f"https://www.reed.co.uk/api/1.0/jobs/{job_id}",
                                        auth=(self.api_cfg.reed_key, ""))
            response.raise_for_status()
            return self._map_reed_to_schema(response.json(), job_url)
        except Exception as e:
            print(f"Reed Scrape Error for job '{job_id}': {e}")
            return None

    def _get_highlights(self, highlights: list[dict]) -> list[dict]:
        return {
            highlight.get("title"): highlight.get("items", [])
            for highlight in highlights
            if isinstance(highlight, dict) and "title" in highlight
        }
    
    async def _scrape_indeed(self, client: httpx.AsyncClient, step: SearchStep, location: LocationData):
        qs = JobQueryCompiler.generate_indeed_queries(step)
        
        headers = {
            'x-api-key': self.api_cfg.indeed_key,
            'Content-Type': "application/json"
        }

        params = JobQueryCompiler.generate_indeed_params(qs, location)
        try:
            resp = await client.get("https://api.hasdata.com/scrape/indeed/listing", 
                                    params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("jobs", [])
            
        except Exception as e:
            print(f"Listing error: {e}")

        unique_metas = {m['url']: m for m in data}.values()
        
        final_jobs = []
        for m in unique_metas:
            job_obj = await self._get_full_indeed_job(client, m, headers)
            if isinstance(job_obj, RawJobMatch):
                final_jobs.append(job_obj)
            await asyncio.sleep(0.5) 

        return final_jobs

    async def _get_full_indeed_job(self, client: httpx.AsyncClient, job: dict, headers: dict) -> Optional[RawJobMatch]:
        url = job.get("url")
        if not url: return None
        
        try:
            response = await client.get("https://api.hasdata.com/scrape/indeed/job", 
                                        params={"url": url}, headers=headers)
            response.raise_for_status()
            return self._map_indeed_to_schema(job, response.json())
        except Exception as e:
            print(f"Error fetching detail for {url}: {e}")
            return None

    def _map_indeed_to_schema(self, job: dict, full_job: dict) -> RawJobMatch:
        details = job.get("details") or []
        work_setting = WorkSetting.UNKNOWN
        schedule_type = "unknown"
        is_contract = False
        for detail in details:
            lower_detail = detail.lower()
            if "contract" in lower_detail.replace("-", " "):
                is_contract = True
            if "hybrid" in lower_detail:
                work_setting = WorkSetting.HYBRID
            if "remote" in lower_detail:
                work_setting = WorkSetting.REMOTE
            if "on site" in lower_detail:
                work_setting = WorkSetting.ONSITE
            if "full time" in lower_detail:
                schedule_type = "Full-time"
            if "part time" in lower_detail:
                schedule_type = "Part-time"
        salary_data = job.get("salary", {})
        salary_min = salary_data.get("min")
        salary_max = salary_data.get("max")

        return RawJobMatch(
            title = job.get("title") or "Unknown title",
            company = job.get("company") or "Unknown company",
            location = job.get("location") or "Unknown location",
            job_url = job.get("url"),
            qualifications = ["Not specified"],
            responsibilities = ["Not specified"],
            benefits = job.get("benefits") or ["Not specified"],
            seniority_level = SeniorityLevel.NOT_SPECIFIED,
            description = full_job.get("descriptionHtml") or full_job.get("description") or job.get("description") or "No description provided",
            salary_max=salary_max,
            salary_min=salary_min,
            schedule_type=schedule_type,
            work_setting=work_setting,
            is_contract=is_contract,
            salary_string="Not specified",
            posted_at=job.get("isoDate") or datetime.now().isoformat()
        )

    async def _scrape_theirstack(self, client: httpx.AsyncClient, step: SearchStep, location: LocationData):
        """
        Internal handler for TheirStack API. 
        Consumes 1 credit per job. Aggregates from LinkedIn, Indeed, and 300k+ sites.
        """
        if not self.api_cfg.theirstack_key:
            return []

        url = "https://api.theirstack.com/v1/jobs/search"
        headers = {
            "Authorization": f"Bearer {self.api_cfg.theirstack_key}",
            "Content-Type": "application/json"
        }
        payload = JobQueryCompiler.generate_theirstack_query(step, location, self.scrap_cfg.max_jobs)
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            raw_results = data.get("data", [])
            if isinstance(raw_results, list):
                return [self._map_theirstack_to_schema(job) for job in raw_results]
            return []
        except Exception as e:
            error(f"TheirStack Scrape Error for {step.title_stems}: {e}")
            return []

    def _map_theirstack_to_schema(self, item: Dict[str, Any]) -> RawJobMatch:
        """Standardizes TheirStack results. No second 'Detail' call needed."""
        work_setting = WorkSetting.UNKNOWN
        if item.get("remote"):
            work_setting = WorkSetting.REMOTE
        if item.get("hybrid"):
            work_setting = WorkSetting.HYBRID
        return RawJobMatch(
            title=item.get("job_title") or "Unknown Title",
            company_name=item.get("company") or "Unknown Company",
            location=item.get("location") or "United Kingdom",
            job_url=item.get("final_url") or item.get("url"),
            description=item.get("description") or "No description provided.",
            salary_min=item.get("min_annual_salary"),
            salary_max=item.get("max_annual_salary"),
            salary_string=item.get("salary_string") or "Not specified",
            work_setting=work_setting,
            posted_at=item.get("date_posted") or datetime.now().isoformat(),
            qualifications=[],
            benefits=[],
            responsibilities=[],
            is_contract=False,
            seniority_level=SeniorityLevel.NOT_SPECIFIED
        )

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
            title=item.get("title") or "Unknown Title",
            company_name=item.get("company_name") or "Unknown Company",
            location=item.get("location") or "Unknown Location",
            job_url=url,
            description=item.get("description") or "",
            salary_string=ext.get("salary") or "Not specified",
            posted_at=ext.get("posted_at") or "",
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
    
    def _map_reed_to_schema(self, job: Dict, job_url: str) -> RawJobMatch:
        try:
            return RawJobMatch(
                title=job.get("jobTitle"),
                company_name=job.get("employerName"),
                location=job.get("locationName"),
                job_url=job_url,
                salary_min=job.get("yearlyMinimumSalary", job.get("minimumSalary")),
                salary_max=job.get("yearlyMaximumSalary", job.get("maximumSalary")),
                salary_string=job.get("salary") or "",
                description=job.get("jobDescription"),
                schedule_type="Full Time" if job.get('fullTime') else "Part Time" if job.get('partTime') else "Unknown",
                is_contract=job.get('contractType') != "Permanent",
                posted_at=job.get('datePosted', ""),
                qualifications=[], 
                responsibilities=[],
                benefits=[]
            )
        except:
            print(f"FAILED TO PARSE JOB: {job}")


    def _process_and_deduplicate(self, flat_list: List[RawJobMatch]) -> RawJobMatchList:
        unique_jobs = {j.job_url: j for j in flat_list if j.job_url}
        return RawJobMatchList(jobs=list(unique_jobs.values()))
    

