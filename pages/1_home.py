"""See your profiles and Jobs"""

import streamlit as st

from src.utils.streamlit_utils import (
    display_profile,
    filter_for_profiles,
    display_job_matches,
    search_for_new_jobs,
    delete_profile_dialogue,
    cv_handler,
    process_new_cv,
    init_app,
)
from src.utils.embeddings_handler import get_embeddings
from src.utils.streamlit_cache import (
    get_cached_global_store,
    get_cached_jobs_for_profile,
    get_cached_user_store,
)


def main_page():
    init_app()
    embedding = get_embeddings(st.session_state.pipeline_settings.api_settings)
    user_vector_store = get_cached_user_store(embedding)
    global_jobs_store = get_cached_global_store(embedding)

    user_id = st.user.sub

    if st.sidebar.button("Add New CV", width="stretch"):
        cv_handler()

    if st.session_state.get("start_processing"):
        with st.status("Running Agent Pipeline...", expanded=True) as status:
            st.write("Analyzing CV...")
            analysis = process_new_cv(
                st.session_state.raw_cv_text,
                st.session_state.desired_role,
                st.session_state.desired_location,
            )
            st.session_state["job_analysis"] = analysis
            st.session_state.start_processing = False
            status.update(label="Analysis Complete!", state="complete")
            st.session_state.raw_cv_text = None
        st.rerun()
    try:
        active_profile_meta = filter_for_profiles(user_vector_store, user_id)

    except ValueError:
        st.write("# Upload a CV to begin.")
        st.stop()

    with st.sidebar:
        st.session_state.desired_role = (
            st.text_input(
                label="Desired Role", placeholder="A Role Like 'Data Engineer'"
            )
            or "Data Engineer"
        )
        st.session_state.desired_location = (
            st.text_input(
                label="Desired Location", placeholder="A Location Like 'London'"
            )
            or "London"
        )

        if st.button("Find jobs for the current profile", use_container_width=True):
            st.session_state["job_analysis"] = search_for_new_jobs(
                active_profile_meta, user_id
            )
            get_cached_jobs_for_profile.clear()
        sorting = st.empty()

        st.divider()
        st.write("### Danger Zone:")
        if st.button(
            "Permanently Delete Current Profile",
            use_container_width=True,
            type="primary",
        ):
            delete_profile_dialogue(
                user_vector_store, active_profile_meta.get("profile_id")
            )
            get_cached_jobs_for_profile.clear()

    display_profile(profile=active_profile_meta)

    jobs = get_cached_jobs_for_profile(
        user_vector_store, active_profile_meta.get("profile_id")
    )

    if jobs:
        sort_by = sorting.selectbox(
            label="Sort Jobs by", options=["Score", "Analysis Date", "Company", "Role"]
        )
        st.header("Matched Jobs")
        display_job_matches(jobs, sort_by)


if __name__ == "__main__":
    main_page()
