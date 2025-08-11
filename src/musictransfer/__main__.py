import os
import webbrowser
import uvicorn

from .app import app

if __name__ == "__main__":
    # Only open browser if this is not a reload
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # Open application in default browser
        webbrowser.open("http://127.0.0.1:5000")

    # Start FastAPI application with uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
