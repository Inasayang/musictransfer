# MusicTransfer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

A powerful web-based tool for migrating music playlists between Spotify and YouTube Music. Transfer your favorite playlists seamlessly while maintaining track metadata and organization.

## Prerequisites

- Python 3.9+
- Spotify Developer Account
- Google Cloud Project with YouTube Data API v3 enabled

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Inasayang/musictransfer.git
cd musictransfer
```

2. Install dependencies using PDM:

```bash
pdm install
```

## Configuration

1. Create a `.env` file in the project root:

```env
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# YouTube/Google API Credentials
YOUTUBE_CLIENT_ID=your_google_client_id
YOUTUBE_CLIENT_SECRET=your_google_client_secret
YOUTUBE_API_KEY=your_youtube_data_api_key

# Application Settings
REDIRECT_URI=http://localhost:5000/callback
```

2. **Spotify Setup**:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new app
   - Add `http://localhost:5000/callback` to Redirect URIs
   - Copy Client ID and Client Secret

3. **YouTube Music Setup**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Add `http://localhost:5000/callback` to authorized redirect URIs
   - Also create an API key for YouTube Data API

## Usage

1. Start the application:
```bash
pdm run src/__main__.py
```

2. Open your browser to `http://localhost:5000`

3. Authenticate with both Spotify and YouTube Music:
   - Click "Connect to Spotify" and authorize the application
   - Click "Connect to YouTube Music" and authorize the application

4. Select a Spotify playlist to migrate

5. Click "Start Migration" and monitor the progress

6. Your playlist will be created in YouTube Music with all transferable tracks

## Limitations

- Currently supports migration from Spotify to YouTube Music only
- Some tracks may not be available on the target platform
- Playlist artwork is not transferred
- Migration speed depends on API rate limits

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This tool is for personal use only. Please respect the terms of service of both Spotify and YouTube Music when using this application.