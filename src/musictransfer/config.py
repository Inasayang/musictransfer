import os

class Config:
    """Configuration class for the application"""
    
    # Spotify Configuration
    SPOTIFY_CLIENT_ID: str = ''
    SPOTIFY_CLIENT_SECRET: str = ''
    
    # YouTube Configuration
    YOUTUBE_CLIENT_ID: str = ''
    YOUTUBE_CLIENT_SECRET: str = ''
    YOUTUBE_API_KEY: str = ''
    
    # Application Configuration
    REDIRECT_URI: str = 'http://127.0.0.1:5000/callback'
    SECRET_KEY: str = ''
    
    @classmethod
    def load_config(cls) -> None:
        """
        Load configuration from various sources in order of priority:
        1. Environment variables
        2. .env file
        3. key.txt file
        4. Default values
        """
        # Load from environment variables first
        cls._load_from_env()
        
        # If still not set, try .env file
        if not cls._is_minimally_configured():
            cls._load_from_env_file()
        
        # If still not set, try key.txt file
        if not cls._is_minimally_configured():
            cls._load_from_key_file()
    
    @classmethod
    def _load_from_env(cls) -> None:
        """Load configuration from environment variables"""
        cls.SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', cls.SPOTIFY_CLIENT_ID)
        cls.SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', cls.SPOTIFY_CLIENT_SECRET)
        cls.YOUTUBE_CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID', cls.YOUTUBE_CLIENT_ID)
        cls.YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', cls.YOUTUBE_CLIENT_SECRET)
        cls.YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', cls.YOUTUBE_API_KEY)
        cls.REDIRECT_URI = os.environ.get('REDIRECT_URI', cls.REDIRECT_URI)
        cls.SECRET_KEY = os.environ.get('SECRET_KEY', cls.SECRET_KEY)
    
    @classmethod
    def _load_from_env_file(cls, env_file_path: str = '.env') -> None:
        """
        Load configuration from a .env file
        
        Args:
            env_file_path: Path to the .env file
        """
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        if hasattr(cls, key):
                            setattr(cls, key, value)
    
    @classmethod
    def _load_from_key_file(cls, key_file_path: str = 'key.txt') -> None:
        """
        Load configuration from key.txt file (original format)
        
        Args:
            key_file_path: Path to the key.txt file
        """
        if os.path.exists(key_file_path):
            with open(key_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line:
                        # Handle format: SPOTIFY_CLIENT_ID = "value"
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().strip('"\' ')
                            
                            if hasattr(cls, key):
                                setattr(cls, key, value)
    
    @classmethod
    def _is_minimally_configured(cls) -> bool:
        """Check if minimal required configuration is present"""
        return bool(cls.SPOTIFY_CLIENT_ID and cls.SPOTIFY_CLIENT_SECRET and 
                   cls.YOUTUBE_CLIENT_ID and cls.YOUTUBE_CLIENT_SECRET and cls.YOUTUBE_API_KEY)
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate that all required configuration values are set
        
        Returns:
            Tuple of (is_valid, list_of_missing_keys)
        """
        required_keys = [
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET',
            'YOUTUBE_CLIENT_ID',
            'YOUTUBE_CLIENT_SECRET',
            'YOUTUBE_API_KEY'
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key, ''):
                missing_keys.append(key)
                
        return len(missing_keys) == 0, missing_keys