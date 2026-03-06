import streamlit as st
from streamlit_local_storage import LocalStorage

def get_local_storage():
    if "storage_bridge" not in st.session_state:
        st.session_state.storage_bridge = LocalStorage()
    return st.session_state.storage_bridge

def get_browser_key(key_type: str, storage: LocalStorage, setting_type: str):
    """
    Fetches a specific key from browser storage and 
    hydrates the Pydantic session state object.
    """
    settings = getattr(st.session_state.pipeline_settings, setting_type)
    browser_key = f"{setting_type}_{key_type}"
    stored_val = storage.getItem(browser_key)
    if stored_val != None:
        setattr(settings, key_type, stored_val)
        return stored_val
    return getattr(settings, key_type, None)

def set_new_key(key_name: str, new_key: str, storage: LocalStorage, setting_type: str):
    """
    Compares new key against the nested session state.
    Updates both Browser and RAM state if changed.
    """
    settings = getattr(st.session_state.pipeline_settings, setting_type, {})
    current_val = getattr(settings, key_name, None)

    if new_key != current_val and new_key != None:
        browser_key = f"{setting_type}_{key_name}"
        setattr(settings, key_name, new_key) 
        storage.setItem(browser_key, new_key, key=f"set_browser_{browser_key}")      
        
        return True  
    return False

def save_provider_config(provider: str, model_map: dict, storage: LocalStorage):
    """
    model_map: {"reader": "gpt-4o", "writer": "gpt-4o-mini"}
    """
    prefix = provider.lower()
    for agent_role, model_id in model_map.items():
        storage_key = f"{prefix}_{agent_role}"
        storage.setItem(storage_key, model_id, key=f"set_{storage_key}")
        setattr(st.session_state.pipeline_settings.api_settings, storage_key, model_id)
