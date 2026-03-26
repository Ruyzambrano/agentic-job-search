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
    def generate_indeed_queries(step: SearchStep) -> list[str]:
        """Breaks complex SearchSteps into smaller queries"""
        title_skill_pairings = []
        for title in step.title_stems:
            for count, skill in enumerate(step.must_have_skills):
                if count < 1:
                    title_skill_pairings.append(f"{title} {skill}")

        return title_skill_pairings
    
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