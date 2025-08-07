import requests
from typing import Dict, List, Optional
import webbrowser
import base64
import hashlib
import os

class YouTubeMusicConnector:
    """
    YouTube Music API connector, handles authentication and API calls
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, api_key: str = None):
        """
        Initialize YouTube Music connector
        
        Args:
            client_id: Application client ID
            client_secret: Application client secret
            redirect_uri: Redirect URI
            api_key: YouTube Data API key (optional)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.api_key = api_key  # Add API key support
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
        # YouTube API endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.api_base_url = "https://youtube.googleapis.com/youtube/v3"
        
    def get_authorization_url(self, state: str) -> str:
        """
        Get YouTube authorization URL
        
        Args:
            state: Random string to prevent CSRF attacks
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "https://www.googleapis.com/auth/youtube",
            "state": state,
            "access_type": "offline"
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
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        # Send request
        response = requests.post(self.token_url, data=data)
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
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        # Send request
        response = requests.post(self.token_url, data=data)
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
        
        # Add content type header
        if 'json' in kwargs and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        response = requests.request(method, url, headers=headers, **kwargs)
        
        # If token expired, try to refresh
        if response.status_code == 401:
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.request(method, url, headers=headers, **kwargs)
            
        # If there's an error, print detailed information
        if not response.ok:
            import logging
            logging.error("YouTube API Error: %s - %s", response.status_code, response.text)
            logging.error("Request URL: %s", url)
            logging.error("Request headers: %s", headers)
            logging.error("Request kwargs: %s", kwargs)
            
        response.raise_for_status()
        return response
    
    def create_playlist(self, title: str) -> Dict:
        """
        Create a new playlist
        
        Args:
            title: Playlist title
            
        Returns:
            Dictionary containing playlist information
        """
        url = f"{self.api_base_url}/playlists"
        params = {
            "part": "snippet,status",
            "key": self.api_key
        }
        
        # Build request body - strictly following YouTube API official HTTP request example
        body = {
            "snippet": {
                "title": title,
                # "description": description,
                # "tags": [
                #     "sample playlist",
                #     "API call"
                # ],
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": "private"
            }
        }
        
        # Set correct headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = self._make_authenticated_request("POST", url, params=params, json=body, headers=headers)
        return response.json()
    
    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> Dict:
        """
        Add video to playlist
        
        Args:
            playlist_id: Playlist ID
            video_id: Video ID
            
        Returns:
            Dictionary containing add result
        """
        url = f"{self.api_base_url}/playlistItems?part=snippet"
        
        # Build request body
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
        
        response = self._make_authenticated_request("POST", url, json=body)
        return response.json()
    
    def get_playlists(self, max_results: int = 50) -> Dict:
        """
        Get user's playlists
        
        Args:
            max_results: Maximum number of results to return (0-50)
            
        Returns:
            Dictionary containing playlist information
        """
        url = f"{self.api_base_url}/playlists"
        params = {
            "part": "snippet,contentDetails",
            "mine": "true",
            "maxResults": min(max_results, 50)
        }
        
        response = self._make_authenticated_request("GET", url, params=params)
        return response.json()
    
    def search_video(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for videos
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List containing search results
        """
        url = f"{self.api_base_url}/search"
        params = {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max_results
        }
        
        response = self._make_authenticated_request("GET", url, params=params)
        return response.json().get("items", [])

# Usage example
if __name__ == "__main__":
    # Configuration parameters (need to be replaced with actual values)
    CLIENT_ID = "your_youtube_client_id"
    CLIENT_SECRET = "your_youtube_client_secret"
    REDIRECT_URI = "http://localhost:8888/callback"
    
    # Create connector instance
    youtube = YouTubeMusicConnector(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    
    # Generate authorization URL and open browser
    state = hashlib.sha256(os.urandom(1024)).hexdigest()
    auth_url = youtube.get_authorization_url(state)
    print(f"Please visit this URL to authorize: {auth_url}")
    webbrowser.open(auth_url)