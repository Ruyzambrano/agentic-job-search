import altair as alt
import pandas as pd
import hashlib
import re


class MarketAnalytics:
    def __init__(self, jobs: list, profiles: list):
        self.df_j = jobs
        self.df_p = profiles

        list_cols = [
            "job_titles",
            "key_skills",
            "industries",
            "qualifications",
            "key_skills",
        ]
        for col in list_cols:
            if col in self.df_p.columns:
                self.df_p[col] = self.df_p[col].apply(
                    lambda x: x if isinstance(x, list) else []
                )
            if col in self.df_j.columns:
                self.df_j[col] = self.df_j[col].apply(
                    lambda x: x if isinstance(x, list) else []
                )

        self.df_p["summary"] = self.df_p["summary"].fillna("")
        self.df_p["seniority_level"] = self.df_p["seniority_level"].fillna(
            "Not Specified"
        )

        self.df_j[["clean_location", "work_style"]] = self.df_j["location"].apply(
            lambda x: pd.Series(normalize_location(x))
        )

        self.df_p[["clean_location", "work_style"]] = self.df_p[
            "current_location"
        ].apply(lambda x: pd.Series(normalize_location(x)))

    def get_filtered_data(self, settings: list, seniorities: list):
        """Returns filtered DataFrames based on UI selection."""
        jf = self.df_j[self.df_j["work_setting"].isin(settings)]
        pf = self.df_p[self.df_p["seniority_level"].isin(seniorities)]
        return jf, pf

    def get_skill_delta(self, df_j, df_p, top_n=15):
        """Calculates Supply vs Demand for skills."""
        demand = count_skills(df_j, "qualifications").assign(Source="Market Demand")
        supply = count_skills(df_p, "key_skills").assign(Source="Talent Supply")

        combined = pd.concat([demand, supply])

        top_skills = combined.groupby("Skill")["Count"].sum().nlargest(top_n).index

        return combined[combined["Skill"].isin(top_skills)]

    @staticmethod
    def generate_anon_id(text: str) -> str:
        safe_text = str(text) if text is not None else ""
        return f"ID-{hashlib.md5(safe_text.encode()).hexdigest()[:6].upper()}"


def create_salary_chart(df):
    return (
        alt.Chart(df)
        .mark_area(opacity=0.5, interpolate="monotone")
        .encode(
            x=alt.X("salary_max:Q", bin=alt.Bin(maxbins=20), title="Annual Salary (£)"),
            y=alt.Y("count():Q", title="Jobs", stack=None),
            color=alt.Color("work_setting:N", scale=alt.Scale(scheme="tableau10")),
            tooltip=["work_setting", "count()"],
        )
        .properties(height=300)
    )


def create_skill_bar_chart(df_skills):
    return (
        alt.Chart(df_skills)
        .mark_bar()
        .encode(
            x=alt.X(
                "Skill:N",
                title=None,
                axis=alt.Axis(
                    labelAngle=-60,
                    labelOverlap=False,
                    labelFontSize=13,
                    tickCount=len(df_skills["Skill"].unique()),
                ),
                sort="-y",
            ),
            y=alt.Y("Count:Q", title="Frequency"),
            color=alt.Color("Skill:N", scale=alt.Scale(range=["#F58518"])),
            tooltip=["Skill", "Source", "Count"],
        )
        .properties(width=40, height=400)
    )


def count_skills(df, col):
    exploded = df.explode(col)
    counts = exploded[col].value_counts().reset_index()
    counts.columns = ["Skill", "Count"]
    return counts


def create_location_salary_chart(df):
    return (
        alt.Chart(df)
        .mark_boxplot(extent="min-max")
        .encode(
            x=alt.X("salary_max:Q", title="Annual Salary (£)"),
            y=alt.Y("clean_location:N", sort="-x", title="Location"),
            color=alt.Color(
                "location:N", legend=None, scale=alt.Scale(scheme="tableau20")
            ),
            tooltip=["location", "salary_max", "salary_min"],
        )
        .properties(height=400, title="Salary Ranges by Location")
    )


def create_market_heatmap(df):
    return (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("seniority_level:N", title="Seniority"),
            y=alt.Y("clean_location:N", title="Location", sort="-color"),
            color=alt.Color(
                "count():Q", scale=alt.Scale(scheme="viridis"), title="Job Count"
            ),
            tooltip=["clean_location", "seniority_level", "count()"],
        )
        .properties(height=400, title="Market Density: Location vs. Seniority")
    )


def create_market_tightness_chart(df_j, df_p):
    loc_stats = (
        df_j.groupby("clean_location")
        .agg({"salary_max": "mean", "job_url": "count"})
        .reset_index()
    )

    cand_stats = (
        df_p.groupby("clean_location").size().reset_index(name="candidate_count")
    )

    merged = pd.merge(loc_stats, cand_stats, on="clean_location")

    return (
        alt.Chart(merged)
        .mark_circle(size=100)
        .encode(
            x=alt.X("salary_max:Q", title="Average Max Salary (£)"),
            y=alt.Y("candidate_count:Q", title="Candidate Volume"),
            size=alt.Size("job_url:Q", title="Open Roles"),
            color=alt.Color("clean_location:N", legend=None),
            tooltip=["clean_location", "salary_max", "candidate_count", "job_url"],
        )
        .properties(height=400, title="Market Tightness: Supply vs Demand per City")
        .interactive()
    )


def normalize_location(loc_str: str):
    if not loc_str or pd.isna(loc_str):
        return "Unknown", "Unknown"

    text = loc_str.lower()

    style = "On-site"
    if "remote" in text:
        style = "Remote"
    elif "hybrid" in text or "flexible" in text:
        style = "Hybrid"

    clean_city = re.sub(r"\(.*?\)", "", text)
    clean_city = re.sub(r"uk-|-uk|uk", "", clean_city)

    parts = re.split(r"[/|,-]", clean_city)
    city = parts[0].strip().title()

    if city in ["Remote", ""]:
        city = "Remote"

    return city, style


def get_skill_delta(self, df_j, df_p):
    """
    SOP: Calculates the gap between Job Demand and Talent Supply.
    Returns a DataFrame with columns: ['skill', 'demand', 'supply', 'delta']
    """
    job_skills = df_j["key_skills"].explode().value_counts().to_dict()
    profile_skills = df_p["key_skills"].explode().value_counts().to_dict()

    all_skills = set(list(job_skills.keys()) + list(profile_skills.keys()))

    data = []
    for skill in all_skills:
        demand = job_skills.get(skill, 0)
        supply = profile_skills.get(skill, 0)
        data.append(
            {
                "skill": skill,
                "demand": demand,
                "supply": supply,
                "delta": supply - demand,
            }
        )

    delta_df = pd.DataFrame(data)

    if delta_df.empty:
        return pd.DataFrame(columns=["skill", "demand", "supply", "delta"])

    return delta_df.sort_values("demand", ascending=False)
