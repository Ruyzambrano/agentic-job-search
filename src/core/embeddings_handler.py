import streamlit as st

from src.utils.model_functions import get_gemini_embedding_model, get_llm_model
from src.utils.func import validate_configuration


@st.cache_resource
def get_embeddings():
    return get_gemini_embedding_model(
        st.secrets.EMBEDDING_MODEL, st.secrets.GEMINI_API_KEY
    )


def setup_models(api_settings):
    roles = ["reader", "researcher", "writer"]
    model_map = {}
    for role in roles:
        model_map[role] = get_llm_model(api_settings, role)
    return model_map


def validate_and_get_models():
    api_settings = st.session_state.pipeline_settings.api_settings
    provider = api_settings.ai_provider.lower()

    validate_configuration(provider, "AI Provider not configured.")

    for model_type in ["reader", "researcher", "writer"]:
        model_key = f"{provider}_{model_type}"
        model_id = getattr(api_settings, model_key, None)

        validate_configuration(model_id, f"{model_type.title()} Model not configured.")

    api_string = f"{provider}_api_key"
    api_key = getattr(api_settings, api_string, None)
    validate_configuration(api_key, "API Key not configured.")
    return setup_models(api_settings)
