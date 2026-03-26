"""
Main Entry Point: Handles authentication, navigation, and global service initialization.
"""

import streamlit as st
from st_social_media_links import SocialMediaIcons

from src.ui.controllers import init_app
from src.ui.navigation import login_screen

def apply_refined_luxury_theme():
    st.markdown("""
        <style>
            /* 1. THE FOUNDATION: Deep Charcoal Obsidian */
            .stApp {
                background-color: #0C0E12 !important;
                color: #E2E8F0 !important;
            }

            /* 2. THE SIDEBAR: Matte Gunmetal */
            [data-testid="stSidebar"] {
                background-color: #12151A !important;
                border-right: 1px solid #1C2128 !important;
            }

            /* 3. DUSTY GOLD TYPOGRAPHY: Brushed Metallic Champagne */
            h1, h2, h3, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
                color: #C5A267 !important; 
                font-family: 'Playfair Display', 'Georgia', serif !important;
                font-weight: 400 !important;
                letter-spacing: 0.08em !important;
                border-bottom: 1px solid #1C2128;
                padding-bottom: 10px;
                /* Subtle metallic depth */
                text-shadow: 1px 1px 1px rgba(0,0,0,0.3);
            }

            /* 4. THE SELECTOR: Primary (Active) vs Secondary (List) */
            
            /* PRIMARY (Selected): Solid Dusty Gold Dust */
            button[data-testid="baseButton-primary"] {
                background-color: #C5A267 !important;
                color: #0C0E12 !important;
                border: 1px solid #C5A267 !important;
                border-radius: 2px !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 1px;
                box-shadow: 0 4px 15px rgba(197, 162, 103, 0.2) !important;
            }

            /* SECONDARY (Job Feed): Hollow Bronze */
            button[data-testid="baseButton-secondary"] {
                background-color: transparent !important;
                color: #C5A267 !important;
                border: 1px solid #2D3139 !important;
                border-radius: 2px !important;
                transition: 0.3s;
            }

            button[data-testid="baseButton-secondary"]:hover {
                border-color: #C5A267 !important;
                background-color: rgba(197, 162, 103, 0.08) !important;
            }

            /* 5. BRIEFING CARDS: Minimalist Slate with Gold Dust Accent */
            [data-testid="stVerticalBlock"] > div > div > div[style*="border"] {
                background-color: #12151A !important;
                border: 1px solid #1C2128 !important;
                border-top: 3px solid #C5A267 !important;
                border-radius: 4px !important;
            }

            /* 6. INPUTS: Matte Charcoal with Metallic Focus */
            .stTextInput>div>div>input {
                background-color: #0C0E12 !important;
                border: 1px solid #2D3139 !important;
                color: #C5A267 !important;
            }
            
            .stTextInput>div>div>input:focus {
                border-color: #C5A267 !important;
                box-shadow: 0 0 5px rgba(197, 162, 103, 0.3) !important;
            }
            
            /* Clean up the divider to be more subtle gold */
            hr {
                border: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, #4A4031, transparent) !important;
                opacity: 0.5;
            }
        </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(page_title="Agentic Job Auditor", page_icon="🤖", layout="wide")
    apply_refined_luxury_theme()
    if not st.user.is_logged_in:
        login_screen()
    else:
        init_app()
        pages = {
            "Jobs":
                [
                    st.Page(page="pages/1_home.py", title="Home", icon="🏠", default=True),
                    st.Page(page="pages/3_all_jobs.py", title="Your Matches", icon="🎯"),
                    st.Page(page="pages/4_job_view.py", title="Job Analysis", icon="🔬"),
                ],
            "Global": 
                [
                    st.Page(page="pages/5_global_jobs.py", title="Global Library", icon="🌐"),
                    st.Page(page="pages/6_market_views.py", title="Market Trends", icon="📊")
                ],
            "Settings": 
                [
                    st.Page(page="pages/2_about.py", title="About", icon="ℹ️"),
                    st.Page(page="pages/7_settings.py", title="Pipeline Settings", icon="⚙️"),
                    st.Page(page="pages/8_logout.py", title="Log out", icon="🚪")
                ],
            "Support the Project":
                [
                    st.Page(page="pages/9_support.py", title="Buy Me a Coffee", icon="☕️")
                ]
        }

        nav_bar = st.navigation(pages, position="top")

        if nav_bar:
            nav_bar.run()
    

    st.space("stretch")
    st.divider()
    social_media_icons = SocialMediaIcons(
        [
            "https://github.com/ruyzambrano",
            "https://linkedin.com/in/ruy-zambrano",
            "https://ko-fi.com/ruyzambrano"
        ],
        colors=["grey", None, None]
    )

    social_media_icons.render(sidebar=False)