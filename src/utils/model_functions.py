from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from src.utils.func import ProviderError

def get_model_index(models_list: list[dict], current_model_id: str) -> int:
    """Finds the integer index of the saved model ID in the current options list."""
    ids = [m["id"] for m in models_list]
    try:
        return ids.index(current_model_id)
    except (ValueError, AttributeError):
        return 0


def get_all_gemini_models(api_key: str = None, free_tier: bool = False):
    if free_tier:
        return [
            {
                "id": "gemini-2.5-flash-lite",
                "label": "Gemini 2.5 Flash Lite | 🧠 (Deep Reasoning) | ⚡ (Fast)",
            },
            {
                "id": "gemini-3-flash-preview",
                "label": "Gemini 3 Flash Preview  | 🧠 (Deep Reasoning) | ⚡ (Fast)",
            },
            {
                "id": "gemini-2.5-flash",
                "label": "Gemini 2.5 Flash | 🧠 (Deep Reasoning) | ⚡ (Fast)",
            },
        ]
    try:
        client = genai.Client(api_key=api_key)
        models = [m for m in client.models.list()]
    except ValueError:
        st.info("Invalid key, falling back to free models")
        models = ["gemini-2.5-flash-lite", "gemini-3-flash-preview", "gemini-2.5-flash"]
    return models


def get_gemini_text_models(models: list, free_tier: bool = False):
    if free_tier:
        return models
    suitable_models = []
    for m in models:
        if not is_valid_model(m):
            continue

        model_id = m.name.split("/")[-1]

        label = model_id
        if m.thinking:
            label += " | 🧠 (Deep Reasoning)"
        if "flash" in model_id:
            label += " | ⚡ (Fast)"

        suitable_models.append({"id": model_id, "label": label})

    return sorted(suitable_models, key=lambda model: model.get("id"), reverse=True)


def is_valid_model(model):
    if "generateContent" not in model.supported_actions:
        return False
    model_id = model.name.split("/")[-1].lower()
    if "gemini" not in model.name.lower():
        return False

    return not any(
        x in model_id
        for x in [
            "tts",
            "robotic",
            "experimental",
            "vision",
            "embedding",
            "aqa",
            "image",
            "computer",
        ]
    )


def get_llm_model(api_settings, role):
    """Allows user to define different models for each step of the pipeline"""
    provider = api_settings.ai_provider.lower()
    model_id = getattr(api_settings, f"{provider}_{role}")
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_id or "gemini-2.5-flash-lite",
            api_key=api_settings.gemini_api_key,
            temperature=0.1,
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
    raise ProviderError(f"{provider.title()} is not supported.")


def get_gemini_embedding_model(embedding_model: str, api_key: str):
    return GoogleGenerativeAIEmbeddings(model=embedding_model, api_key=api_key)
