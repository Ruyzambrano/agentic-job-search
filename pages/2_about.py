import streamlit as st

def about_page():
    st.title("📖 About the Pipeline")
    st.markdown("""
    **AI Career Matcher** is a high-tenacity, state-driven research agent designed to automate the heavy lifting of job discovery and seniority auditing. 

    By utilizing a **Directed Acyclic Graph (DAG)** architecture, the system coordinates specialized nodes to ensure every job lead is verified, deduplicated, and audited against your specific professional "track."
    """)

    st.divider()

    st.header("🛠️ Infrastructure & Setup")
    st.info("""
    **Bring Your Own Key:** This system is entirely client-side. Your CV data and search quotas remain private and dedicated to your research.
    """)

    col_llm, col_pine = st.columns(2)

    with col_llm:
        with st.container(border=True, height="stretch"):
            st.subheader("🧠 LLM & Analysis")
            st.markdown("""
            You can use **Gemini, Claude, or OpenAI**.
            
            **Recommended:** Use **Gemini** via [Google AI Studio](https://aistudio.google.com/) for a generous **Free Tier** (up to 15 RPM).
            
            *Pro-tip: Use different models for each node (e.g., Flash for search, Pro for auditing) to avoid rate limits.*
            """)
            st.caption("Setup: Get key at [aistudio.google.com](aistudio.google.com)")

    with col_pine:
        with st.container(border=True, height="stretch"):
            st.subheader("💾 Managed Storage")
            st.markdown("""
            **Secure Vector Vault**
            
            Unlike the LLM and Scraper keys, the storage layer is **fully managed** by the pipeline. 
            
            - **Deduplication:** Uses a global index to prevent redundant AI analysis.
            - **Privacy:** Your specific match scores are isolated to your session.
            - **Maintenance:** Index scaling and optimization are handled automatically.
            """)
            st.caption("Status: Managed Infrastructure (No key required)")

    col_search, col_specialist = st.columns(2)

    with col_search:
        with st.container(border=True, height="stretch"):
            st.subheader("🔍 Global Search")
            st.markdown("""
            **SerpAPI and RapidAPI**
            - [SerpAPI](https://serpapi.com/): 100 free searches/mo.
            - [RapidAPI](https://rapidapi.com/): Requires subscription to the [LinkedIn Job Search API](https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/linkedin-job-search-api).
            """)
            st.caption("Usage: Toggle these in the Settings tab.")

    with col_specialist:
        with st.container(border=True, height="stretch"):
            st.subheader("🇬🇧 UK Specialist")
            st.markdown("""
            **Reed.co.uk**
            Direct access to the UK's largest professional job board. 
            
            **Setup:** Request a free API key at the [Reed Developer Portal](https://www.reed.co.uk/developers/). Provides 1000+ searches each month.
            """)
            st.caption("Best for: Exacting London/UK matches.")
    

    col_agg, col_direct = st.columns(2)

    with col_agg:
        with st.container(border=True, height=400):
            st.subheader("🌐 Market Aggregator")
            st.markdown("""
            **TheirStack API**
            The "Master Key" for the global market. Aggregates listings from LinkedIn, Indeed, and 300k+ company career pages into a single structured feed.
            
            **Setup:**
            1. Create an account at [TheirStack.com](https://theirstack.com/).
            2. Generate an API Key in your **Dashboard**.
            3. Provides structured salary and remote-work data natively.
            """)
            st.caption("Usage: Best for high-volume, global tech-track discovery.")

    with col_direct:
        with st.container(border=True, height=400):
            st.subheader("🎯 Direct Scraping")
            st.markdown("""
            **HasData (Indeed Specialist)**
            Used to bypass 429 rate-limits on Indeed via high-tenacity proxy rotation and headless browsers.
            
            **Setup:**
            1. Register at [HasData.com](https://hasdata.com/apis/indeed-api).
            2. Copy your **API Key** from the profile settings.
            3. This node executes a two-step process: *Listing Scrape* followed by *Full Description Extraction*.
            """)
            st.caption("Usage: Best for \"Day 1\" Indeed postings and raw-text extraction.")
    st.divider()
    st.header("🚀 The 'Auditor' Philosophy")
    st.markdown("""
    Unlike standard "keyword matchers," this pipeline employs a **Seniority Auditor** logic. When the system analyzes a job, it performs a mathematical check on your career timeline:
    
    1. **Track Isolation:** Separates total work years from years in your specific "Tech Track."
    2. **Gap Identification:** Explicitly lists missing technologies or certifications (e.g., Quantexa, AWS, etc.).
    3. **Deduplication:** Hashes job URLs so you never pay to analyze the same job twice.
    """)

    st.caption("Version 1.2.0 | Agentic Career Research Pipeline")
    if st.button("Support this project",  type="primary"):
        st.switch_page("pages/9_support.py")

if __name__ == "__main__":
    about_page()