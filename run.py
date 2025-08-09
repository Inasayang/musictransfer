#!/usr/bin/env python3
"""
MusicTransfer Web Application Launcher
Launch MusicTransfer Web Application
"""

import sys
import os

# Add src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

if __name__ == "__main__":
    from app import app
    import webbrowser
    print("Launching MusicTransfer Web Application...")
    print("Application will run at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the application")
    # Open application in default browser
    webbrowser.open('http://127.0.0.1:5000')
    # Start Flask application
    app.run(debug=True, port=5000)