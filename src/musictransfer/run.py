#!/usr/bin/env python3
"""
MusicTransfer Web Application Launcher
Launch MusicTransfer Web Application
"""

import os


def main():
    from musictransfer.app import app
    import webbrowser
    print("Launching MusicTransfer Web Application...")
    print("Application will run at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the application")
    # Only open browser if this is not a reload (Flask debug mode can cause reloads)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Open application in default browser
        webbrowser.open("http://127.0.0.1:5000")
    # Start Flask application
    app.run(debug=True, port=5000)

if __name__ == "__main__":
    main()