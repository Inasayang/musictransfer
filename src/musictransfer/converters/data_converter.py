import re
from datetime import datetime
from typing import Dict, List

from musictransfer.models import Playlist, Track


class DataConverter:
    """
    Converter for data between Spotify and YouTube Music formats
    """
    
    @staticmethod
    def spotify_playlist_to_common(spotify_playlist_data: Dict) -> Playlist:
        """
        Convert Spotify playlist data to common Playlist object
        
        Args:
            spotify_playlist_data: Playlist data returned by Spotify API
            
        Returns:
            Common Playlist object
        """
        # Extract basic playlist information
        playlist_id = spotify_playlist_data.get("id", "")
        name = spotify_playlist_data.get("name", "")
        description = spotify_playlist_data.get("description", "")
        
        # Process timestamps
        created_at = None
        updated_at = None
        
        if "tracks" in spotify_playlist_data:
            tracks_data = spotify_playlist_data["tracks"]
            tracks = DataConverter._spotify_tracks_to_common(tracks_data)
        else:
            tracks = []
        
        # Create platform-specific data dictionary
        platform_specific_data = {
            "spotify": {
                "href": spotify_playlist_data.get("href", ""),
                "uri": spotify_playlist_data.get("uri", ""),
                "owner": spotify_playlist_data.get("owner", {})
            }
        }
        
        return Playlist(
            id=playlist_id,
            name=name,
            description=description,
            tracks=tracks,
            created_at=created_at,
            updated_at=updated_at,
            platform_specific_data=platform_specific_data
        )
    
    @staticmethod
    def _spotify_tracks_to_common(tracks_data: Dict) -> List[Track]:
        """
        Convert Spotify track data to common Track object list
        
        Args:
            tracks_data: Track data returned by Spotify API
            
        Returns:
            List of common Track objects
        """
        tracks = []
        
        # Process paginated data
        items = tracks_data.get("items", [])
        
        for item in items:
            # Spotify track information is in the track field
            track_info = item.get("track", {}) if item.get("track") else item
            
            if not track_info or track_info.get("type") != "track":
                continue
                
            # Extract basic track information
            track_id = track_info.get("id", "")
            title = track_info.get("name", "")
            
            # Extract artist information
            artists = []
            for artist in track_info.get("artists", []):
                artists.append(artist.get("name", ""))
            
            # Extract album information
            album_info = track_info.get("album", {})
            album = album_info.get("name", "") if album_info else ""
            
            # Extract duration (milliseconds)
            duration_ms = track_info.get("duration_ms", 0)
            
            # Extract added time
            added_at = None
            if "added_at" in item and item["added_at"]:
                try:
                    added_at = datetime.fromisoformat(
                        item["added_at"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            
            # Create platform-specific data dictionary
            platform_specific_data = {
                "spotify": {
                    "href": track_info.get("href", ""),
                    "uri": track_info.get("uri", ""),
                    "popularity": track_info.get("popularity", 0)
                }
            }
            
            track = Track(
                id=track_id,
                title=title,
                artists=artists,
                album=album,
                duration_ms=duration_ms,
                added_at=added_at,
                platform_specific_data=platform_specific_data
            )
            
            tracks.append(track)
        
        return tracks
    
    @staticmethod
    def common_playlist_to_youtube_title(common_playlist: Playlist) -> str:
        """
        Convert common playlist to YouTube Music compatible title
        
        Args:
            common_playlist: Common Playlist object
            
        Returns:
            YouTube Music compatible title
        """
        # YouTube title is limited to 100 characters
        title = common_playlist.name[:100]
        
        # Remove special characters not supported by YouTube
        title = re.sub(r'[<>"|?*]', '', title)
        
        return title
    
    @staticmethod
    def common_playlist_to_youtube_description(common_playlist: Playlist) -> str:
        """
        Convert common playlist to YouTube Music compatible description
        
        Args:
            common_playlist: Common Playlist object
            
        Returns:
            YouTube Music compatible description
        """
        description = common_playlist.description or ""
        
        # YouTube description is limited to 5000 characters
        description = description[:5000]
        
        # Add migration information
        if description:
            description += "\n\n"
        description += f"Migrated from Spotify playlist '{common_playlist.name}'"
        
        return description
    
    @staticmethod
    def create_youtube_search_query(common_track: Track) -> str:
        """
        Create YouTube search query for common track
        
        Args:
            common_track: Common Track object
            
        Returns:
            YouTube search query string
        """
        # Combine artists and title as search query
        artists_str = ", ".join(common_track.artists)
        query = f"{common_track.title} {artists_str}"
        
        # Remove special characters that may interfere with search
        query = re.sub(r'[^\w\s\-\'\.]', ' ', query)
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query

# Usage example
if __name__ == "__main__":
    # Sample Spotify playlist data
    sample_spotify_data = {
        "id": "sample_playlist_id",
        "name": "Sample Playlist",
        "description": "A sample playlist for testing",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "track1",
                        "name": "Sample Song",
                        "artists": [
                            {"name": "Sample Artist"}
                        ],
                        "album": {
                            "name": "Sample Album"
                        },
                        "duration_ms": 200000,
                        "href": "https://api.spotify.com/v1/tracks/track1",
                        "uri": "spotify:track:track1"
                    },
                    "added_at": "2023-01-01T00:00:00Z"
                }
            ]
        }
    }
    
    # Conversion example
    converter = DataConverter()
    common_playlist = converter.spotify_playlist_to_common(sample_spotify_data)
    
    print(f"Converted playlist: {common_playlist}")
    if common_playlist.tracks:
        print(f"First track: {common_playlist.tracks[0]}")