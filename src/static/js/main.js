// Global variables
let selectedPlaylistId = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize authentication status
    updateAuthStatus();
    
    // Bind event listeners
    bindEventListeners();
});

// Update authentication status
function updateAuthStatus() {
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            // Update Spotify status
            const spotifyStatus = document.getElementById('spotify-status');
            const spotifyBtn = document.getElementById('spotify-auth-btn');
            
            if (data.spotify) {
                spotifyStatus.textContent = 'Authenticated';
                spotifyStatus.className = 'status-indicator authenticated';
                spotifyBtn.disabled = true;
            } else {
                spotifyStatus.textContent = 'Not Authenticated';
                spotifyStatus.className = 'status-indicator not-authenticated';
                spotifyBtn.disabled = false;
            }
            
            // Update YouTube status
            const youtubeStatus = document.getElementById('youtube-status');
            const youtubeBtn = document.getElementById('youtube-auth-btn');
            
            if (data.youtube) {
                youtubeStatus.textContent = 'Authenticated';
                youtubeStatus.className = 'status-indicator authenticated';
                youtubeBtn.disabled = true;
            } else {
                youtubeStatus.textContent = 'Not Authenticated';
                youtubeStatus.className = 'status-indicator not-authenticated';
                youtubeBtn.disabled = false;
            }
            
            // Update migration button state
            updateMigrateButtonState();
        })
        .catch(error => {
            console.error('Failed to get authentication status:', error);
        });
}

// Bind event listeners
function bindEventListeners() {
    // Spotify authentication button
    document.getElementById('spotify-auth-btn').addEventListener('click', function() {
        window.open('/auth/spotify', 'Spotify Authentication', 'width=600,height=600');
    });
    
    // YouTube authentication button
    document.getElementById('youtube-auth-btn').addEventListener('click', function() {
        window.open('/auth/youtube', 'YouTube Authentication', 'width=600,height=600');
    });
    
    // Platform selector
    document.getElementById('platform-selector').addEventListener('change', function() {
        const platform = this.value;
        const loadBtn = document.getElementById('load-playlists-btn');
        loadBtn.disabled = !platform;
    });
    
    // Load playlists button
    document.getElementById('load-playlists-btn').addEventListener('click', function() {
        const platform = document.getElementById('platform-selector').value;
        if (platform) {
            loadPlaylists(platform);
        }
    });
    
    // Migration button
    document.getElementById('migrate-btn').addEventListener('click', function() {
        const playlistId = selectedPlaylistId || document.getElementById('playlist-id-input').value;
        if (playlistId) {
            startMigration(playlistId);
        }
    });
    
    // Playlist ID input field
    document.getElementById('playlist-id-input').addEventListener('input', function() {
        updateMigrateButtonState();
    });
}

// Load playlists
function loadPlaylists(platform) {
    const container = document.getElementById('playlists-container');
    container.innerHTML = '<li>Loading...</li>';
    
    fetch(`/api/playlists?platform=${platform}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                container.innerHTML = `<li class="error">Failed to load: ${data.error}</li>`;
                return;
            }
            
            if (data.length === 0) {
                container.innerHTML = '<li>No playlists found</li>';
                return;
            }
            
            container.innerHTML = '';
            data.forEach(playlist => {
                const li = document.createElement('li');
                li.className = 'playlist-item';
                li.innerHTML = `
                    <h3>${playlist.name}</h3>
                    <p>${playlist.track_count} songs</p>
                    <small>ID: ${playlist.id}</small>
                `;
                li.addEventListener('click', function() {
                    selectPlaylist(playlist.id);
                });
                container.appendChild(li);
            });
        })
        .catch(error => {
            container.innerHTML = `<li class="error">Failed to load: ${error.message}</li>`;
        });
}

// Select playlist
function selectPlaylist(playlistId) {
    selectedPlaylistId = playlistId;
    document.getElementById('playlist-id-input').value = playlistId;
    updateMigrateButtonState();
    
    // Highlight selected playlist item
    document.querySelectorAll('.playlist-item').forEach(item => {
        item.style.backgroundColor = '';
    });
    event.currentTarget.style.backgroundColor = '#e3f2fd';
}

// Update migration button state
function updateMigrateButtonState() {
    const playlistId = selectedPlaylistId || document.getElementById('playlist-id-input').value;
    const migrateBtn = document.getElementById('migrate-btn');
    
    // Check if both platforms are authenticated
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            const isFullyAuthenticated = data.spotify && data.youtube;
            migrateBtn.disabled = !playlistId || !isFullyAuthenticated;
        });
}

// Start migration
function startMigration(playlistId) {
    // Reset progress display
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-text').textContent = 'Starting migration...';
    document.getElementById('result-container').classList.add('hidden');
    
    // Send migration request
    fetch('/api/migrate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ playlist_id: playlistId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Start polling migration status
        pollMigrationStatus();
    })
    .catch(error => {
        showError(error.message);
    });
}

// Poll migration status
function pollMigrationStatus() {
    const interval = setInterval(function() {
        fetch('/api/migration/status')
            .then(response => response.json())
            .then(data => {
                // Update progress bar
                document.getElementById('progress-fill').style.width = data.progress + '%';
                document.getElementById('progress-text').textContent = data.description;
                
                // Check if completed
                if (!data.running) {
                    clearInterval(interval);
                    
                    if (data.error) {
                        showError(data.error);
                    } else {
                        showResult(data.result);
                    }
                }
            })
            .catch(error => {
                console.error('Failed to get migration status:', error);
                clearInterval(interval);
            });
    }, 1000);
}

// Show error
function showError(error) {
    document.getElementById('progress-text').textContent = `Error: ${error}`;
    document.getElementById('progress-fill').style.backgroundColor = '#dc3545';
}

// Show result
function showResult(playlistId) {
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    
    resultText.innerHTML = `
        Migration completed! YouTube Music playlist ID: <strong>${playlistId}</strong><br>
        You can view the new playlist in YouTube Music.
    `;
    
    resultContainer.classList.remove('hidden');
}

// Periodically update authentication status
setInterval(updateAuthStatus, 5000);