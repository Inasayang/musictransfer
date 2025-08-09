import json
import logging
import os
import threading
import webbrowser

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Local application imports
from connectors.spotify_connector import SpotifyConnector
from connectors.youtube_connector import YouTubeMusicConnector
from converters.data_converter import DataConverter
from engine.migration_engine import MigrationEngine
from utils.error_handling import setup_logging
from config import Config

# Load configuration
Config.load_config()

# Validate configuration
is_valid, missing_keys = Config.validate()
if not is_valid:
    logging.warning("Missing configuration keys: %s", missing_keys)

# Setup logging
setup_logging("musictransfer.log", logging.INFO)

# Create Flask application
app = Flask(__name__)

# Configure session
# app.config['SESSION_TYPE'] = 'filesystem'
# app.config['SESSION_FILE_DIR'] = './sessions'
app.config['SECRET_KEY'] = Config.SECRET_KEY or 'dev-key-change-in-production'

# Global variables
spotify_connector = None
youtube_connector = None
migration_engine = None
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

@app.route('/')
def index():
    """
    Home page
    """
    return render_template('index.html')

@app.route('/auth/spotify')
def auth_spotify():
    """
    Spotify authentication
    """
    global spotify_connector
    
    try:
        spotify_connector = SpotifyConnector(
            SPOTIFY_CLIENT_ID,
            SPOTIFY_CLIENT_SECRET,
            REDIRECT_URI
        )
        
        # Generate authorization URL
        import hashlib
        import os
        state = hashlib.sha256(os.urandom(1024)).hexdigest()
        auth_url = spotify_connector.get_authorization_url(state)
        
        # Set authentication in progress flag in session
        session['auth_in_progress'] = 'spotify'
        
        # Redirect to Spotify authorization page
        return redirect(auth_url)
        
    except Exception as e:
        logging.error("Spotify authentication initialization failed: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/auth/youtube')
def auth_youtube():
    """
    YouTube authentication
    """
    global youtube_connector
    
    try:
        youtube_connector = YouTubeMusicConnector(
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            REDIRECT_URI,
            YOUTUBE_API_KEY
        )
        
        # Generate authorization URL
        import hashlib
        import os
        state = hashlib.sha256(os.urandom(1024)).hexdigest()
        auth_url = youtube_connector.get_authorization_url(state)
        
        # Set authentication in progress flag in session
        session['auth_in_progress'] = 'youtube'
        
        # Redirect to YouTube authorization page
        return redirect(auth_url)
        
    except Exception as e:
        logging.error("YouTube authentication initialization failed: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/callback')
def callback():
    """
    OAuth callback handling
    """
    global spotify_connector, youtube_connector
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Determine the platform from the request URL
    referer = request.headers.get('Referer', '')
    request_url = request.url
    
    logging.info("Callback processing: code=%s, state=%s", code, state)
    logging.info("Referer: %s", referer)
    logging.info("Request URL: %s", request_url)
    
    try:
        # Determine platform by checking URL and referer
        is_spotify = 'spotify' in request_url.lower() or 'accounts.spotify.com' in referer.lower() or ('state' in request.args and 'spotify' in request.args.get('state', ''))
        is_youtube = 'youtube' in request_url.lower() or 'google' in referer.lower() or 'youtube' in referer.lower()
        
        logging.info("Platform identification: Spotify=%s, YouTube=%s", is_spotify, is_youtube)
        
        # If unable to determine platform from URL, try to get information from session
        if not is_spotify and not is_youtube:
            # Check if there's an ongoing authentication in session
            if session.get('auth_in_progress') == 'spotify':
                is_spotify = True
            elif session.get('auth_in_progress') == 'youtube':
                is_youtube = True
        
        if is_spotify and spotify_connector and code:
            token_info = spotify_connector.exchange_code_for_token(code)
            session['spotify_authenticated'] = True
            session['spotify_token_info'] = token_info
            session.pop('auth_in_progress', None)  # Clear authentication in progress flag
            logging.info("Spotify authentication successful")
            return render_template('callback.html', platform='Spotify')
        elif is_youtube and youtube_connector and code:
            token_info = youtube_connector.exchange_code_for_token(code)
            logging.info("YouTube token_info: %s", token_info)
            session['youtube_authenticated'] = True
            session['youtube_token_info'] = token_info
            session.pop('auth_in_progress', None)  # Clear authentication in progress flag
            logging.info("YouTube authentication successful")
            return render_template('callback.html', platform='YouTube Music')
        else:
            logging.warning("Unknown callback source or missing required parameters: is_spotify=%s, is_youtube=%s, code=%s", is_spotify, is_youtube, code)
            logging.warning("Spotify connector: %s", spotify_connector is not None)
            logging.warning("Youtube connector: %s", youtube_connector is not None)
            session.pop('auth_in_progress', None)  # Clear authentication in progress flag
            return redirect(url_for('index'))
        
    except Exception as e:
        logging.error("Authentication callback processing failed: %s", str(e))
        session.pop('auth_in_progress', None)  # Clear authentication in progress flag
        # Provide specific guidance for YouTube refresh token issues
        if "No refresh token available" in str(e) or "YouTube authentication has expired" in str(e):
            return render_template('error.html', error="YouTube authentication failed. Please try re-authenticating with YouTube. If the problem persists, you may need to revoke access in your Google account settings and re-authorize the application.")
        return render_template('error.html', error=str(e))

def get_spotify_connector():
    """Get or create Spotify connector from session"""
    global spotify_connector
    
    # If there's already a connector and it's authenticated, return directly
    if spotify_connector and hasattr(spotify_connector, 'access_token') and spotify_connector.access_token:
        return spotify_connector
    
    # Get token information from session
    token_info = session.get('spotify_token_info')
    if token_info:
        # Create new connector
        spotify_connector = SpotifyConnector(
            SPOTIFY_CLIENT_ID,
            SPOTIFY_CLIENT_SECRET,
            REDIRECT_URI
        )
        # Restore token
        if isinstance(token_info, dict):
            spotify_connector.access_token = token_info.get('access_token')
            spotify_connector.refresh_token = token_info.get('refresh_token')
        elif isinstance(token_info, str):
            # If it's a JSON string, parse it
            try:
                token_data = json.loads(token_info)
                spotify_connector.access_token = token_data.get('access_token')
                spotify_connector.refresh_token = token_data.get('refresh_token')
            except:
                pass
        return spotify_connector
    
    return None

def get_youtube_connector():
    """Get or create YouTube connector from session"""
    global youtube_connector
    
    # If there's already a connector and it's authenticated, return directly
    if youtube_connector and hasattr(youtube_connector, 'access_token') and youtube_connector.access_token:
        logging.info("Returning existing YouTube connector with access_token: %s, refresh_token: %s", 
                    youtube_connector.access_token, youtube_connector.refresh_token)
        # Check if connector is properly authenticated
        if not youtube_connector.is_authenticated():
            logging.warning("Existing YouTube connector not properly authenticated, forcing re-authentication")
            session.pop('youtube_authenticated', None)
            session.pop('youtube_token_info', None)
            youtube_connector = None
            return None
        return youtube_connector
    
    # Get token information from session
    token_info = session.get('youtube_token_info')
    logging.info("Retrieved token_info from session: %s", token_info)
    
    if token_info:
        # Create new connector
        youtube_connector = YouTubeMusicConnector(
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            REDIRECT_URI,
            YOUTUBE_API_KEY
        )
        # Restore token
        if isinstance(token_info, dict):
            youtube_connector.access_token = token_info.get('access_token')
            youtube_connector.refresh_token = token_info.get('refresh_token')
            logging.info("Restored tokens from dict. Access token: %s, Refresh token: %s", 
                        youtube_connector.access_token, youtube_connector.refresh_token)
            # Check if connector is properly authenticated
            if not youtube_connector.is_authenticated():
                logging.warning("Restored YouTube connector not properly authenticated, forcing re-authentication")
                session.pop('youtube_authenticated', None)
                session.pop('youtube_token_info', None)
                youtube_connector = None
                return None
        elif isinstance(token_info, str):
            # If it's a JSON string, parse it
            try:
                token_data = json.loads(token_info)
                youtube_connector.access_token = token_data.get('access_token')
                youtube_connector.refresh_token = token_data.get('refresh_token')
                logging.info("Restored tokens from JSON string. Access token: %s, Refresh token: %s", 
                            youtube_connector.access_token, youtube_connector.refresh_token)
                # Check if connector is properly authenticated
                if not youtube_connector.is_authenticated():
                    logging.warning("Restored YouTube connector not properly authenticated, forcing re-authentication")
                    session.pop('youtube_authenticated', None)
                    session.pop('youtube_token_info', None)
                    youtube_connector = None
                    return None
            except Exception as e:
                logging.error("Failed to parse token_info as JSON: %s", str(e))
                pass
        return youtube_connector
    
    logging.warning("No YouTube token info found in session")
    return None

@app.route('/api/auth/youtube/force')
def force_youtube_auth():
    """
    Force re-authentication with YouTube by clearing session and redirecting to auth endpoint
    """
    # Clear YouTube authentication from session
    session.pop('youtube_authenticated', None)
    session.pop('youtube_token_info', None)
    global youtube_connector
    youtube_connector = None
    
    logging.info("Forced YouTube re-authentication - cleared session and connector")
    
    # Redirect to YouTube auth endpoint
    return redirect(url_for('auth_youtube'))


@app.route('/api/auth/youtube/refresh', methods=['POST'])
def refresh_youtube_auth():
    """
    Attempt to refresh YouTube authentication using refresh token
    """
    global youtube_connector
    
    logging.info("Attempting to refresh YouTube authentication")
    
    # Check if we have a YouTube connector
    if not youtube_connector:
        youtube_connector = get_youtube_connector()
    
    # If we still don't have a connector, return error
    if not youtube_connector:
        logging.warning("No YouTube connector available for refresh")
        return jsonify({'success': False, 'error': 'No YouTube authentication found. Please re-authenticate.'}), 400
    
    # Try to refresh the access token
    try:
        token_info = youtube_connector.refresh_access_token()
        logging.info("Successfully refreshed YouTube access token")
        
        # Update session with new token info
        session['youtube_token_info'] = token_info
        session['youtube_authenticated'] = True
        
        return jsonify({'success': True, 'message': 'YouTube authentication refreshed successfully'})
    except Exception as e:
        logging.error("Failed to refresh YouTube authentication: %s", str(e))
        # Clear session and connector if refresh failed
        session.pop('youtube_authenticated', None)
        session.pop('youtube_token_info', None)
        youtube_connector = None
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/playlists')
def get_playlists():
    """
    Get playlists
    """
    platform = request.args.get('platform')
    
    logging.info("Get playlists request: platform=%s", platform)
    logging.info("Spotify authentication status: %s", session.get('spotify_authenticated', False))
    logging.info("YouTube authentication status: %s", session.get('youtube_authenticated', False))
    
    try:
        if platform == 'spotify' and session.get('spotify_authenticated'):
            # Get or create Spotify connector
            connector = get_spotify_connector()
            if not connector:
                logging.warning("Unable to create Spotify connector")
                return jsonify({'error': 'Spotify not properly authorized'}), 401
            
            # Check if there's an access token
            if not hasattr(connector, 'access_token') or not connector.access_token:
                logging.warning("Spotify connector missing access token")
                return jsonify({'error': 'Spotify not properly authorized'}), 401
                
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
            return jsonify(playlists)
        elif platform == 'youtube' and session.get('youtube_authenticated'):
            # Get or create YouTube connector
            connector = get_youtube_connector()
            if not connector:
                logging.warning("Unable to create YouTube connector - missing refresh token")
                return jsonify({'error': 'YouTube authentication has expired. Please re-authenticate with YouTube.'}), 401
            
            # Check if there's an access token
            if not hasattr(connector, 'access_token') or not connector.access_token:
                logging.warning("YouTube connector missing access token")
                return jsonify({'error': 'YouTube not properly authorized'}), 401
                
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
            return jsonify(playlists)
        
        logging.warning("Unsupported platform or not authenticated: %s", platform)
        return jsonify({'error': 'Not authenticated or unsupported platform'}), 400
        
    except Exception as e:
        logging.error("Failed to get playlists: %s", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/migrate', methods=['POST'])
def start_migration():
    """
    Start migration
    """
    global migration_status, migration_engine
    
    if migration_status['running']:
        return jsonify({'error': 'Migration already in progress'}), 400
    
    data = request.get_json()
    playlist_id = data.get('playlist_id')
    
    if not playlist_id:
        return jsonify({'error': 'Missing playlist ID'}), 400
    
    # Check authentication status in session
    if not session.get('spotify_authenticated') or not session.get('youtube_authenticated'):
        return jsonify({'error': 'Please complete platform authentication first'}), 400
    
    # Get or create connectors
    spotify_conn = get_spotify_connector()
    youtube_conn = get_youtube_connector()
    
    if not spotify_conn:
        return jsonify({'error': 'Unable to initialize Spotify connector'}), 400
    
    if not youtube_conn:
        return jsonify({'error': 'YouTube authentication has expired. Please re-authenticate with YouTube.'}), 400
    
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
    
    return jsonify({'status': 'started'})

def run_migration(playlist_id, spotify_conn=None, youtube_conn=None):
    """
    Execute migration in background thread
    """
    global migration_status, migration_engine
    
    logging.info("Starting run_migration with playlist_id: %s", playlist_id)
    logging.info("Initial spotify_conn: %s", spotify_conn)
    logging.info("Initial youtube_conn: %s", youtube_conn)
    
    try:
        # If connectors are not provided, try to restore from session
        if spotify_conn is None:
            logging.info("Getting Spotify connector from session")
            spotify_conn = get_spotify_connector()
        if youtube_conn is None:
            logging.info("Getting YouTube connector from session")
            youtube_conn = get_youtube_connector()
            
        logging.info("Final spotify_conn: %s", spotify_conn)
        logging.info("Final youtube_conn: %s", youtube_conn)
        if youtube_conn:
            logging.info("YouTube connector access_token: %s", youtube_conn.access_token)
            logging.info("YouTube connector refresh_token: %s", youtube_conn.refresh_token)
        else:
            raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube.")
            
        # Create data converter and migration engine
        converter = DataConverter()
        migration_engine = MigrationEngine(spotify_conn, youtube_conn, converter)
        
        # Execute migration
        youtube_playlist_id = migration_engine.migrate_playlist(
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

@app.route('/api/migration/status')
def get_migration_status():
    """
    Get migration status
    """
    return jsonify(migration_status)

@app.route('/api/auth/status')
def get_auth_status():
    """
    Get authentication status
    """
    spotify_auth = session.get('spotify_authenticated', False)
    youtube_auth = session.get('youtube_authenticated', False)
    
    logging.info("Authentication status check: Spotify=%s, YouTube=%s", spotify_auth, youtube_auth)
    
    return jsonify({
        'spotify': spotify_auth,
        'youtube': youtube_auth
    })

if __name__ == '__main__':
    # Create necessary directories
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Start Flask application
    app.run(debug=True, port=5000)