from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Track:
    """
    Unified track data model
    """
    id: str
    title: str
    artists: List[str]
    album: str
    duration_ms: int
    added_at: Optional[datetime] = None
    platform_specific_data: Optional[dict] = None
    
    def __str__(self) -> str:
        """
        Return string representation of the track
        """
        artists_str = ", ".join(self.artists)
        return f"{self.title} by {artists_str}"

@dataclass
class Playlist:
    """
    Unified playlist data model
    """
    id: str
    name: str
    description: Optional[str]
    tracks: List[Track]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    platform_specific_data: Optional[dict] = None
    
    def __str__(self) -> str:
        """
        Return string representation of the playlist
        """
        return f"{self.name} ({len(self.tracks)} tracks)"
    
    def add_track(self, track: Track) -> None:
        """
        Add track to playlist
        """
        self.tracks.append(track)
        
    def remove_track(self, track_id: str) -> bool:
        """
        Remove track from playlist
        
        Args:
            track_id: Track ID
            
        Returns:
            Whether removal was successful
        """
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                del self.tracks[i]
                return True
        return False
    
    def get_track_count(self) -> int:
        """
        Get number of tracks in playlist
        """
        return len(self.tracks)