"""
Market Intelligence Dashboard
SOP: Visualizes global job market trends vs. user talent profiles.
"""

import streamlit as st

from src.ui.streamlit_cache import get_cached_market_data, get_cached_salary_chart, get_market_dfs
from src.ui.altair_handler import (
    MarketAnalytics,
    create_salary_chart,
    create_skill_bar_chart,
    create_location_salary_chart,
    create_market_tightness_chart,
    get_skill_delta,
)
from src.ui.controllers import init_app

def display_dashboard(profiles: list, jobs: list):
    """Renders the advanced analytical view of market data."""
    df_j, df_p = get_market_dfs(jobs, profiles)
    engine = MarketAnalytics(df_j, df_p)

    with st.sidebar:
        st.header("Dashboard Filters")
        st.caption("Refine the dataset for specific market segments.")

        work_settings = st.multiselect(
            "Work Setting",
            options=list(engine.df_j["work_setting"].unique()),
            default=list(engine.df_j["work_setting"].unique()),
        )

        seniorities = st.multiselect(
            "Seniority Level",
            options=list(engine.df_p["seniority_level"].unique()),
            default=list(engine.df_p["seniority_level"].unique()),
        )

    df_j, df_p = engine.get_filtered_data(work_settings, seniorities)

    st.markdown("### ⚡ Market Snapshot")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("Live Demand", f"{len(df_j)} Roles", border=True)
    with kpi2:
        st.metric("Talent Supply", f"{len(df_p)} Profiles", border=True)
    with kpi3:
        ratio = len(df_j) / max(len(df_p), 1)
        st.metric(
            "Market Tightness",
            f"{ratio:.1f}x",
            help="Jobs per candidate. Higher = Candidate Market.",
            border=True,
        )
    with kpi4:
        avg_max = df_j["salary_max"].mean() if not df_j.empty else 0
        st.metric("Avg. Max Salary", f"£{avg_max/1000:,.0f}k", border=True)

    st.divider()

    tab_financials, tab_skills, tab_geo = st.tabs(
        ["💰 Salary Benchmarking", "🧠 Skill Gap Analysis", "📍 Geographic Dynamics"]
    )

    with tab_financials:
        col_chart, col_stats = st.columns([2, 1])
        with col_chart:
            st.altair_chart(create_salary_chart(df_j), width="stretch")
        with col_stats:
            st.markdown("##### Salary Distribution")
            if not df_j.empty:
                stats = df_j["salary_max"].describe(percentiles=[0.25, 0.5, 0.75])
                st.write(f"**Top 25%:** £{stats['75%']/1000:,.0f}k")
                st.write(f"**Median:** £{stats['50%']/1000:,.0f}k")
                st.write(f"**Entry Level:** £{stats['25%']/1000:,.0f}k")
                st.info(
                    "💡 **Insights:** Target the 75th percentile for high-leverage negotiations."
                )
            else:
                st.write("No salary data available for selected filters.")

    with tab_skills:
        st.subheader("Market Demand vs. Profile Supply")
        skill_data = engine.get_skill_delta(df_j, df_p)
        st.altair_chart(create_skill_bar_chart(skill_data), width="stretch")

        skill_data = engine.get_skill_delta(df_j, df_p)

        if not skill_data.empty and "delta" in skill_data.columns:
            missing_skills = (
                skill_data[skill_data["delta"] < 0].sort_values("delta").head(3)
            )
            if not missing_skills.empty:
                skills_list = ", ".join(
                    [f"`{s}`" for s in missing_skills["skill"].tolist()]
                )
                st.warning(
                    f"⚠️ **Upskilling Opportunity:** Undersupplied in: {skills_list}"
                )
        else:
            st.info("No skill overlap data available yet.")
    with tab_geo:
        st.subheader("Regional Trends")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Competition by City**")
            st.altair_chart(create_market_tightness_chart(df_j, df_p), width="stretch")
        with c2:
            st.markdown("**Salary by Location**")
            st.altair_chart(create_location_salary_chart(df_j), width="stretch")

    st.divider()
    st.subheader("🕵️ Talent Persona Scout")
    st.caption("Anonymized snapshots of candidate profiles in the current pool.")

    persona_cols = st.columns(3)
    for idx, (i, row) in enumerate(df_p.head(6).iterrows()):
        with persona_cols[idx % 3]:
            with st.container(border=True):
                anon_id = engine.generate_anon_id(row["summary"])
                st.markdown(f"**Persona {anon_id}**")

                titles = row.get("job_titles", [])
                primary_title = titles[0] if titles else "Professional"
                st.markdown(f"**{row['seniority_level']} {primary_title}**")

                st.caption(
                    f"📍 {row['current_location']} · 🏠 {row.get('work_preference', 'Hybrid')}"
                )

                years = row.get("years_of_experience", 0)
                st.progress(min(years / 15, 1.0), text=f"{years} yrs experience")

                skills = row.get("key_skills", [])
                st.write(" ".join([f"`{s}`" for s in skills[:3]]))


def main():
    init_app()

    storage = st.session_state.storage_service

    with st.spinner("Fetching Market Data..."):
        profiles, jobs = get_cached_market_data(storage)

    if not jobs or not profiles:
        st.title("📊 Market Insights")
        st.info(
            "Gathering more market data... Upload a CV or wait for global job syncing to unlock this dashboard."
        )
        st.stop()

    display_dashboard(profiles, jobs)


if __name__ == "__main__":
    main()
