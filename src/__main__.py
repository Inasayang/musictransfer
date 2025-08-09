import sys
import os
import webbrowser

# Add project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app

if __name__ == "__main__":
    # Only open browser if this is not a reload (Flask debug mode can cause reloads)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Open application in default browser
        webbrowser.open("http://127.0.0.1:5000")

    # Start Flask application
    app.run(debug=True, port=5000)