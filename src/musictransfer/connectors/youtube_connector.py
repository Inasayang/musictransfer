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
            "access_type": "offline",  # Request offline access to get refresh token
            "prompt": "consent",  # Force to show consent screen to get refresh token
            "include_granted_scopes": "true"  # Include previously granted scopes
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
        import logging
        # Prepare request parameters
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        # Send request
        logging.info("Exchanging code for token with data: %s", data)
        response = requests.post(self.token_url, data=data)
        logging.info("Token exchange response status: %s", response.status_code)
        logging.info("Token exchange response headers: %s", response.headers)
        logging.info("Token exchange response text: %s", response.text)
        response.raise_for_status()
        
        token_info = response.json()
        logging.info("YouTube token exchange response: %s", token_info)
        self.access_token = token_info["access_token"]
        self.refresh_token = token_info.get("refresh_token")
        logging.info("YouTube access_token: %s", self.access_token)
        logging.info("YouTube refresh_token: %s", self.refresh_token)
        
        # Check if refresh_token is missing
        if not self.refresh_token:
            logging.warning("No refresh_token in token exchange response. This may cause issues later.")
            logging.warning("Response keys: %s", list(token_info.keys()))
            logging.warning("This could be because the user has already authorized the app. Try revoking access and re-authorizing.")
            # Log additional information that might help diagnose the issue
            logging.warning("If this continues to happen, check that:")
            logging.warning("1. The OAuth client is properly configured in Google Cloud Console")
            logging.warning("2. The redirect URI matches exactly what's registered in Google Cloud Console")
            logging.warning("3. The user is granting consent properly during authentication")
        
        return token_info
    
    def is_authenticated(self) -> bool:
        """
        Check if the connector is properly authenticated with both access and refresh tokens
        
        Returns:
            bool: True if properly authenticated, False otherwise
        """
        import logging
        logging.info("Checking YouTube connector authentication status")
        logging.info("Access token: %s", self.access_token)
        logging.info("Refresh token: %s", self.refresh_token)
        
        # Check if we have both access and refresh tokens
        has_access_token = bool(self.access_token)
        has_refresh_token = bool(self.refresh_token)
        
        logging.info("Has access token: %s", has_access_token)
        logging.info("Has refresh token: %s", has_refresh_token)
        
        return has_access_token and has_refresh_token
    
    def refresh_access_token(self) -> Dict:
        """
        Get new access token using refresh token
        
        Returns:
            Dictionary containing new access token
        """
        import logging
        logging.info("Attempting to refresh access token. Current refresh_token: %s", self.refresh_token)
        
        if not self.refresh_token:
            logging.error("No refresh token available for YouTube connector")
            raise ValueError("No refresh token available. Please re-authenticate with YouTube.")
            
        # Prepare request parameters
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        # Log request details for debugging
        logging.info("Token refresh request URL: %s", self.token_url)
        logging.info("Token refresh request data: %s", data)
        
        # Send request
        response = requests.post(self.token_url, data=data)
        logging.info("Token refresh response status: %s", response.status_code)
        logging.info("Token refresh response headers: %s", response.headers)
        logging.info("Token refresh response text: %s", response.text)
        
        # Check if the response is successful
        if not response.ok:
            logging.error("Failed to refresh access token. Status code: %s", response.status_code)
            logging.error("Response content: %s", response.text)
            
            # If it's a client error (4xx), the refresh token might be invalid
            if 400 <= response.status_code < 500:
                logging.error("Client error during token refresh. Refresh token may be invalid.")
                self.refresh_token = None  # Clear the invalid refresh token
                raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube.")
            
            response.raise_for_status()
        
        token_info = response.json()
        self.access_token = token_info["access_token"]
        
        # Note: refresh_token is typically not returned in refresh responses
        # but if it is, we should update it
        if "refresh_token" in token_info:
            self.refresh_token = token_info["refresh_token"]
            logging.info("Updated refresh token from refresh response")
        
        logging.info("Successfully refreshed access token. New access_token: %s", self.access_token)
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
        import logging
        logging.info("Making authenticated request to %s", url)
        logging.info("Current access_token: %s", self.access_token)
        logging.info("Current refresh_token: %s", self.refresh_token)
        
        if not self.access_token:
            logging.error("No access token available. Please authenticate first.")
            raise ValueError("No access token available. Please authenticate first.")
            
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        # Add content type header
        if 'json' in kwargs and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        # Log detailed request information
        logging.info("Request method: %s", method)
        logging.info("Request headers: %s", headers)
        logging.info("Request kwargs: %s", kwargs)
        
        response = requests.request(method, url, headers=headers, **kwargs)
        logging.info("Initial request response status: %s", response.status_code)
        logging.info("Initial request response headers: %s", response.headers)
        logging.info("Initial request response text (first 1000 chars): %s", response.text[:1000] if response.text else "")
        
        # If token expired, try to refresh
        if response.status_code == 401:
            logging.info("Token expired (401 response), attempting to refresh...")
            try:
                self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                logging.info("Retrying request with new access token")
                response = requests.request(method, url, headers=headers, **kwargs)
                logging.info("Retry request response status: %s", response.status_code)
                logging.info("Retry request response headers: %s", response.headers)
                logging.info("Retry request response text (first 1000 chars): %s", response.text[:1000] if response.text else "")
            except ValueError as e:
                if "No refresh token available" in str(e) or "YouTube authentication has expired" in str(e):
                    logging.error("Refresh token is missing or invalid. User needs to re-authenticate with YouTube.")
                    raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube.") from e
                else:
                    logging.error("Unexpected error during token refresh: %s", str(e))
                    raise
            
        # If there's an error, print detailed information
        if not response.ok:
            logging.error("YouTube API Error: %s - %s", response.status_code, response.text)
            logging.error("Request URL: %s", url)
            logging.error("Request method: %s", method)
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