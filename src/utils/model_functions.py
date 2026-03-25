import streamlit as st
from google import genai
from anthropic import Anthropic
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from src.utils.func import ProviderError


def get_model_index(models_list: list[dict], current_model_id: str) -> int:
    """Finds the integer index of the saved model ID in the current options list."""
    if not current_model_id:
        return 0
    ids = [m["id"] for m in models_list]
    try:
        return ids.index(current_model_id)
    except (ValueError, AttributeError):
        return 0

def get_all_anthropic_models(api_key: str = None, free_tier: bool = False):
    """Fetches all available Claude models"""
    if free_tier or not api_key:
        return []
    try: 
        client = Anthropic(
            api_key=api_key
        )
        page = client.models.list()
        return page
    except Exception as e:
        st.write(str(e))
        return []

def get_anthropic_text_models(models: list, free_tier: bool = False):
    """Filters Anthropic models and adds capability-based badges."""
    if not models or not isinstance(models[0], dict):
        return models

    suitable_models = []
    
    for m in models:
        if not is_valid_anthropic_model(m):
            continue

        model_id = m.get("id")
        label = m.get("display_name", model_id)
        caps = m.get("capabilities", {})

        if caps.get("thinking", {}).get("supported"):
            label += " | 🧠 (Thinking Mode)"
        
        if "haiku" in model_id:
            label += " | ⚡ (Fast & Cheap)"
            
        if "opus" in model_id:
            label += " | 🏆 (SOTA Reasoning)"

        suitable_models.append({"id": model_id, "label": label})

    return sorted(suitable_models, key=lambda x: x["id"], reverse=True)


def is_valid_anthropic_model(model: dict) -> bool:
    """Filters out specialized/internal Anthropic models."""
    model_id = model.get("id", "").lower()
    
    exclude_list = [
        "moderation", 
        "legacy", 
        "search-index", 
        "vision-only", 
        "internal"
    ]
    
    if any(x in model_id for x in exclude_list):
        return False
        
    return "claude" in model_id and ("4-" in model_id or "5-" in model_id)

def get_all_gemini_models(api_key: str = None, free_tier: bool = False):
    """Fetches available models from Google API or returns hardcoded free tier."""
    if free_tier or not api_key:
        return [
            {
                "id": "gemini-2.5-flash",
                "label": "Gemini 2.5 Flash | ⚡ (Fast)",
            },
            {
                "id": "gemini-2.5-flash-lite",
                "label": "Gemini 2.5 Flash Lite | ⚡ (Lite)",
            },
            {
                "id": "gemini-3-flash-preview",
                "label": "Gemini 3 Flash Preview | 🧠 (Deep Reasoning)",
            },
            {
                "id": "gemini-3.1-flash-lite-preview",
                "label": "Gemini 3.1 Flash Lite | 🧠 (Deep Reasoning) | ⚡ (Lite)"
            }
        ]
    try:
        client = genai.Client(api_key=api_key)
        models = [m for m in client.models.list()]
        return models
    except Exception as e:
        st.warning(f"Could not fetch live models: {e}. Using defaults.")
        return get_all_gemini_models(free_tier=True)


def get_gemini_text_models(models: list, free_tier: bool = False):
    """Filters raw API models for those suitable for text generation."""
    if free_tier or not models or isinstance(models[0], dict):
        return models

    suitable_models = []
    for m in models:
        if not is_valid_model(m):
            continue

        model_id = m.name.split("/")[-1]
        label = model_id

        if getattr(m, "thinking", False):
            label += " | 🧠 (Deep Reasoning)"
        if "flash" in model_id:
            label += " | ⚡ (Fast)"
        if "pro" in model_id:
            label += " | ✨ (Premium)"

        suitable_models.append({"id": model_id, "label": label})

    return sorted(suitable_models, key=lambda model: model.get("id"), reverse=True)


def is_valid_model(model) -> bool:
    """Security/Utility filter for Google models."""
    if "generateContent" not in model.supported_actions:
        return False

    model_name = model.name.lower()
    model_id = model_name.split("/")[-1]

    exclude_list = [
        "tts",
        "robotic",
        "experimental",
        "vision",
        "embedding",
        "aqa",
        "image",
        "computer",
    ]
    if any(x in model_id for x in exclude_list):
        return False

    return "gemini" in model_name


def get_llm_model(api_settings, model_id: str, provider: str):
    """
    Factory: Returns the specific LangChain Chat object for a pipeline role.
    Roles: 'reader', 'writer', 'researcher'
    """
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_id or "gemini-3-flash-preview",
            api_key=api_settings.gemini_api_key,
            temperature=0.1,
            max_retries=3,
        )

    elif provider == "openai":
        return ChatOpenAI(
            model=model_id or "gpt-4o-mini",
            api_key=api_settings.openai_api_key,
            temperature=0.1,
        )

    elif provider == "anthropic":
        return ChatAnthropic(
            model=model_id or "claude-3-5-haiku",
            api_key=api_settings.anthropic_api_key,
            temperature=0.1,
        )

    raise ProviderError(f"Provider '{provider}' is not configured or supported.")


def get_gemini_embedding_model(model_id: str, api_key: str):
    """Returns the embedding engine used by the StorageService."""
    return GoogleGenerativeAIEmbeddings(model=model_id, api_key=api_key)
