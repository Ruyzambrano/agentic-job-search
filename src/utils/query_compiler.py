from src.schema import SearchStep, LocationData

class JobQueryCompiler:
    @staticmethod
    def to_linkedin(step: SearchStep) -> str:
        """LinkedIn likes: ('Title A' | 'Title B') & 'Skill List'"""
        title_q = " | ".join([f"'{t}'" for t in step.title_stems])
        skills_q = " ".join(step.must_have_skills)
        
        return {
            "title": f"({title_q})",
            "skills": skills_q
        }

    @staticmethod
    def to_google(step: SearchStep) -> str:
        """Google likes: (Title A OR Title B) Skill A Skill B"""
        titles = " OR ".join(step.title_stems)
        skills = " ".join(step.must_have_skills)
        return f"({titles}) {skills}"
    

    @staticmethod
    def generate_reed_queries(step: SearchStep) -> list[str]:
        """Breaks a complex SearchStep into individual 
        keyword-only strings for simple APIs."""
        title_skill_pairings = []
        for title in step.title_stems:
            for count, skill in enumerate(step.must_have_skills):
                if count < 1:
                    title_skill_pairings.append(f"{title} {skill}")

        return title_skill_pairings
    
    @staticmethod
    def generate_indeed_queries(step: SearchStep) -> str:
        """Generates only one query"""
        title = step.title_stems[0]
        skill = step.must_have_skills[0]

        return f"{title} {skill}"
    
    @staticmethod
    def generate_indeed_params(keyword: str, location: LocationData) -> dict:
        domain_map = {
            "uk": "uk",
            "us": "www",
            "gb": "uk"
        }
        return {
            "keyword": keyword, 
            "location": location.indeed_string, 
            "domain": f"{domain_map.get(location.country_code.lower(), "uk")}.indeed.com"
        }
    
    @staticmethod
    def generate_theirstack_query(step: SearchStep, location: LocationData, limit: int) -> dict:
        return {
            "job_title_or": [title.lower() for title in step.title_stems], 
            "job_country_code_or": [location.country_code.upper() or "GB"],
            "posted_at_max_age_days": 14,
            "limit": min(limit, 5),
            "job_location_pattern_or": [location.city]
        }