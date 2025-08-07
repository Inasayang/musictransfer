import sys
import os

# Add project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app

if __name__ == "__main__":
    # Open application in default browser
    import webbrowser
    webbrowser.open('http://127.0.0.1:5000')
    
    # Start Flask application
    app.run(debug=True, port=5000)