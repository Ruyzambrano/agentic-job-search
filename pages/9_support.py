import streamlit as st

def support_page():
    
    
    col1, col2 = st.columns([1, 2])
    
    with col2:
        st.title("☕ Support the Project")
        st.write("""
        Building and maintaining high-concurrency scrapers and agentic reasoning logic requires significant development time and cloud testing. 
        If this tool has helped you discover a 'hidden gem' role, consider fueling the project.
        """)
        st.divider()
        st.markdown("""
        ### Why Support?
        This pipeline is a labor of love designed to level the playing field for job seekers. While it is a **BYOK (Bring Your Own Key)** tool, there are underlying costs to keep the engine running:
        
        * **Managed Storage:** I cover the costs for the **Pinecone Vector Database** to ensure your jobs are deduplicated and globally cached.
        * **Infrastructure:** Server costs for hosting and maintaining the scraper resilience.
        * **Development:** Constant updates to the "Auditor" logic to beat changing job board structures.
        """)
        st.divider()
    
        st.subheader("Other Ways to Help")
        st.markdown("""
        - **Feedback:** Report bugs or suggest features on GitHub.
        - **Share:** If you land an interview using this tool, let me know! It's the best motivation.
        """)
    
    with col1:
        st.markdown(
            f"""
            <iframe id='kofiframe' 
                src='https://ko-fi.com/ruyzambrano/?hidefeed=true&widget=true&embed=true&preview=true' 
                style='border:none;width:100%;padding:4px;background:#f9f9f9;;' 
                height=650 
                title='ruyzambrano'></iframe>
            """,
            unsafe_allow_html=True
        )

    

if __name__ == "__main__":
    support_page()