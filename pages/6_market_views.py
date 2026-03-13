import json

import streamlit as st

from src.utils.streamlit_utils import init_app
from src.utils.streamlit_cache import get_cached_user_store, get_cached_global_store
from src.utils.altair_handler import (
    MarketAnalytics,
    create_salary_chart,
    create_skill_bar_chart,
    create_location_salary_chart,
    create_market_heatmap,
    create_market_tightness_chart,
)
from src.utils.embeddings_handler import get_embeddings

def display_dashboard(profiles, jobs):
    engine = MarketAnalytics(jobs, profiles)

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


def main_dashboard():
    init_app()

    embeddings = get_embeddings()
    user_store = get_cached_user_store(embeddings)
    global_store = get_cached_global_store(embeddings)
    
    user_index = user_store.get_pinecone_index(st.secrets["PINECONE_NAME"])
    zero_vector = [0.0] * 3072 
    
    profile_results = user_index.query(
        vector=zero_vector,
        top_k=100,
        namespace=user_store._namespace,
        include_metadata=True
    )
    profiles = []
    for m in profile_results.get("matches", []):
        meta = m["metadata"]
        for field in ["job_titles", "key_skills", "industries"]:
            if isinstance(meta.get(field), str):
                meta[field] = json.loads(meta[field])
        profiles.append(meta)

    global_index = global_store.get_pinecone_index(st.secrets["PINECONE_NAME"])
    job_results = global_index.query(
        vector=zero_vector,
        top_k=1000,
        namespace=global_store._namespace,
        include_metadata=True
    )
    jobs = [m["metadata"] for m in job_results.get("matches", [])]

    if jobs and profiles:
        display_dashboard(profiles, jobs)
    else:
        st.info("Gathering more market data... Upload a CV or wait for job syncing.")

if __name__ == "__main__":

    main_dashboard()
