#!/usr/bin/env python3
"""
MusicTransfer Web Application Launcher
Launch MusicTransfer Web Application
"""

import os


def main():
    from .app import app
    import webbrowser
    import uvicorn
    
    print("Launching MusicTransfer Web Application...")
    print("Application will run at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the application")
    
    # Only open browser if this is not a reload
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Open application in default browser
        webbrowser.open("http://127.0.0.1:5000")
    
    # Start FastAPI application with uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")

if __name__ == "__main__":
    main()