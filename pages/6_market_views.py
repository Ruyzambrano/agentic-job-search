import altair as alt
import pandas as pd
import streamlit as st

from src.utils.altair_handler import (
    MarketAnalytics,
    create_salary_chart,
    create_skill_bar_chart,
    create_location_salary_chart,
    create_market_heatmap,
    create_market_tightness_chart,
)
from src.utils.vector_handler import get_global_jobs_store, get_user_analysis_store


def main_dashboard():
    global_store = get_global_jobs_store()
    user_store = get_user_analysis_store()

    profiles = user_store.get().get("metadatas", {})
    jobs = global_store.get().get("metadatas", {})

    engine = MarketAnalytics(jobs, profiles)

    # --- Sidebar ---
    with st.sidebar:
        st.header("Dashboard Filters")
        settings = st.multiselect(
            "WFH, Office or Hybrid",
            options=engine.df_j["work_setting"].unique(),
            default=["Remote", "Hybrid", "On-site"],
        )
        seniorities = st.multiselect(
            "Seniority",
            options=engine.df_p["seniority_level"].unique(),
            default=engine.df_p["seniority_level"].unique(),
        )

    # Get Data
    df_j, df_p = engine.get_filtered_data(settings, seniorities)

    # --- Metrics ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Live Opportunities", len(df_j), border=True)
    c2.metric("Available Talent", len(df_p), border=True)
    c3.metric("Market Avg", f"£{df_j['salary_max'].mean()/1000:,.0f}k", border=True)

    # --- Charts ---
    st.subheader("Salary Distribution")
    st.altair_chart(create_salary_chart(df_j), width="stretch")

    st.subheader("Skill Gap Analysis (Supply vs Demand)")
    skill_data = engine.get_skill_delta(df_j, df_p)
    st.altair_chart(create_skill_bar_chart(skill_data))

    # --- Persona Grid ---
    st.subheader("Talent Personas")
    cols = st.columns(3)
    for idx, row in df_p.head(6).iterrows():
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{engine.generate_anon_id(row['summary'])}**")
                job_titles = row["job_titles"]
                display_title = (
                    job_titles[0]
                    if isinstance(job_titles, list) and len(job_titles) > 0
                    else "Professional"
                )

                st.markdown(f"**{row['seniority_level']} {display_title}**")
                st.caption(f"📍 {row['current_location']}")
                st.markdown(" ".join([f"`{s}`" for s in row["key_skills"][:3]]))

    st.subheader("Location")
    st.altair_chart(create_market_tightness_chart(df_j, df_p))
    st.altair_chart(create_location_salary_chart(df_j))
    st.altair_chart(create_market_heatmap(df_p))


if __name__ == "__main__":

    main_dashboard()
