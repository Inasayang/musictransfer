import json
import logging
import os
import threading
import hashlib

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse
from pydantic import BaseModel

# Local application imports
from .connectors.spotify_connector import SpotifyConnector
from .connectors.youtube_connector import YouTubeMusicConnector
from .converters.data_converter import DataConverter
from .engine.migration_engine import MigrationEngine
from .utils.error_handling import setup_logging
from .config import Config

# Load configuration
Config.load_config()

# Validate configuration
is_valid, missing_keys = Config.validate()
if not is_valid:
    logging.warning("Missing configuration keys: %s", missing_keys)

# Setup logging
setup_logging("musictransfer.log", logging.INFO)

# Create FastAPI application
app = FastAPI(title="MusicTransfer", description="Spotify and YouTube Music Playlist Migration Tool")

# Setup templates and static files
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
static_dir = os.path.join(os.path.dirname(__file__), 'static')
templates = Jinja2Templates(directory=template_dir)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY or 'dev-key-change-in-production')

# Mount static files
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve built frontend files from the frontend/dist directory
frontend_dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
if os.path.exists(frontend_dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_dir, 'assets')), name="assets")

# Security
security = HTTPBearer(auto_error=False)

# Global variables
SPOTIFY_CONNECTOR = None
YOUTUBE_CONNECTOR = None
MIGRATION_ENGINE = None
migration_status = {
    'running': False,
    'progress': 0,
    'description': '',
    'result': None,
    'error': None
}

# Configuration parameters
SPOTIFY_CLIENT_ID = Config.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = Config.SPOTIFY_CLIENT_SECRET
YOUTUBE_CLIENT_ID = Config.YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET = Config.YOUTUBE_CLIENT_SECRET
YOUTUBE_API_KEY = Config.YOUTUBE_API_KEY
REDIRECT_URI = Config.REDIRECT_URI

# This route is now handled by the frontend function above
# @app.route('/')
# def index():
#     """
#     Home page
#     """
#     return render_template('index.html')

