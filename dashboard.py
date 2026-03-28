"""
Main Entry Point: Handles authentication, navigation, and global service initialization.
"""
import base64

import streamlit as st
from st_social_media_links import SocialMediaIcons

from src.ui.controllers import init_app
from src.ui.navigation import login_screen

def create_slate_logo():
    return  """<svg width="250" height="60" viewBox="0 0 250 60" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="8" height="40" rx="1.5" fill="#C5A267"/>
        <rect x="25" y="18" width="20" height="7" rx="1.5" fill="#C5A267" fill-opacity="1.0"/>
        <rect x="25" y="30" width="20" height="7" rx="1.5" fill="#C5A267" fill-opacity="0.7"/>
        <rect x="25" y="42" width="12" height="7" rx="1.5" fill="#C5A267" fill-opacity="0.4"/>
        <text x="60" y="42" fill="#C5A267" style="font: 400 28px 'Playfair Display', serif; letter-spacing: 0.1em;">THE SLATE</text>
    </svg>"""

def apply_slate_logo(logo: str):
    b64 = base64.b64encode(logo.encode()).decode()
    logo_url = f"data:image/svg+xml;base64,{b64}"
    st.logo(logo_url, icon_image=logo_url, size="large")

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
            .slate-support-btn {
                display: inline-block;
                padding: 8px 20px;
                border: 1px solid #C5A267 !important;
                border-radius: 2px !important;
                color: #C5A267 !important;
                font-family: 'Inter', sans-serif !important;
                font-size: 11px !important;
                font-weight: 600 !important;
                letter-spacing: 0.12em !important;
                text-transform: uppercase !important;
                text-decoration: none !important;
                background-color: transparent !important;
                transition: all 0.4s ease-in-out !important;
            }

            .slate-support-btn:hover {
                background-color: rgba(197, 162, 103, 0.15) !important;
                box-shadow: 0 0 15px rgba(197, 162, 103, 0.2) !important;
                border-color: #E2E8F0 !important; /* Slight shift to silver-gold on hover */
                color: #E2E8F0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

def main():
    slate_logo = create_slate_logo()
    st.set_page_config(
        page_title="THE SLATE",
        layout="wide"
    )
    apply_slate_logo(slate_logo)
    apply_refined_luxury_theme()
    if not st.user.is_logged_in:
        login_screen()
        return
    else:
        init_app()
        pages = {
            "Jobs":
                [
                    st.Page(page="pages/1_home.py", title="Home", default=True),
                    st.Page(page="pages/3_all_jobs.py", title="Your Matches"),
                    st.Page(page="pages/4_job_view.py", title="Job Analysis"),
                ],
            "Global": 
                [
                    st.Page(page="pages/5_global_jobs.py", title="Global Library"),
                    st.Page(page="pages/6_market_views.py", title="Market Trends")
                ],
            "Settings": 
                [
                    st.Page(page="pages/2_about.py", title="About",),
                    st.Page(page="pages/7_settings.py", title="Pipeline Settings"),
                    st.Page(page="pages/8_logout.py", title="Log out")
                ],
            "Support the Project":
                [
                    st.Page(page="pages/9_support.py", title="Buy Me a Coffee")
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
        colors=["#94A3B8","#78909C", "#C5A267"]
    )

    social_media_icons.render(sidebar=False)

if __name__ == "__main__":
    main()