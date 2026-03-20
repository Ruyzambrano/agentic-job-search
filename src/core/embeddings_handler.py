import streamlit as st

from src.utils.model_functions import get_gemini_embedding_model, get_llm_model
from src.utils.func import validate_configuration
from src.schema import ApiSettings


@st.cache_resource
def get_embeddings():
    return get_gemini_embedding_model(
        st.secrets.EMBEDDING_MODEL, st.secrets.GEMINI_API_KEY
    )


def setup_models(api_settings: ApiSettings, provider_models: dict, provider: str):
    roles = ["reader", "researcher", "writer"]
    model_map = {}
    for role in roles:
        model_id = provider_models.get(role)
        validate_configuration(
            model_id, 
            f"{role.title()} model not configured for {provider.upper()}."
        )
        model_map[role] = get_llm_model(api_settings, model_id, provider)
    return model_map


def validate_and_get_models():
    api_settings = st.session_state.pipeline_settings.api_settings
    provider = api_settings.ai_provider.lower()

    validate_configuration(provider, "AI Provider not selected.")
    
    provider_models = api_settings.models.get(provider, {})
    
    if not provider_models:
        st.error(f"No model configuration found for provider: {provider.upper()}")
        st.stop()

    api_key_attr = f"{provider}_api_key"
    api_key = getattr(api_settings, api_key_attr, None)
    
    validate_configuration(api_key, f"API Key for {provider.upper()} is missing.")

    return setup_models(api_settings, provider_models, provider)