@app.get('/auth/spotify')
async def auth_spotify(request: Request):
    """
    Spotify authentication
    """
    global SPOTIFY_CONNECTOR
    
    try:
        SPOTIFY_CONNECTOR = SpotifyConnector(
            SPOTIFY_CLIENT_ID,
            SPOTIFY_CLIENT_SECRET,
            REDIRECT_URI
        )
        
        # Generate authorization URL
        state = hashlib.sha256(os.urandom(1024)).hexdigest()
        auth_url = SPOTIFY_CONNECTOR.get_authorization_url(state)
        
        # Set authentication in progress flag in session
        request.session['auth_in_progress'] = 'spotify'
        
        # Redirect to Spotify authorization page
        return RedirectResponse(auth_url)
        
    except Exception as e:
        logging.error("Spotify authentication initialization failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/auth/youtube')
async def auth_youtube(request: Request):
    """
    YouTube authentication
    """
    global YOUTUBE_CONNECTOR
    
    try:
        YOUTUBE_CONNECTOR = YouTubeMusicConnector(
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            REDIRECT_URI,
            YOUTUBE_API_KEY
        )
        
        # Generate authorization URL
        state = hashlib.sha256(os.urandom(1024)).hexdigest()
        auth_url = YOUTUBE_CONNECTOR.get_authorization_url(state)
        
        # Set authentication in progress flag in session
        request.session['auth_in_progress'] = 'youtube'
        
        # Redirect to YouTube authorization page
        return RedirectResponse(auth_url)
        
    except Exception as e:
        logging.error("YouTube authentication initialization failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/callback')
async def callback(request: Request, code: str = None, state: str = None):
    """
    OAuth callback handling
    """
    global SPOTIFY_CONNECTOR, YOUTUBE_CONNECTOR
    
    
    # Determine the platform from the request URL
    referer = request.headers.get('referer', '')
    request_url = str(request.url)
    
    logging.info("Callback processing: code=%s, state=%s", code, state)
    logging.info("Referer: %s", referer)
    logging.info("Request URL: %s", request_url)
    
    try:
        # Determine platform by checking URL and referer
        is_spotify = ('spotify' in request_url.lower() or 
                      'accounts.spotify.com' in referer.lower() or 
                      ('state' in request.query_params and 'spotify' in request.query_params.get('state', '')) or
                      request.session.get('auth_in_progress') == 'spotify')
        is_youtube = ('youtube' in request_url.lower() or 
                      'google' in referer.lower() or 
                      'youtube' in referer.lower() or
                      'googleapis.com' in referer.lower() or
                      request.session.get('auth_in_progress') == 'youtube')
        
        logging.info("Platform identification: Spotify=%s, YouTube=%s", is_spotify, is_youtube)
        
        # If still unable to determine platform, use session fallback
        if not is_spotify and not is_youtube:
            # Default fallback - if we can't identify, check which connector exists
            if SPOTIFY_CONNECTOR:
                is_spotify = True
                logging.info("Defaulting to Spotify based on connector existence")
            elif YOUTUBE_CONNECTOR:
                is_youtube = True
                logging.info("Defaulting to YouTube based on connector existence")
        
        
        if is_spotify and SPOTIFY_CONNECTOR and code:
            token_info = SPOTIFY_CONNECTOR.exchange_code_for_token(code)
            request.session['spotify_authenticated'] = True
            request.session['spotify_token_info'] = token_info
            request.session.pop('auth_in_progress', None)  # Clear authentication in progress flag
            logging.info("Spotify authentication successful")
            return templates.TemplateResponse('callback.html', {'request': request, 'platform': 'Spotify'})
        elif is_youtube and YOUTUBE_CONNECTOR and code:
            token_info = YOUTUBE_CONNECTOR.exchange_code_for_token(code)
            logging.info("YouTube token_info: %s", token_info)
            request.session['youtube_authenticated'] = True
            request.session['youtube_token_info'] = token_info
            request.session.pop('auth_in_progress', None)  # Clear authentication in progress flag
            request.session.pop('youtube_reauth_in_progress', None)  # Clear re-authentication flag
            logging.info("YouTube authentication successful")
            return templates.TemplateResponse('callback.html', {'request': request, 'platform': 'YouTube Music'})
        else:
            logging.warning("Unknown callback source or missing required parameters: is_spotify=%s, is_youtube=%s, code=%s", is_spotify, is_youtube, code)
            logging.warning("Spotify connector: %s", SPOTIFY_CONNECTOR is not None)
            logging.warning("Youtube connector: %s", YOUTUBE_CONNECTOR is not None)
            request.session.pop('auth_in_progress', None)  # Clear authentication in progress flag
            return RedirectResponse(url='/')
        
    except Exception as e:
        logging.error("Authentication callback processing failed: %s", str(e))
        request.session.pop('auth_in_progress', None)  # Clear authentication in progress flag
        # Provide specific guidance for YouTube refresh token issues
        if "No refresh token available" in str(e) or "YouTube authentication has expired" in str(e):
            return templates.TemplateResponse('error.html', {'request': request, 'error': "YouTube authentication failed. Please try re-authenticating with YouTube. If the problem persists, you may need to revoke access in your Google account settings and re-authorize the application."})
        return templates.TemplateResponse('error.html', {'request': request, 'error': str(e)})

def get_spotify_connector(request: Request):
    """Get or create Spotify connector from session"""
    global SPOTIFY_CONNECTOR
    
    # If there's already a connector and it's authenticated, return directly
    if SPOTIFY_CONNECTOR and hasattr(SPOTIFY_CONNECTOR, 'access_token') and SPOTIFY_CONNECTOR.access_token:
        return SPOTIFY_CONNECTOR
    
    # Get token information from session
    token_info = request.session.get('spotify_token_info')
    if token_info:
        # Create new connector
        SPOTIFY_CONNECTOR = SpotifyConnector(
            SPOTIFY_CLIENT_ID,
            SPOTIFY_CLIENT_SECRET,
            REDIRECT_URI
        )
        # Restore token
        if isinstance(token_info, dict):
            SPOTIFY_CONNECTOR.access_token = token_info.get('access_token')
            SPOTIFY_CONNECTOR.refresh_token = token_info.get('refresh_token')
        elif isinstance(token_info, str):
            # If it's a JSON string, parse it
            try:
                token_data = json.loads(token_info)
                SPOTIFY_CONNECTOR.access_token = token_data.get('access_token')
                SPOTIFY_CONNECTOR.refresh_token = token_data.get('refresh_token')
            except:
                pass
        return SPOTIFY_CONNECTOR
    
    return None

def get_youtube_connector(request: Request):
    """Get or create YouTube connector from session"""
    global YOUTUBE_CONNECTOR
    
    # If there's already a connector and it's authenticated, return directly
    if YOUTUBE_CONNECTOR and hasattr(YOUTUBE_CONNECTOR, 'access_token') and YOUTUBE_CONNECTOR.access_token:
        logging.info("Returning existing YouTube connector with access_token: %s, refresh_token: %s", 
                    YOUTUBE_CONNECTOR.access_token, YOUTUBE_CONNECTOR.refresh_token)
        # Check if connector is properly authenticated
        if not YOUTUBE_CONNECTOR.is_authenticated():
            logging.warning("Existing YouTube connector not properly authenticated, forcing re-authentication")
            request.session.pop('youtube_authenticated', None)
            request.session.pop('youtube_token_info', None)
            YOUTUBE_CONNECTOR = None
            return None
        return YOUTUBE_CONNECTOR
    
    # Get token information from session
    token_info = request.session.get('youtube_token_info')
    logging.info("Retrieved token_info from session: %s", token_info)
    
    if token_info:
        # Create new connector
        YOUTUBE_CONNECTOR = YouTubeMusicConnector(
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            REDIRECT_URI,
            YOUTUBE_API_KEY
        )
        # Restore token
        if isinstance(token_info, dict):
            YOUTUBE_CONNECTOR.access_token = token_info.get('access_token')
            YOUTUBE_CONNECTOR.refresh_token = token_info.get('refresh_token')
            logging.info("Restored tokens from dict. Access token: %s, Refresh token: %s", 
                        YOUTUBE_CONNECTOR.access_token, YOUTUBE_CONNECTOR.refresh_token)
            # Check if connector is properly authenticated
            if not YOUTUBE_CONNECTOR.is_authenticated():
                logging.warning("Restored YouTube connector not properly authenticated, forcing re-authentication")
                request.session.pop('youtube_authenticated', None)
                request.session.pop('youtube_token_info', None)
                YOUTUBE_CONNECTOR = None
                return None
        elif isinstance(token_info, str):
            # If it's a JSON string, parse it
            try:
                token_data = json.loads(token_info)
                YOUTUBE_CONNECTOR.access_token = token_data.get('access_token')
                YOUTUBE_CONNECTOR.refresh_token = token_data.get('refresh_token')
                logging.info("Restored tokens from JSON string. Access token: %s, Refresh token: %s", 
                            YOUTUBE_CONNECTOR.access_token, YOUTUBE_CONNECTOR.refresh_token)
                # Check if connector is properly authenticated
                if not YOUTUBE_CONNECTOR.is_authenticated():
                    logging.warning("Restored YouTube connector not properly authenticated, forcing re-authentication")
                    request.session.pop('youtube_authenticated', None)
                    request.session.pop('youtube_token_info', None)
                    YOUTUBE_CONNECTOR = None
                    return None
            except Exception as e:
                logging.error("Failed to parse token_info as JSON: %s", str(e))
                pass
        return YOUTUBE_CONNECTOR
    
    logging.warning("No YouTube token info found in session")
    return None

@app.get('/api/auth/youtube/force')
async def force_youtube_auth(request: Request):
    """
    Force re-authentication with YouTube by redirecting to auth endpoint
    Keep current authentication status until re-auth is successful
    """
    # Don't clear YouTube authentication from session here
    # Keep current authentication status until re-auth is successful
    logging.info("Forced YouTube re-authentication initiated - keeping current session")
    
    # Set a flag to indicate re-authentication is in progress
    request.session['youtube_reauth_in_progress'] = True
    
    # Redirect to YouTube auth endpoint
    return RedirectResponse(url='/auth/youtube')


@app.post('/api/auth/youtube/refresh')
async def refresh_youtube_auth(request: Request):
    """
    Attempt to refresh YouTube authentication using refresh token
    """
    global YOUTUBE_CONNECTOR
    
    logging.info("Attempting to refresh YouTube authentication")
    
    # Check if we have a YouTube connector
    if not YOUTUBE_CONNECTOR:
        YOUTUBE_CONNECTOR = get_youtube_connector(request)
    
    # If we still don't have a connector, return error
    if not YOUTUBE_CONNECTOR:
        logging.warning("No YouTube connector available for refresh")
        return JSONResponse(
            content={'success': False, 'error': 'No YouTube authentication found. Please re-authenticate.'},
            status_code=400
        )
    
    # Try to refresh the access token
    try:
        token_info = YOUTUBE_CONNECTOR.refresh_access_token()
        logging.info("Successfully refreshed YouTube access token")
        
        # Update session with new token info
        request.session['youtube_token_info'] = token_info
        request.session['youtube_authenticated'] = True
        
        return JSONResponse(
            content={'success': True, 'message': 'YouTube authentication refreshed successfully'}
        )
    except Exception as e:
        logging.error("Failed to refresh YouTube authentication: %s", str(e))
        # Clear session and connector if refresh failed
        request.session.pop('youtube_authenticated', None)
        request.session.pop('youtube_token_info', None)
        YOUTUBE_CONNECTOR = None
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=400
        )


@app.get('/api/playlists')
async def get_playlists(request: Request, platform: str):
    """
    Get playlists
    """
    
    logging.info("Get playlists request: platform=%s", platform)
    logging.info("Spotify authentication status: %s", request.session.get('spotify_authenticated', False))
    logging.info("YouTube authentication status: %s", request.session.get('youtube_authenticated', False))
    
    try:
        if platform == 'spotify' and request.session.get('spotify_authenticated'):
            # Get or create Spotify connector
            connector = get_spotify_connector(request)
            if not connector:
                logging.warning("Unable to create Spotify connector")
                raise HTTPException(status_code=401, detail='Spotify not properly authorized')
            
            # Check if there's an access token
            if not hasattr(connector, 'access_token') or not connector.access_token:
                logging.warning("Spotify connector missing access token")
                raise HTTPException(status_code=401, detail='Spotify not properly authorized')
                
            playlists_data = connector.get_current_user_playlists()
            playlists = []
            for item in playlists_data.get("items", []):
                playlists.append({
                    'id': item.get("id"),
                    'name': item.get("name"),
                    'track_count': item.get("tracks", {}).get("total", 0),
                    'description': item.get("description", "")
                })
            logging.info("Successfully retrieved %d Spotify playlists", len(playlists))
            return JSONResponse(content=playlists)
        elif platform == 'youtube' and request.session.get('youtube_authenticated'):
            # Get or create YouTube connector
            connector = get_youtube_connector(request)
            if not connector:
                logging.warning("Unable to create YouTube connector - missing refresh token")
                raise HTTPException(status_code=401, detail='YouTube authentication has expired. Please re-authenticate with YouTube.')
            
            # Check if there's an access token
            if not hasattr(connector, 'access_token') or not connector.access_token:
                logging.warning("YouTube connector missing access token")
                raise HTTPException(status_code=401, detail='YouTube not properly authorized')
                
            playlists_data = connector.get_playlists()
            playlists = []
            for item in playlists_data.get("items", []):
                playlists.append({
                    'id': item.get("id"),
                    'name': item.get("snippet", {}).get("title", ""),
                    'track_count': item.get("contentDetails", {}).get("itemCount", 0),
                    'description': item.get("snippet", {}).get("description", "")
                })
            logging.info("Successfully retrieved %d YouTube playlists", len(playlists))
            return JSONResponse(content=playlists)
        
        logging.warning("Unsupported platform or not authenticated: %s", platform)
        raise HTTPException(status_code=400, detail='Not authenticated or unsupported platform')
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error("Failed to get playlists: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

class MigrationRequest(BaseModel):
    playlist_id: str

@app.post('/api/migrate')
async def start_migration(request: Request, migration_req: MigrationRequest):
    """
    Start migration
    """
    global migration_status, MIGRATION_ENGINE
    
    if migration_status['running']:
        raise HTTPException(status_code=400, detail='Migration already in progress')
    
    playlist_id = migration_req.playlist_id
    
    if not playlist_id:
        raise HTTPException(status_code=400, detail='Missing playlist ID')
    
    # Check authentication status in session
    if not request.session.get('spotify_authenticated') or not request.session.get('youtube_authenticated'):
        raise HTTPException(status_code=400, detail='Please complete platform authentication first')
    
    # Get or create connectors
    spotify_conn = get_spotify_connector(request)
    youtube_conn = get_youtube_connector(request)
    
    if not spotify_conn:
        raise HTTPException(status_code=400, detail='Unable to initialize Spotify connector')
    
    if not youtube_conn:
        raise HTTPException(status_code=400, detail='YouTube authentication has expired. Please re-authenticate with YouTube.')
    
    # Reset migration status
    migration_status['running'] = True
    migration_status['progress'] = 0
    migration_status['description'] = 'Starting migration...'
    migration_status['result'] = None
    migration_status['error'] = None
    
    # Execute migration in background thread
    # Remove the copy_current_request_context decorator and pass connectors directly
    thread = threading.Thread(target=run_migration, args=(playlist_id, spotify_conn, youtube_conn))
    thread.daemon = True
    thread.start()
    
    return JSONResponse(content={'status': 'started'})

def run_migration(playlist_id, spotify_conn=None, youtube_conn=None):
    """
    Execute migration in background thread
    """
    global migration_status, MIGRATION_ENGINE
    
    logging.info("Starting run_migration with playlist_id: %s", playlist_id)
    logging.info("Initial spotify_conn: %s", spotify_conn)
    logging.info("Initial youtube_conn: %s", youtube_conn)
    
    try:
        # Connectors should always be passed as parameters in FastAPI
        # Session access in background threads is not reliable
        if spotify_conn is None:
            raise ValueError("Spotify connector not provided")
        if youtube_conn is None:
            raise ValueError("YouTube connector not provided")
            
        logging.info("Final spotify_conn: %s", spotify_conn)
        logging.info("Final youtube_conn: %s", youtube_conn)
        if youtube_conn:
            logging.info("YouTube connector access_token: %s", youtube_conn.access_token)
            logging.info("YouTube connector refresh_token: %s", youtube_conn.refresh_token)
        else:
            raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube.")
            
        # Create data converter and migration engine
        converter = DataConverter()
        MIGRATION_ENGINE = MigrationEngine(spotify_conn, youtube_conn, converter)
        
        # Execute migration
        youtube_playlist_id = MIGRATION_ENGINE.migrate_playlist(
            playlist_id,
            progress_callback=migration_progress_callback
        )
        
        migration_status['running'] = False
        migration_status['result'] = youtube_playlist_id
        migration_status['description'] = 'Migration completed!'
        
    except Exception as e:
        logging.error("Migration failed: %s", str(e))
        migration_status['running'] = False
        migration_status['error'] = str(e)
        # Provide a more user-friendly error message for YouTube authentication issues
        if "No refresh token available" in str(e) or "YouTube authentication has expired" in str(e):
            migration_status['description'] = 'Migration failed: YouTube authentication has expired. Please re-authenticate with YouTube and try again.'
        else:
            migration_status['description'] = f'Migration failed: {str(e)}'

def migration_progress_callback(current, total, description):
    """
    Migration progress callback
    """
    global migration_status
    migration_status['progress'] = (current / total) * 100
    migration_status['description'] = description

@app.get('/api/migration/status')
async def get_migration_status():
    """
    Get migration status
    """
    return JSONResponse(content=migration_status)

@app.get('/api/auth/status')
async def get_auth_status(request: Request):
    """
    Get authentication status
    During re-authentication, keep showing authenticated status until re-auth is complete
    """
    spotify_auth = request.session.get('spotify_authenticated', False)
    youtube_auth = request.session.get('youtube_authenticated', False)
    
    # During YouTube re-authentication, keep showing authenticated status
    # unless the re-authentication has explicitly failed
    youtube_reauth_in_progress = request.session.get('youtube_reauth_in_progress', False)
    
    logging.info("Authentication status check: Spotify=%s, YouTube=%s, YouTube Re-auth in progress=%s", 
                 spotify_auth, youtube_auth, youtube_reauth_in_progress)
    
    return JSONResponse(content={
        'spotify': spotify_auth,
        'youtube': youtube_auth  # Keep showing current status during re-auth
    })


@app.post('/api/auth/spotify/logout')
async def logout_spotify(request: Request):
    """
    Logout from Spotify - clear session and connector
    """
    global SPOTIFY_CONNECTOR
    
    # Clear Spotify authentication from session
    request.session.pop('spotify_authenticated', None)
    request.session.pop('spotify_token_info', None)
    
    # Clear global connector
    SPOTIFY_CONNECTOR = None
    
    logging.info("Spotify logout successful")
    
    return JSONResponse(content={'success': True, 'message': 'Logged out from Spotify successfully'})


@app.post('/api/auth/youtube/logout')
async def logout_youtube(request: Request):
    """
    Logout from YouTube - clear session and connector
    """
    global YOUTUBE_CONNECTOR
    
    # Clear YouTube authentication from session
    request.session.pop('youtube_authenticated', None)
    request.session.pop('youtube_token_info', None)
    request.session.pop('youtube_reauth_in_progress', None)
    
    # Clear global connector
    YOUTUBE_CONNECTOR = None
    
    logging.info("YouTube logout successful")
    
    return JSONResponse(content={'success': True, 'message': 'Logged out from YouTube successfully'})

# Frontend routes (must be defined after all API routes)
if os.path.exists(frontend_dist_dir):
    @app.get("/")
    @app.get("/{path:path}")
    async def frontend(path: str = ""):
        # Exclude API and auth routes from frontend routing
        if path.startswith('api/') or path.startswith('auth/') or path.startswith('callback'):
            raise HTTPException(status_code=404, detail="Not found")
        
        # If the path is a file that exists in the dist directory, serve it
        if path and os.path.exists(os.path.join(frontend_dist_dir, path)):
            return FileResponse(os.path.join(frontend_dist_dir, path))
        # Otherwise, serve index.html for client-side routing
        return FileResponse(os.path.join(frontend_dist_dir, 'index.html'))

if __name__ == '__main__':
    import uvicorn
    
    # Create necessary directories
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Start FastAPI application
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")