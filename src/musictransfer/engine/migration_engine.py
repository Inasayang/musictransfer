import time
import logging
from typing import Optional, Callable
from musictransfer.models import Playlist
from musictransfer.connectors.spotify_connector import SpotifyConnector
from musictransfer.connectors.youtube_connector import YouTubeMusicConnector
from musictransfer.converters.data_converter import DataConverter
from musictransfer.utils.error_handling import retry_with_backoff, handle_api_errors, RateLimiter


class MigrationEngine:
    """
    Playlist migration engine, responsible for coordinating different components to complete migration tasks
    """
    
    def __init__(
        self,
        spotify_connector: SpotifyConnector,
        youtube_connector: YouTubeMusicConnector,
        converter: DataConverter,
    ):
        """
        Initialize migration engine
        
        Args:
            spotify_connector: Spotify connector instance
            youtube_connector: YouTube Music connector instance
            converter: Data converter instance
        """
        self.spotify_connector = spotify_connector
        self.youtube_connector = youtube_connector
        self.converter = converter
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Migration configuration
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        self.request_delay = 0.1  # seconds, avoid API rate limiting
        
        # Rate limiters
        self.spotify_limiter = RateLimiter(max_calls=10, time_window=1.0)
        self.youtube_limiter = RateLimiter(max_calls=5, time_window=1.0)
        
    def migrate_playlist(
        self, spotify_playlist_id: str, progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Migrate Spotify playlist to YouTube Music
        
        Args:
            spotify_playlist_id: Spotify playlist ID
            progress_callback: Progress callback function, receives (current_progress, total, description) parameters
            
        Returns:
            YouTube Music playlist ID
        """
        self.logger.info("Starting playlist migration %s", spotify_playlist_id)
        
        # 1. Get playlist data from Spotify
        if progress_callback:
            progress_callback(0, 4, "Getting Spotify playlist information...")
        
        spotify_playlist_data = self._get_spotify_playlist(spotify_playlist_id)
        
        # 2. Convert to common format
        if progress_callback:
            progress_callback(1, 4, "Converting playlist format...")
        
        common_playlist = self.converter.spotify_playlist_to_common(
            spotify_playlist_data
        )
        
        # 3. Create playlist on YouTube Music
        if progress_callback:
            progress_callback(2, 4, "Creating playlist on YouTube Music...")
        
        youtube_playlist_id = self._create_youtube_playlist(common_playlist)
        
        # 4. Migrate tracks
        if progress_callback:
            progress_callback(3, 4, f"Migrating {len(common_playlist.tracks)} tracks...")
        
        self._migrate_tracks(common_playlist, youtube_playlist_id, progress_callback)
        
        # Complete
        if progress_callback:
            progress_callback(4, 4, "Migration completed!")
        
        self.logger.info(
            "Playlist migration completed, YouTube Music playlist ID: %s", youtube_playlist_id
        )
        return youtube_playlist_id
        
    @handle_api_errors
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def _get_spotify_playlist(self, playlist_id: str) -> dict:
        """
        Get playlist data from Spotify
        
        Args:
            playlist_id: Playlist ID
            
        Returns:
            Spotify playlist data
        """
        try:
            # Apply rate limiting
            self.spotify_limiter.acquire()
            
            # Get basic playlist information
            playlist_data = self.spotify_connector.get_current_user_playlists()
            
            # Find target playlist
            target_playlist = None
            for playlist in playlist_data.get("items", []):
                if playlist.get("id") == playlist_id:
                    target_playlist = playlist
                    break
            
            if not target_playlist:
                raise ValueError(f"Playlist with ID {playlist_id} not found")
            
            # Get all tracks in the playlist
            tracks = []
            offset = 0
            limit = 100
            
            while True:
                # Apply rate limiting
                self.spotify_limiter.acquire()
                
                tracks_data = self.spotify_connector.get_playlist_tracks(
                    playlist_id, limit=limit, offset=offset
                )
                
                tracks.extend(tracks_data.get("items", []))
                
                # Check if there are more tracks
                if len(tracks_data.get("items", [])) < limit:
                    break
                
                offset += limit
                time.sleep(self.request_delay)  # Avoid API rate limiting
                
            # Add track data to playlist data
            target_playlist["tracks"] = {"items": tracks}
            
            return target_playlist
            
        except Exception as e:
            self.logger.error("Failed to get Spotify playlist: %s", str(e))
            raise
            
    @handle_api_errors
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def _create_youtube_playlist(self, common_playlist: Playlist) -> str:
        """
        Create playlist on YouTube Music
        
        Args:
            common_playlist: Common playlist object
            
        Returns:
            YouTube Music playlist ID
        """
        try:
            # Apply rate limiting
            self.youtube_limiter.acquire()
            
            # Convert to YouTube Music compatible format
            title = self.converter.common_playlist_to_youtube_title(common_playlist)
            
            # Create playlist
            self.logger.info("Attempting to create YouTube Music playlist with title: %s", title)
            playlist_data = self.youtube_connector.create_playlist(title)
            self.logger.info("YouTube Music playlist creation response: %s", playlist_data)
            
            youtube_playlist_id = playlist_data.get("id")
            if not youtube_playlist_id:
                raise ValueError("Failed to create YouTube Music playlist")
            
            self.logger.info("Successfully created YouTube Music playlist: %s", youtube_playlist_id)
            return youtube_playlist_id
            
        except Exception as e:
            self.logger.error("Failed to create YouTube Music playlist: %s", str(e))
            self.logger.error("Exception type: %s", type(e).__name__)
            # Provide a more specific error message for authentication issues
            if "No refresh token available" in str(e) or "YouTube authentication has expired" in str(e):
                raise ValueError("YouTube authentication has expired. Please re-authenticate with YouTube and try again.") from e
            raise
            
    def _migrate_tracks(
        self,
        common_playlist: Playlist,
        youtube_playlist_id: str,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """
        Migrate tracks to YouTube Music playlist
        
        Args:
            common_playlist: Common playlist object
            youtube_playlist_id: YouTube Music playlist ID
            progress_callback: Progress callback function
        """
        total_tracks = len(common_playlist.tracks)
        migrated_tracks = 0
        failed_tracks = 0
        
        self.logger.info("Starting migration of %d tracks", total_tracks)
        
        for i, track in enumerate(common_playlist.tracks):
            try:
                # Generate search query
                search_query = self.converter.create_youtube_search_query(track)
                self.logger.info("Searching for track: %s with query: %s", track, search_query)
                
                # Apply rate limiting
                self.youtube_limiter.acquire()
                
                # Search for corresponding YouTube video
                search_results = self.youtube_connector.search_video(
                    search_query, max_results=1
                )
                self.logger.info("Search results for %s: %s", track, search_results)
                
                if not search_results:
                    self.logger.warning("No matching video found: %s", track)
                    failed_tracks += 1
                    continue
                
                # Get video ID from first search result
                video_id = search_results[0].get("id", {}).get("videoId")
                if not video_id:
                    self.logger.warning("Video ID not found in search results: %s", track)
                    failed_tracks += 1
                    continue
                
                self.logger.info("Adding video %s to playlist for track: %s", video_id, track)
                
                # Add video to playlist
                self._add_video_to_playlist_with_retry(youtube_playlist_id, video_id)
                
                migrated_tracks += 1
                self.logger.info("Successfully migrated track: %s", track)
                
            except (ValueError, KeyError) as e:
                self.logger.error("Failed to migrate track %s: %s", track, str(e))
                failed_tracks += 1
            except RuntimeError as e:
                self.logger.error("Failed to migrate track %s: Runtime error: %s", track, str(e))
                failed_tracks += 1
            except Exception as e:
                self.logger.error("Failed to migrate track %s: Unknown error: %s", track, str(e))
                self.logger.error("Exception type: %s", type(e).__name__)
                failed_tracks += 1
            
            # Update progress
            if progress_callback:
                progress = 3 + (i + 1) / total_tracks
                progress_callback(
                    progress,
                    4,
                    f"Migrating tracks... ({migrated_tracks}/{total_tracks} successful, {failed_tracks} failed)",
                )
            
            # Delay to avoid API rate limiting
            time.sleep(self.request_delay)
            
        self.logger.info(
            "Track migration completed. Successful: %d, Failed: %d, Total: %d", migrated_tracks, failed_tracks, total_tracks
        )
        
    @handle_api_errors
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def _add_video_to_playlist_with_retry(
        self, playlist_id: str, video_id: str
    ) -> None:
        """
        Add video to playlist with retry mechanism
        
        Args:
            playlist_id: Playlist ID
            video_id: Video ID
        """
        # Apply rate limiting
        self.youtube_limiter.acquire()
        
        try:
            self.youtube_connector.add_video_to_playlist(playlist_id, video_id)
        except Exception as e:
            self.logger.warning("Failed to add video to playlist: %s", str(e))
            raise