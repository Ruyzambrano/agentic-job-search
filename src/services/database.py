"""Handles Supabase Integration and User Provisioning Core."""
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

class SupabaseStorage:
    def __init__(self):
        self.client: Client = self._get_client()

    @st.cache_resource
    def _get_client(_self) -> Client:
        url = st.secrets["SUPABASE_URL"]
        # Use the public anon key for safe client operations respecting RLS
        key = st.secrets["SUPABASE_ANON_KEY"] or st.secrets["SUPABASE_KEY"]
        return create_client(url, key)

    @st.cache_data
    def provision_user(_self, user_id: str, email: str) -> None:
        """
        SOP: Registers the identity inside the central unified user dimension table.
        The default trial tier configuration is automatically applied.
        """
        _self.client.table("profiles").upsert(
            {
                "id": user_id, 
                "email": email,
                "tier": "trial"
            }, 
            on_conflict="id"
        ).execute()

    def check_and_increment_search(self, user_id: str) -> dict:
        """Calls the Stored Procedure to verify if search is allowed."""
        response = self.client.rpc("check_and_increment_search", {"target_user_id": user_id}).execute()
        if response.data:
            return response.data[0]
        return {"allowed": False, "remaining_count": 0, "current_tier": "error"}
    
    @st.cache_data
    def get_user_status(_self, user_id: str, updated=False):
        """
        Passive check for UI/Sidebar. 
        Does NOT increment the search counter.
        """
        try:
            response = _self.client.rpc("get_user_status", {"target_user_id": user_id}).execute()
            if response.data:
                return response.data[0]
            return {"tier": "trial", "remaining_searches": 0, "has_cv": False}
        except Exception as e:
            print(f"◈ Status Error: {e}")
            return {"tier": "error", "remaining_searches": 0, "has_cv": False}

    def get_cv_metadata(self, user_id: str):
        """Fetches just the clean UI metadata (Skills/Summary) without the raw text."""
        res = self.client.table("cv_vault").select("parsed_metadata").eq("user_id", user_id).single().execute()
        return res.data.get("parsed_metadata") if res.data else None
    
    def refund_search_credit(self, user_id: str):
        """Decrements the search count if a search failed."""
        return self.client.rpc("refund_search", {"target_user_id": user_id}).execute()
    
    def save_cv(self, user_id, raw_text, parsed_json):
        """
        Commits the CV to the vault. Using upsert ensures 
        we respect the unique constraint on user_id.
        """
        payload = {
            "user_id": str(user_id), 
            "cv_content": raw_text,
            "parsed_metadata": parsed_json
        }
        return self.client.table("cv_vault").upsert(payload).execute()
    
    def delete_cv(self, user_id, cv_id):
        """
        Deletes a specific CV. State recalculations for 'has_active_cv' 
        are managed instantly by PostgreSQL database triggers.
        """
        try:
            self.client.table("cv_vault").delete().eq("id", cv_id).eq("user_id", str(user_id)).execute()
            
            # Simple check to return structural state context to the frontend handler
            remaining = self.client.table("cv_vault")\
                .select("id", count='exact')\
                .eq("user_id", str(user_id))\
                .execute()
            
            cv_count = remaining.count if remaining.count is not None else 0
                
            return {
                "success": True, 
                "has_remaining": cv_count > 0, 
                "count": cv_count
            }
            
        except Exception as e:
            return {"success": False, "message": str(e)}