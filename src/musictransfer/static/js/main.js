// Global variables
let selectedPlaylistId = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    initializeTheme();
    
    // Initialize authentication status
    updateAuthStatus();
    
    // Bind event listeners
    bindEventListeners();
});

// Initialize theme based on saved preference or system preference
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

// Update authentication status
function updateAuthStatus() {
    fetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            // Update Spotify status
            const spotifyStatus = document.getElementById('spotify-status');
            const spotifyBtn = document.getElementById('spotify-auth-btn');
            const spotifyReauthBtn = document.getElementById('spotify-reauth-btn');
            
            if (data.spotify) {
                spotifyStatus.textContent = 'Connected';
                spotifyStatus.className = 'px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400';
                spotifyBtn.classList.add('hidden'); // Hide connect button when connected
                spotifyReauthBtn.classList.remove('hidden'); // Show re-auth button when connected
                // Update status indicator
                spotifyStatus.previousElementSibling.querySelector('div').className = 'w-3 h-3 rounded-full bg-green-500';
            } else {
                spotifyStatus.textContent = 'Not Authenticated';
                spotifyStatus.className = 'px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400';
                spotifyBtn.classList.remove('hidden'); // Show connect button when not connected
                spotifyReauthBtn.classList.add('hidden'); // Hide re-auth button when not connected
                // Update status indicator
                spotifyStatus.previousElementSibling.querySelector('div').className = 'w-3 h-3 rounded-full bg-red-500';
            }
            
            // Update YouTube status
            const youtubeStatus = document.getElementById('youtube-status');
            const youtubeBtn = document.getElementById('youtube-auth-btn');
            const youtubeReauthBtn = document.getElementById('youtube-reauth-btn');
            
            if (data.youtube) {
                youtubeStatus.textContent = 'Connected';
                youtubeStatus.className = 'px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400';
                youtubeBtn.classList.add('hidden'); // Hide connect button when connected
                youtubeReauthBtn.classList.remove('hidden'); // Show re-auth button when connected
                // Update status indicator
                youtubeStatus.previousElementSibling.querySelector('div').className = 'w-3 h-3 rounded-full bg-green-500';
            } else {
                youtubeStatus.textContent = 'Not Authenticated';
                youtubeStatus.className = 'px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400';
                youtubeBtn.classList.remove('hidden'); // Show connect button when not connected
                youtubeReauthBtn.classList.add('hidden'); // Hide re-auth button when not connected
                // Update status indicator
                youtubeStatus.previousElementSibling.querySelector('div').className = 'w-3 h-3 rounded-full bg-red-500';
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
    
    // Spotify re-authentication button
    document.getElementById('spotify-reauth-btn').addEventListener('click', function() {
        // For Spotify, we don't have an automatic refresh mechanism, so we directly re-authenticate
        window.open('/auth/spotify', 'Spotify Authentication', 'width=600,height=600');
    });
    
    // YouTube authentication button
    document.getElementById('youtube-auth-btn').addEventListener('click', function() {
        window.open('/auth/youtube', 'YouTube Authentication', 'width=600,height=600');
    });
    
    // YouTube re-authentication button
    document.getElementById('youtube-reauth-btn').addEventListener('click', function() {
        // First try to refresh the token automatically
        fetch('/api/auth/youtube/refresh', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Refresh successful
                alert('YouTube authentication refreshed successfully!');
                updateAuthStatus(); // Update the UI to show connected status
            } else {
                // Refresh failed, need to re-authenticate manually
                alert('Automatic refresh failed. Opening manual authentication window...');
                window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600');
            }
        })
        .catch(err => {
            console.error('Failed to refresh YouTube authentication:', err);
            // If refresh request fails, proceed with manual re-authentication
            alert('Automatic refresh failed. Opening manual authentication window...');
            window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600');
        });
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
    container.innerHTML = '<li class="p-4 text-center text-vercel-gray-400">Loading...</li>';
    
    fetch(`/api/playlists?platform=${platform}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // Check if this is a YouTube authentication error
                if (platform === 'youtube' && (data.error.includes('YouTube authentication has expired') || data.error.includes('Please re-authenticate with YouTube'))) {
                    container.innerHTML = `<li class="p-4 text-center text-red-400">Failed to load: ${data.error}<br><button id="reauth-youtube-playlist-btn" class="mt-2 bg-vercel-blue-500 hover:bg-vercel-blue-600 text-white text-sm font-medium py-1.5 px-3 rounded-lg transition duration-200">Re-authenticate with YouTube</button></li>`;
                    
                    // Add event listener to the re-authentication button
                    setTimeout(() => {
                        const reauthBtn = document.getElementById('reauth-youtube-playlist-btn');
                        if (reauthBtn) {
                            reauthBtn.addEventListener('click', function() {
                                // First try to refresh the token automatically
                                fetch('/api/auth/youtube/refresh', {
                                    method: 'POST'
                                })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        // Refresh successful, try to load playlists again
                                        container.innerHTML = '<li class="p-4 text-center text-vercel-gray-400">Authentication refreshed! Reloading playlists...</li>';
                                        setTimeout(() => loadPlaylists(platform), 1000);
                                    } else {
                                        // Refresh failed, need to re-authenticate manually
                                        container.innerHTML = '<li class="p-4 text-center text-red-400">Automatic refresh failed. Manual re-authentication required...<br>Opening authentication window...</li>';
                                        
                                        // Open YouTube authentication in a new window
                                        window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600');
                                        
                                        // Update UI to show that re-authentication is in progress
                                        container.innerHTML = '<li class="p-4 text-center text-vercel-gray-400">Manual re-authentication in progress... Please complete the authentication in the popup window and try loading playlists again.</li>';
                                    }
                                })
                                .catch(err => {
                                    console.error('Failed to refresh YouTube authentication:', err);
                                    // If refresh request fails, proceed with manual re-authentication
                                    container.innerHTML = '<li class="p-4 text-center text-red-400">Automatic refresh failed. Manual re-authentication required...<br>Opening authentication window...</li>';
                                    
                                    // Open YouTube authentication in a new window
                                    window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600');
                                    
                                    // Update UI to show that re-authentication is in progress
                                    container.innerHTML = '<li class="p-4 text-center text-vercel-gray-400">Manual re-authentication in progress... Please complete the authentication in the popup window and try loading playlists again.</li>';
                                });
                            });
                        }
                    }, 100);
                } else {
                    container.innerHTML = `<li class="p-4 text-center text-red-400">Failed to load: ${data.error}</li>`;
                }
                return;
            }
            
            if (data.length === 0) {
                container.innerHTML = '<li class="p-4 text-center text-vercel-gray-400">No playlists found</li>';
                return;
            }
            
            container.innerHTML = '';
            data.forEach(playlist => {
                const li = document.createElement('li');
                li.className = 'p-4 hover:bg-vercel-gray-700 cursor-pointer transition duration-150 ease-in-out';
                li.innerHTML = `
                    <h3 class="text-sm font-medium text-vercel-gray-100">${playlist.name}</h3>
                    <p class="text-vercel-gray-400 text-xs mt-1">${playlist.track_count} songs</p>
                    <small class="text-vercel-gray-500 text-xs truncate block mt-1">ID: ${playlist.id}</small>
                `;
                li.addEventListener('click', function() {
                    selectPlaylist(playlist.id);
                });
                container.appendChild(li);
            });
        })
        .catch(error => {
            container.innerHTML = `<li class="p-4 text-center text-red-400">Failed to load: ${error.message}</li>`;
        });
}

// Select playlist
function selectPlaylist(playlistId) {
    selectedPlaylistId = playlistId;
    document.getElementById('playlist-id-input').value = playlistId;
    updateMigrateButtonState();
    
    // Highlight selected playlist item
    document.querySelectorAll('#playlists-container li').forEach(item => {
        item.classList.remove('bg-vercel-gray-700', 'border-l-2', 'border-l-vercel-blue-500');
    });
    
    // Add highlight to selected item (if event is available)
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('bg-vercel-gray-700', 'border-l-2', 'border-l-vercel-blue-500');
    }
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
    const progressText = document.getElementById('progress-text');
    progressText.textContent = `Error: ${error}`;
    document.getElementById('progress-fill').classList.remove('bg-gradient-to-r', 'from-vercel-blue-500', 'to-vercel-purple-500');
    document.getElementById('progress-fill').classList.add('bg-red-500');
    
    // Check if this is a YouTube authentication error and provide re-authentication option
    if (error.includes('YouTube authentication has expired') || error.includes('Please re-authenticate with YouTube')) {
        progressText.innerHTML += '<br><button id="reauth-youtube-btn" class="mt-2 bg-vercel-blue-500 hover:bg-vercel-blue-600 text-white text-sm font-medium py-1.5 px-3 rounded-lg transition duration-200">Re-authenticate with YouTube</button>';
        
        // Add event listener to the re-authentication button
        setTimeout(() => {
            const reauthBtn = document.getElementById('reauth-youtube-btn');
            if (reauthBtn) {
                reauthBtn.addEventListener('click', function() {
                    // First try to refresh the token automatically
                    fetch('/api/auth/youtube/refresh', {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Refresh successful
                            progressText.textContent = 'YouTube authentication refreshed successfully! You can now try the migration again.';
                            document.getElementById('progress-fill').classList.remove('bg-red-500');
                            document.getElementById('progress-fill').classList.add('bg-gradient-to-r', 'from-vercel-blue-500', 'to-vercel-purple-500');
                            updateAuthStatus(); // Update the UI to show connected status
                        } else {
                            // Refresh failed, need to re-authenticate manually
                            progressText.innerHTML = 'Automatic refresh failed. Manual re-authentication required...';
                            
                            // Open YouTube authentication in a new window
                            window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600');
                            
                            // Update UI to show that re-authentication is in progress
                            progressText.innerHTML = 'Manual re-authentication in progress... Please complete the authentication in the popup window.';
                            
                            // Periodically check if authentication is complete
                            const authCheckInterval = setInterval(() => {
                                fetch('/api/auth/status')
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.youtube) {
                                            clearInterval(authCheckInterval);
                                            progressText.textContent = 'YouTube re-authentication successful! You can now try the migration again.';
                                            document.getElementById('progress-fill').classList.remove('bg-red-500');
                                            document.getElementById('progress-fill').classList.add('bg-gradient-to-r', 'from-vercel-blue-500', 'to-vercel-purple-500');
                                            updateAuthStatus(); // Update the UI to show connected status
                                        }
                                    })
                                    .catch(err => {
                                        console.error('Failed to check authentication status:', err);
                                    });
                            }, 2000); // Check every 2 seconds
                        }
                    })
                    .catch(err => {
                        console.error('Failed to refresh YouTube authentication:', err);
                        // If refresh request fails, proceed with manual re-authentication
                        progressText.innerHTML = 'Automatic refresh failed. Manual re-authentication required...';
                        
                        // Open YouTube authentication in a new window
                        window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600');
                        
                        // Update UI to show that re-authentication is in progress
                        progressText.innerHTML = 'Manual re-authentication in progress... Please complete the authentication in the popup window.';
                        
                        // Periodically check if authentication is complete
                        const authCheckInterval = setInterval(() => {
                            fetch('/api/auth/status')
                                .then(response => response.json())
                                .then(data => {
                                    if (data.youtube) {
                                        clearInterval(authCheckInterval);
                                        progressText.textContent = 'YouTube re-authentication successful! You can now try the migration again.';
                                        document.getElementById('progress-fill').classList.remove('bg-red-500');
                                        document.getElementById('progress-fill').classList.add('bg-gradient-to-r', 'from-vercel-blue-500', 'to-vercel-purple-500');
                                        updateAuthStatus(); // Update the UI to show connected status
                                    }
                                })
                                .catch(err => {
                                    console.error('Failed to check authentication status:', err);
                                });
                        }, 2000); // Check every 2 seconds
                    });
                });
            }
        }, 100);
    }
}

// Show result
function showResult(playlistId) {
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    
    resultText.innerHTML = `
        Migration completed! YouTube Music playlist ID: <strong class="text-vercel-gray-100">${playlistId}</strong><br>
        You can view the new playlist in YouTube Music.
    `;
    
    resultContainer.classList.remove('hidden');
    
    // Reset progress bar to original colors
    document.getElementById('progress-fill').classList.remove('bg-red-500');
    document.getElementById('progress-fill').classList.add('bg-gradient-to-r', 'from-vercel-blue-500', 'to-vercel-purple-500');
}

// Periodically update authentication status
setInterval(updateAuthStatus, 5000);