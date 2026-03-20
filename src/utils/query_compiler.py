from src.schema import SearchStep

class JobQueryCompiler:
    @staticmethod
    def to_linkedin(step: SearchStep) -> str:
        """LinkedIn likes: ('Title A' | 'Title B') & 'Skill List'"""
        title_q = " | ".join([f"'{t}:*'" for t in step.title_stems])
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