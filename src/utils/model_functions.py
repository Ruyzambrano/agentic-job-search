from google import genai

def get_gemini_models_safe(api_key: str = None, free_tier: bool = False):
    """
    Returns a default list of models if no key is provided, 
    otherwise fetches the live list from Google.
    """
    basic_models = ["gemini-2.5-flash-lite", "gemini-3-flash-preview", "gemini-2.5-flash"]
    default_models = [{"id": m, "label": f"m | 🧠 (Deep Reasoning) | ⚡ (Fast)"} for m in basic_models]
    if not api_key or len(api_key) < 10 or free_tier: 
        return sorted(default_models, key=lambda model: model.get("id"), reverse=True)
    try:
        client = genai.Client(api_key=api_key)
        suitable_models = []
        for m in client.models.list():
            if "gemini" not in m.name.lower():
                continue
            if "generateContent" not in m.supported_actions:
                continue
            
            model_id = m.name.split('/')[-1]
            
            if any(x in model_id for x in ["robotic", "experimental", "vision", "embedding", "aqa"]):
                continue

            label = model_id
            if m.thinking:
                label += " | 🧠 (Deep Reasoning)"
            if "flash" in model_id:
                label += " | ⚡ (Fast)"

            suitable_models.append({"id": model_id, "label": label})

        return sorted(suitable_models, key=lambda model: model.get("id"), reverse=True)

    except Exception as e:
        st.error(f"{e} Not a valid ID, falling back to base models")
        return sorted(default_models, key=lambda model: model.get("id"), reverse=True)


def get_model_index(models_list: list[dict], current_model_id: str) -> int:
    """Finds the integer index of the saved model ID in the current options list."""
    ids = [m["id"] for m in models_list]
    try:
        return ids.index(current_model_id)
    except (ValueError, AttributeError):
        return 0