import streamlit as st
from streamlit_local_storage import LocalStorage


def get_local_storage():
    """Initializes the browser storage bridge in the session state."""
    if "storage_bridge" not in st.session_state:
        st.session_state.storage_bridge = LocalStorage()
    return st.session_state.storage_bridge


def get_browser_key(key_type: str, storage: LocalStorage, setting_type: str):
    """
    Fetches a key from browser storage and hydrates the Pydantic session state.
    """
    settings_group = getattr(st.session_state.pipeline_settings, setting_type, None)
    if settings_group is None:
        return None

    browser_key = f"{setting_type}_{key_type}"
    stored_val = storage.getItem(browser_key)

    if stored_val is not None:
        if (
            isinstance(getattr(settings_group, key_type, None), int)
            and stored_val != ""
        ):
            try:
                stored_val = int(stored_val)
            except ValueError:
                pass

        setattr(settings_group, key_type, stored_val)
        return stored_val

    return getattr(settings_group, key_type, None)


def set_new_key(key_name: str, new_key: str, storage: LocalStorage, setting_type: str):
    """
    Updates Browser Storage and Python state only if the value has changed.
    """
    settings_group = getattr(st.session_state.pipeline_settings, setting_type, None)
    if settings_group is None:
        return False

    current_val = getattr(settings_group, key_name, None)

    if new_key is not None and str(new_key) != str(current_val):
        browser_key = f"{setting_type}_{key_name}"

        setattr(settings_group, key_name, new_key)

        storage.setItem(browser_key, new_key, key=f"set_browser_{browser_key}")
        return True
    return False


def save_provider_config(provider: str, model_map: dict, storage: LocalStorage) -> dict:
    """
    Saves model selections (e.g., 'gemini_reader') to browser and state.
    model_map: {"reader": "gemini-1.5-flash", "writer": "gemini-1.5-pro"}
    """
    prefix = provider.lower()
    api_settings = st.session_state.pipeline_settings.api_settings

    for agent_role, model_id in model_map.items():
        storage_key = f"{prefix}_{agent_role}"

        if hasattr(api_settings, storage_key):
            setattr(api_settings, storage_key, model_id)

        storage.setItem(storage_key, model_id, key=f"set_{storage_key}")
