import os
import webbrowser

from musictransfer.app import app


def main():
    # Only open browser if this is not a reload (Flask debug mode can cause reloads)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Open application in default browser
        webbrowser.open("http://127.0.0.1:5000")

    # Start Flask application
    app.run(debug=True, port=5000)

if __name__ == "__main__":
    main()