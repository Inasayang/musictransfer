import requests
from typing import Dict, List, Optional
import webbrowser
import base64
import hashlib
import os

class SpotifyConnector:
    """
    Spotify API connector, handles authentication and API calls
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
        # Spotify API endpoints
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.api_base_url = "https://api.spotify.com/v1"
        
    def get_authorization_url(self, state: str) -> str:
        """
        Get Spotify authorization URL
        
        Args:
            state: Random string to prevent CSRF attacks
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "playlist-read-private playlist-read-collaborative",
            "state": state
        }
        
        # Build authorization URL
        auth_url = f"{self.auth_url}?"
        auth_url += "&".join([f"{key}={value}" for key, value in params.items()])
        
        return auth_url
    
    def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code
            
        Returns:
            Dictionary containing access token and refresh token
        """
        # Prepare request parameters
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        # Send request
        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()
        
        token_info = response.json()
        self.access_token = token_info["access_token"]
        self.refresh_token = token_info.get("refresh_token")
        
        return token_info
    
    def refresh_access_token(self) -> Dict:
        """
        Get new access token using refresh token
        
        Returns:
            Dictionary containing new access token
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")
            
        # Prepare request parameters
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        # Send request
        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()
        
        token_info = response.json()
        self.access_token = token_info["access_token"]
        
        return token_info
    
    def _make_authenticated_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Send authenticated API request
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Other request parameters
            
        Returns:
            HTTP response
        """
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")
            
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        response = requests.request(method, url, headers=headers, **kwargs)
        
        # If token expired, try to refresh
        if response.status_code == 401:
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.request(method, url, headers=headers, **kwargs)
            
        response.raise_for_status()
        return response
    
    def get_current_user_playlists(self, limit: int = 50, offset: int = 0) -> Dict:
        """
        Get current user's playlists
        
        Args:
            limit: Number of playlists to return per page (1-50)
            offset: Offset
            
        Returns:
            Dictionary containing playlist information
        """
        url = f"{self.api_base_url}/me/playlists"
        params = {
            "limit": limit,
            "offset": offset
        }
        
        response = self._make_authenticated_request("GET", url, params=params)
        return response.json()
    
    def get_playlist_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get tracks in a playlist
        
        Args:
            playlist_id: Playlist ID
            limit: Number of tracks to return per page (1-100)
            offset: Offset
            
        Returns:
            Dictionary containing track information
        """
        url = f"{self.api_base_url}/playlists/{playlist_id}/tracks"
        params = {
            "limit": limit,
            "offset": offset
        }
        
        response = self._make_authenticated_request("GET", url, params=params)
        return response.json()

# Usage example
if __name__ == "__main__":
    # Configuration parameters (need to be replaced with actual values)
    CLIENT_ID = "your_spotify_client_id"
    CLIENT_SECRET = "your_spotify_client_secret"
    REDIRECT_URI = "http://localhost:8888/callback"
    
    # Create connector instance
    spotify = SpotifyConnector(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    
    # Generate authorization URL and open browser
    state = hashlib.sha256(os.urandom(1024)).hexdigest()
    auth_url = spotify.get_authorization_url(state)
    print(f"Please visit this URL to authorize: {auth_url}")
    webbrowser.open(auth_url)