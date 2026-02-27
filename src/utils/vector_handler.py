from os import environ as ENV

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model=ENV.get("EMBEDDING_MODEL"))

def get_global_jobs_store():
    """Collection for raw, deduplicated jobs across all users."""
    return Chroma(
        collection_name="global_raw_jobs",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db",
    )

def get_user_analysis_store():
    """Collection for personalized user-specific match analysis."""
    return Chroma(
        collection_name="user_job_analyses",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_db",
    )