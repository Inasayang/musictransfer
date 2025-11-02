import hashlib
import logging
import os
import webbrowser
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeMusicConnector:
    """
    YouTube Music API connector, handles authentication and API calls via the official SDK
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
        self.api_key = api_key
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # YouTube API endpoints and scopes
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.scopes = ["https://www.googleapis.com/auth/youtube"]

        # Internal caches for Google API client
        self._youtube_service = None
        self._credentials: Optional[Credentials] = None

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
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }

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
        logging.info("Exchanging code for token with YouTube: redirect_uri=%s", self.redirect_uri)
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        response = requests.post(self.token_url, data=data)
        logging.info("Token exchange response status: %s", response.status_code)
        logging.info("Token exchange response headers: %s", response.headers)
        logging.info("Token exchange response text: %s", response.text)
        response.raise_for_status()

        token_info = response.json()
        logging.info("YouTube token exchange response: %s", token_info)
        self._update_tokens(token_info)
        logging.info("YouTube access_token: %s", self.access_token)
        logging.info("YouTube refresh_token: %s", self.refresh_token)

        if not self.refresh_token:
            logging.warning("No refresh_token in token exchange response. This may cause issues later.")
            logging.warning("Response keys: %s", list(token_info.keys()))
            logging.warning(
                "If this continues to happen, check the OAuth client configuration and ensure consent is granted."
            )

        return token_info

    def is_authenticated(self) -> bool:
        """
        Check if the connector is properly authenticated with access token

        Returns:
            bool: True if properly authenticated, False otherwise
        """
        logging.info("Checking YouTube connector authentication status")
        logging.info("Access token: %s", self.access_token)
        logging.info("Refresh token: %s", self.refresh_token)
        logging.info("Token expiry: %s", self.token_expiry)
        return bool(self.access_token)

    def refresh_access_token(self) -> Dict:
        """
        Get new access token using refresh token

        Returns:
            Dictionary containing new access token
        """
        logging.info("Attempting to refresh YouTube access token. Current refresh_token: %s", self.refresh_token)

        if not self.refresh_token:
            logging.error("No refresh token available for YouTube connector")
            raise ValueError("No refresh token available. Please re-authenticate with YouTube.")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        logging.info("Token refresh request URL: %s", self.token_url)
        logging.info("Token refresh request data: %s", data)

        response = requests.post(self.token_url, data=data)
        logging.info("Token refresh response status: %s", response.status_code)
        logging.info("Token refresh response headers: %s", response.headers)
        logging.info("Token refresh response text: %s", response.text)

        if not response.ok:
            logging.error("Failed to refresh access token. Status code: %s", response.status_code)
            logging.error("Response content: %s", response.text)

            if 400 <= response.status_code < 500:
                logging.error("Client error during token refresh. Refresh token may be invalid.")
                self.refresh_token = None
                raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube.")

            response.raise_for_status()

        token_info = response.json()
        self._update_tokens(token_info)
        logging.info("Successfully refreshed YouTube access token. New access_token: %s", self.access_token)
        return token_info

    def apply_token_info(self, token_info: Dict) -> None:
        """Apply persisted token information to the connector."""
        if not token_info:
            return

        token_data = dict(token_info)
        if "refresh_token" not in token_data and self.refresh_token:
            token_data["refresh_token"] = self.refresh_token
        self._update_tokens(token_data)

    def create_playlist(self, title: str) -> Dict:
        """
        Create a new playlist

        Args:
            title: Playlist title

        Returns:
            Dictionary containing playlist information
        """
        body = {
            "snippet": {
                "title": title,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",
            },
        }

        def _call(service):
            return service.playlists().insert(part="snippet,status", body=body)

        return self._execute_with_refresh(_call, "create_playlist")

    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> Dict:
        """
        Add video to playlist

        Args:
            playlist_id: Playlist ID
            video_id: Video ID

        Returns:
            Dictionary containing add result
        """
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }

        def _call(service):
            return service.playlistItems().insert(part="snippet", body=body)

        return self._execute_with_refresh(_call, "add_video_to_playlist")

    def get_playlists(self, max_results: int = 50) -> Dict:
        """
        Get user's playlists

        Args:
            max_results: Maximum number of results to return (0-50)

        Returns:
            Dictionary containing playlist information
        """
        def _call(service):
            return service.playlists().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=min(max_results, 50),
            )

        return self._execute_with_refresh(_call, "get_playlists")

    def search_video(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for videos

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List containing search results
        """
        params = {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max(1, min(max_results, 50)),
        }

        if self.api_key:
            params["key"] = self.api_key

        def _call(service):
            return service.search().list(**params)

        response = self._execute_with_refresh(_call, "search_video")
        return response.get("items", [])

    def _invalidate_service(self) -> None:
        """Invalidate cached Google API client instances."""
        self._youtube_service = None
        self._credentials = None

    def _build_credentials(self) -> Credentials:
        """Build OAuth credentials instance from stored tokens."""
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")

        credentials = Credentials(
            token=self.access_token,
            refresh_token=self.refresh_token,
            token_uri=self.token_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes,
        )

        if self.token_expiry:
            credentials.expiry = self.token_expiry

        return credentials

    def _get_credentials(self) -> Credentials:
        """Return cached credentials or build a new one."""
        if self._credentials is None:
            self._credentials = self._build_credentials()
        else:
            self._credentials.token = self.access_token
            self._credentials.refresh_token = self.refresh_token
            if self.token_expiry:
                self._credentials.expiry = self.token_expiry

        return self._credentials

    def _get_youtube_service(self, force_rebuild: bool = False):
        """Get an authenticated YouTube Data API service instance."""
        if force_rebuild:
            self._invalidate_service()

        if not self.access_token:
            logging.error("No access token available. Please authenticate first.")
            raise ValueError("No access token available. Please authenticate first.")

        credentials = self._get_credentials()

        # Refresh credentials automatically if expired
        if credentials and credentials.refresh_token:
            should_refresh = False
            if credentials.expiry:
                should_refresh = credentials.expiry <= datetime.now(timezone.utc)
            elif self.token_expiry:
                should_refresh = self.token_expiry <= datetime.now(timezone.utc)

            if should_refresh:
                logging.info("Stored YouTube credentials expired, refreshing automatically")
                try:
                    credentials.refresh(GoogleAuthRequest())
                    self.access_token = credentials.token
                    if credentials.expiry:
                        self.token_expiry = credentials.expiry
                except Exception as exc:  # pragma: no cover - safety net for SDK refresh errors
                    logging.error("Failed to refresh YouTube credentials automatically: %s", exc)
                    raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube.") from exc

        if self._youtube_service is None:
            self._youtube_service = build(
                "youtube",
                "v3",
                credentials=credentials,
                cache_discovery=False,
            )

        return self._youtube_service

    def _execute_with_refresh(self, call_factory, operation: str) -> Dict:
        """Execute a YouTube Data API request, retrying once on authentication failure."""
        logging.info("Executing YouTube API operation via SDK: %s", operation)
        try:
            service = self._get_youtube_service()
            return call_factory(service).execute()
        except HttpError as error:
            if error.resp.status == 401 and self.refresh_token:
                logging.info("YouTube API returned 401 during %s. Attempting token refresh.", operation)
                self.refresh_access_token()
                service = self._get_youtube_service(force_rebuild=True)
                return call_factory(service).execute()

            logging.error("YouTube API error during %s: %s", operation, error)
            if hasattr(error, "content"):
                logging.error("Error content: %s", error.content)
            raise

    def _update_tokens(self, token_info: Dict) -> None:
        """Update stored tokens and caches from token response."""
        if not token_info:
            return

        access_token = token_info.get("access_token")
        if access_token:
            self.access_token = access_token

        refresh_token = token_info.get("refresh_token")
        if refresh_token:
            self.refresh_token = refresh_token

        expires_at = token_info.get("expires_at")
        expires_in = token_info.get("expires_in")
        if expires_at:
            try:
                self.token_expiry = datetime.fromisoformat(expires_at)
            except ValueError:
                logging.warning("Invalid expires_at format received: %s", expires_at)
                self.token_expiry = None
        elif expires_in:
            try:
                expires_in_seconds = int(expires_in)
                expires_at_dt = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
                self.token_expiry = expires_at_dt
                token_info["expires_at"] = expires_at_dt.isoformat()
            except (TypeError, ValueError):
                logging.warning("Invalid expires_in value received: %s", expires_in)
                self.token_expiry = None
        else:
            self.token_expiry = None

        if self.refresh_token and "refresh_token" not in token_info:
            token_info["refresh_token"] = self.refresh_token

        self._invalidate_service()


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
