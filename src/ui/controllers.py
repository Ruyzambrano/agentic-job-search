import streamlit as st
from src.utils.local_storage import get_local_storage, get_browser_key
from src.schema import PipelineSettings, AgentWeights
from src.ui.streamlit_cache import (
    get_job_analysis,
    get_storage_service,
    get_model_cache,
)
from src.core.embeddings_handler import validate_and_get_models, get_embeddings
from src.utils.func import get_provider_config, get_model_roles, ModelTypeError
from src.utils.model_functions import get_gemini_text_models, get_model_index


def init_app():
    """
    Initializes the application state, defines default settings,
    and hydrates values from the browser's local storage.
    """
    if "pipeline_settings" not in st.session_state:
        st.session_state.pipeline_settings = PipelineSettings()

    storage = get_local_storage()

    if "storage_service" not in st.session_state:
        try:
            embeddings = get_embeddings()
            st.session_state.storage_service = get_storage_service(embeddings)
        except Exception as e:
            st.error(f"Failed to initialize Storage Service: {e}")

    hydrate_keys(storage)

    hydrate_settings(
        "weights",
        ["key_skills", "seniority_weight", "experience", "retention_risk"],
        storage,
    )

    hydrate_settings(
        "scraper_settings", ["region", "max_jobs", "distance_param"], storage
    )

    if "last_updated" not in st.session_state:
        st.session_state.last_updated = 0.0

    


def hydrate_keys(storage):
    """Business Logic: Maps browser strings to our Pydantic API settings."""
    st.session_state.provider_config = get_provider_config()
    st.session_state.model_roles = get_model_roles()

    new_data_found = False
    keys_to_fetch = [
        "serpapi_key",
        "ai_provider",
        "rapidapi_key",
        "use_google",
        "use_linkedin",
        "free_tier",
    ]

    for provider, item in st.session_state.provider_config.items():
        keys_to_fetch.append(item.get("key"))
        for role in st.session_state.model_roles:
            keys_to_fetch.append(f"{provider.lower()}_{role}")

    for k in keys_to_fetch:
        old_val = getattr(st.session_state.pipeline_settings.api_settings, k, None)
        new_val = get_browser_key(k, storage, "api_settings")

        if new_val is not None and new_val != old_val:
            new_data_found = True

    if new_data_found:
        st.rerun()


def hydrate_settings(setting_type: str, keys: list[str], storage):
    """Helper to hydrate non-API settings."""
    for key in keys:
        get_browser_key(key, storage, setting_type)


def process_new_cv(raw_cv_text: str, desired_role: str, desired_location: str):
    """
    Controller for the 'New CV' flow.
    Constructs the Graph config and triggers the async matching pipeline.
    """
    if not raw_cv_text:
        st.error("No CV text found to process.")
        return None

    # Prepare configuration for the LangGraph nodes
    config = {
        "configurable": {
            "user_id": st.user.sub if st.user else "local-user",
            "location": desired_location,
            "role": desired_role,
            "pipeline_settings": st.session_state.pipeline_settings,
            "storage_service": st.session_state.storage_service,
        }
    }

    models = validate_and_get_models()

    return get_job_analysis(raw_cv_text, config, models)


def search_for_new_jobs(active_profile_meta: dict, user_id: str):
    """
    Controller for the 'Existing Profile' flow.
    Re-runs the researcher and writer nodes without re-parsing the CV.
    """
    profile_id = active_profile_meta.get("profile_id")

    config = {
        "configurable": {
            "user_id": user_id,
            "active_profile_id": profile_id,
            "location": st.session_state.get("desired_location", ""),
            "role": st.session_state.get("desired_role", ""),
            "pipeline_settings": st.session_state.pipeline_settings,
            "storage_service": st.session_state.storage_service,
        }
    }

    models = validate_and_get_models()

    return get_job_analysis("", config, models)


def initialise_pipeline_settings():
    """Ensures PipelineSettings object exists in session state."""
    if "pipeline_settings" not in st.session_state:
        st.session_state.pipeline_settings = PipelineSettings()


def reset_setting_to_default_values(setting_type: str, storage):
    """Resets specific settings groups to their Pydantic defaults."""
    from src.utils.local_storage import set_new_key

    if setting_type == "weights":
        defaults = AgentWeights().model_dump()
        for key, value in defaults.items():
            set_new_key(key, value, storage, setting_type)
        st.toast("Weights reset to defaults.")


def handle_profile_deletion(storage, profile_id):
    """Logic for deleting a profile and cleaning up the app state."""
    success = storage.delete_current_profile(profile_id)
    if success:
        if st.session_state.get("active_profile_id") == profile_id:
            st.session_state.pop("active_profile_id", None)
        st.success("Profile deleted successfully!")
        return True
    else:
        st.error("Technical error: Could not remove profile from database.")
        return False


def set_models_for_pipeline(new_provider: str, free_tier: bool = False) -> dict:
    api_settings = st.session_state.pipeline_settings.api_settings
    if new_provider == "Gemini" and getattr(api_settings, "gemini_api_key", None):
        all_models = get_model_cache(api_settings.gemini_api_key, free_tier)
        text_models = get_gemini_text_models(all_models, free_tier)
        return get_models_for_pipelines(text_models, new_provider.lower())
    # TODO: Implement openai and anthropic
    # if new_provider == "OpenAI" and getattr(api_settings, "openai_api_key", None):
    #     st.header("TODO: Get models")


def get_models_for_pipelines(text_models: list[dict], new_provider: str):
    api = st.session_state.pipeline_settings.api_settings
    model_dict = api.models.get(new_provider)
    if not model_dict:
        raise ModelTypeError("Invalid Model Type")
    current_reader = model_dict.get("reader")
    current_researcher = model_dict.get("researcher")
    current_writer = model_dict.get("writer")
    if st.toggle("Use different models for the agents?", value=True):
        reader, researcher, writer = st.columns(3)
        with reader:
            reader_model = st.selectbox(
                "Select a CV Parser",
                options=text_models,
                format_func=lambda x: x.get("label").title().replace("-", " "),
                key=f"select_{new_provider}_reader",
                index=get_model_index(text_models, current_reader),
            )
        with researcher:
            researcher_model = st.selectbox(
                "Select a Researcher",
                options=text_models,
                format_func=lambda x: x.get("label").title().replace("-", " "),
                key=f"select_{new_provider}_researcher",
                index=get_model_index(text_models, current_researcher),
            )
        with writer:
            writer_model = st.selectbox(
                "Select an Analyser",
                options=text_models,
                format_func=lambda x: x.get("label").title().replace("-", " "),
                key=f"select_{new_provider}_writer",
                index=get_model_index(text_models, current_writer),
            )
    else:
        reader_model = st.selectbox(
            "Select an Embedder",
            options=text_models,
            format_func=lambda x: x.get("label").title().replace("-", " "),
            key=f"select_{new_provider}_all_nodes",
            index=get_model_index(text_models, current_reader),
        )
        researcher_model = reader_model
        writer_model = researcher_model

    return {
        "reader": reader_model.get("id"),
        "writer": writer_model.get("id"),
        "researcher": researcher_model.get("id"),
    }
