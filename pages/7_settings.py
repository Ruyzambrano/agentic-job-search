from src.ui.components import render_settings_page, add_sidebar_support
from src.ui.controllers import init_app, show_success_toast

if __name__ == "__main__":
    add_sidebar_support()
    init_app()
    show_success_toast()
    render_settings_page() 
    

