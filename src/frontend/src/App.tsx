import React, { useState, useEffect } from 'react'

// Define types for our data
interface Playlist {
  id: string
  name: string
  track_count: number
}

interface AuthStatus {
  spotify: boolean
  youtube: boolean
}

interface Alert {
  type: 'success' | 'error'
  message: string
  visible: boolean
}

const App: React.FC = () => {
  // State management
  const [authStatus, setAuthStatus] = useState<AuthStatus>({ spotify: false, youtube: false })
  const [selectedPlatform, setSelectedPlatform] = useState<string>('')
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [selectedPlaylistId, setSelectedPlaylistId] = useState<string | null>(null)
  const [playlistIdInput, setPlaylistIdInput] = useState<string>('')
  const [progress, setProgress] = useState<number>(0)
  const [progressText, setProgressText] = useState<string>('Ready to start migration')
  const [migrationResult, setMigrationResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingPlaylists, setLoadingPlaylists] = useState<boolean>(false)
  const [theme, setTheme] = useState<'light' | 'dark'>('light'); // Add theme state
  const [alert, setAlert] = useState<Alert>({ type: 'success', message: '', visible: false });

  // Initialize theme
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    const initialTheme = (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) ? 'dark' : 'light';
    setTheme(initialTheme); // Set theme state
    
    // Apply theme class to document
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(initialTheme);
    document.documentElement.setAttribute('data-theme', initialTheme);

    // Update auth status
    updateAuthStatus();

    // Set up periodic auth status updates
    const interval = setInterval(updateAuthStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Update authentication status
  const updateAuthStatus = () => {
    fetch('/api/auth/status')
      .then(response => response.json())
      .then(data => {
        setAuthStatus(data)
      })
      .catch(error => {
        console.error('Failed to get authentication status:', error)
      })
  }

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme); // Update theme state
    
    // Apply theme class to document
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  // Handle platform selection
  const handlePlatformChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPlatform(e.target.value)
  }

  // Load playlists
  const loadPlaylists = () => {
    if (!selectedPlatform) return

    setLoadingPlaylists(true)
    setError(null)

    fetch(`/api/playlists?platform=${selectedPlatform}`)
      .then(response => {
        // Check if response is ok
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.error) {
          setError(data.error)
          setPlaylists([])
        } else {
          setPlaylists(data)
        }
        setLoadingPlaylists(false)
      })
      .catch(error => {
        console.error('Failed to load playlists:', error);
        // Provide a more user-friendly error message
        if (error.message.includes('401')) {
          setError('Authentication required. Please re-authenticate with the platform.');
        } else if (error.message.includes('500')) {
          setError('Server error occurred. Please try again later.');
        } else if (error.message.includes('Failed to fetch')) {
          setError('Network error. Please check your connection and try again.');
        } else {
          setError(error.message || 'Failed to load playlists. Please try again.');
        }
        setPlaylists([])
        setLoadingPlaylists(false)
      })
  }

  // Select playlist
  const selectPlaylist = (id: string) => {
    setSelectedPlaylistId(id)
    setPlaylistIdInput(id)
  }

  // Start migration
  const startMigration = () => {
    const playlistId = selectedPlaylistId || playlistIdInput
    if (!playlistId) return

    // Reset progress display
    setProgress(0)
    setProgressText('Starting migration...')
    setMigrationResult(null)
    setError(null)

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
          setError(data.error)
          return
        }

        // Start polling migration status
        pollMigrationStatus()
      })
      .catch(error => {
        setError(error.message)
      })
  }

  // Poll migration status
  const pollMigrationStatus = () => {
    const interval = setInterval(() => {
      fetch('/api/migration/status')
        .then(response => response.json())
        .then(data => {
          // Update progress bar
          setProgress(data.progress)
          setProgressText(data.description)

          // Check if completed
          if (!data.running) {
            clearInterval(interval)

            if (data.error) {
              setError(data.error)
            } else {
              setMigrationResult(data.result)
            }
          }
        })
        .catch(error => {
          console.error('Failed to get migration status:', error)
          clearInterval(interval)
        })
    }, 1000)
  }

  // Handle Spotify authentication
  const handleSpotifyAuth = () => {
    const popup = window.open('/auth/spotify', 'Spotify Authentication', 'width=600,height=600')

    // Listen for message from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'auth_complete') {
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }

    window.addEventListener('message', handleMessage)

    // Poll for popup closure as fallback
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed)
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }, 1000)
  }

  // Handle Spotify re-authentication
  const handleSpotifyReauth = () => {
    const popup = window.open('/auth/spotify', 'Spotify Authentication', 'width=600,height=600')

    // Listen for message from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'auth_complete') {
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }

    window.addEventListener('message', handleMessage)

    // Poll for popup closure as fallback
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed)
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }, 1000)
  }

  // Handle YouTube authentication
  const handleYoutubeAuth = () => {
    const popup = window.open('/auth/youtube', 'YouTube Authentication', 'width=600,height=600')

    // Listen for message from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'auth_complete') {
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }

    window.addEventListener('message', handleMessage)

    // Poll for popup closure as fallback
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed)
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }, 1000)
  }

  // Handle YouTube token refresh
  const handleYoutubeTokenRefresh = () => {
    // First try to refresh the token automatically
    fetch('/api/auth/youtube/refresh', {
      method: 'POST'
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Refresh successful
          showAlert('success', 'YouTube authentication refreshed successfully!')
          updateAuthStatus() // Update the UI to show connected status
        } else {
          // Refresh failed
          showAlert('error', 'Automatic refresh failed. Please re-authenticate manually.')
        }
      })
      .catch(err => {
        console.error('Failed to refresh YouTube authentication:', err)
        // If refresh request fails
        showAlert('error', 'Automatic refresh failed. Please re-authenticate manually.')
      })
  }

  // Handle YouTube re-authentication
  const handleYoutubeReauth = () => {
    // Directly open the re-authentication window
    const popup = window.open('/api/auth/youtube/force', 'YouTube Authentication', 'width=600,height=600')

    // Listen for message from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'auth_complete') {
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }

    window.addEventListener('message', handleMessage)

    // Poll for popup closure as fallback
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed)
        window.removeEventListener('message', handleMessage)
        setTimeout(updateAuthStatus, 1000) // Update auth status after popup closes
      }
    }, 1000)
  }

  // Handle Spotify logout
  const handleSpotifyLogout = () => {
    fetch('/api/auth/spotify/logout', {
      method: 'POST'
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showAlert('success', 'Logged out from Spotify successfully')
          updateAuthStatus() // Update the UI to show disconnected status
        } else {
          showAlert('error', 'Failed to logout from Spotify')
        }
      })
      .catch(err => {
        console.error('Failed to logout from Spotify:', err)
        showAlert('error', 'Failed to logout from Spotify')
      })
  }

  // Handle YouTube logout
  const handleYoutubeLogout = () => {
    fetch('/api/auth/youtube/logout', {
      method: 'POST'
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showAlert('success', 'Logged out from YouTube successfully')
          updateAuthStatus() // Update the UI to show disconnected status
        } else {
          showAlert('error', 'Failed to logout from YouTube')
        }
      })
      .catch(err => {
        console.error('Failed to logout from YouTube:', err)
        showAlert('error', 'Failed to logout from YouTube')
      })
  }

  // Check if migration button should be enabled
  const isMigrateButtonEnabled = () => {
    const playlistId = selectedPlaylistId || playlistIdInput
    return playlistId && authStatus.spotify && authStatus.youtube
  }

  // Show alert function
  const showAlert = (type: 'success' | 'error', message: string) => {
    setAlert({ type, message, visible: true });
    // Auto hide alert after 5 seconds
    setTimeout(() => {
      setAlert(prevAlert => ({ ...prevAlert, visible: false }));
    }, 5000);
  };

  return (
    <div className="min-h-screen flex flex-col bg-base-100 font-sans transition-colors duration-300">
      {/* Alert */}
      {alert.visible && (
        <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
          <div className={`alert alert-${alert.type} shadow-xl z-10 max-w-md mx-4 pointer-events-auto`}>
            <div>
              {alert.type === 'success' ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              <span>{alert.message}</span>
            </div>
          </div>
        </div>
      )}
      
      {/* Header */}
      <header className="border-b border-base-300 bg-base-100 sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-primary to-accent flex items-center justify-center shadow-soft">
                <span className="font-bold text-lg" style={{ color: 'hsl(var(--primary-foreground))' }}>MT</span>
              </div>
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">MusicTransfer</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-xl hover:bg-base-200 transition-all duration-300 transform hover:scale-105"
                aria-label="Toggle theme"
              >
                {theme === 'light' ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h1M3 12H2m15.325-6.675l-.707-.707M6.343 17.657l-.707-.707M16.95 16.95l.707.707M6.343 6.343l-.707-.707M12 7a5 5 0 110 10 5 5 0 010-10z" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow container mx-auto px-4 py-12">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-20">
            <h1 className="text-2xl md:text-4xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-primary via-secondary to-accent leading-normal">
              🎵 Music Playlist Migration
            </h1>
            <p className="text-base md:text-lg text-muted-foreground max-w-3xl mx-auto font-light leading-normal">
              Seamlessly migrate your playlists between Spotify and YouTube Music with our fast and reliable tool.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Authentication Card */}
            <div className="card p-8 shadow-soft hover:shadow-soft-xl transition-all duration-500 transform hover:-translate-y-1">
              <h2 className="text-lg font-bold mb-6">Platform Authentication</h2>
              <div className="space-y-5">
                <div className="flex items-center justify-between p-5 rounded-xl transition-all duration-300 hover:shadow-soft-lg">
                  <div className="flex items-center space-x-4">
                    <div className={`w-4 h-4 rounded-full ${authStatus.spotify ? 'bg-success animate-pulse' : 'bg-error'}`}></div>
                    <div>
                      <h3 className="font-semibold text-base">Spotify</h3>
                      <p className="text-sm text-muted-foreground">
                        {authStatus.spotify ? 'Connected' : 'Not Authenticated'}
                      </p>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    {authStatus.spotify ? (
                      <>
                        <button
                          onClick={handleSpotifyReauth}
                          className="btn btn-secondary btn-sm"
                        >
                          Re-auth
                        </button>
                        <button
                          onClick={handleSpotifyLogout}
                          className="btn btn-destructive btn-sm"
                        >
                          Logout
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={handleSpotifyAuth}
                        className="btn btn-primary btn-sm"
                      >
                        Connect
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between p-5 rounded-xl transition-all duration-300 hover:shadow-soft-lg">
                  <div className="flex items-center space-x-4">
                    <div className={`w-4 h-4 rounded-full ${authStatus.youtube ? 'bg-success animate-pulse' : 'bg-error'}`}></div>
                    <div>
                      <h3 className="font-semibold text-base">YouTube Music</h3>
                      <p className="text-sm text-muted-foreground">
                        {authStatus.youtube ? 'Connected' : 'Not Authenticated'}
                      </p>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    {authStatus.youtube ? (
                      <>

                        <button
                          onClick={handleYoutubeReauth}
                          className="btn btn-secondary btn-sm"
                        >
                          Re-auth
                        </button>
                        <button
                          onClick={handleYoutubeTokenRefresh}
                          className="btn btn-secondary btn-sm"
                        >
                          Refresh
                        </button>
                        <button
                          onClick={handleYoutubeLogout}
                          className="btn btn-destructive btn-sm"
                        >
                          Logout
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={handleYoutubeAuth}
                        className="btn btn-primary btn-sm"
                      >
                        Connect
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Migration Card */}
            <div className="card p-8 shadow-soft hover:shadow-soft-xl transition-all duration-500 transform hover:-translate-y-1">
              <h2 className="text-lg font-bold mb-6">Migrate Playlist</h2>
              <div className="space-y-7">
                <div className="flex flex-col sm:flex-row gap-4">
                  <select
                    value={selectedPlatform}
                    onChange={handlePlatformChange}
                    className="select flex-1 rounded-xl py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary border shadow-soft leading-normal"
                  >
                    <option value="">Select Source Platform</option>
                    <option value="spotify">Spotify</option>
                    <option value="youtube">YouTube Music</option>
                  </select>
                  <button
                    onClick={loadPlaylists}
                    disabled={!selectedPlatform}
                    className={`btn px-6 py-3 font-medium transition-all shadow-soft ${selectedPlatform ? 'btn-primary' : 'btn-disabled'}`}
                  >
                    Load Playlists
                  </button>
                </div>

                <div className="border rounded-xl max-h-72 overflow-y-auto p-2 shadow-soft">
                  <ul className="space-y-2">
                    {loadingPlaylists ? (
                      <li className="p-6 text-center text-muted-foreground">
                        <div className="flex justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                        </div>
                        <p className="mt-3">Loading playlists...</p>
                      </li>
                    ) : error && error.includes('YouTube authentication has expired') ? (
                      <li className="p-6 text-center bg-error/10 rounded-xl border border-error/30">
                        <p className="text-error font-medium mb-3">Failed to load: {error}</p>
                        <button
                          onClick={handleYoutubeReauth}
                          className="btn btn-primary rounded-xl px-5 py-2 font-medium transition-all duration-300 transform hover:scale-105 shadow-soft"
                        >
                          Re-authenticate with YouTube
                        </button>
                      </li>
                    ) : error ? (
                      <li className="p-6 text-center bg-error/10 rounded-xl border border-error/30">
                        <p className="text-error font-medium">Failed to load: {error}</p>
                      </li>
                    ) : playlists.length === 0 ? (
                      <li className="p-6 text-center text-muted-foreground">
                        <p className="text-base">No playlists found</p>
                        <p className="text-sm mt-2">Connect to a platform and load playlists to get started</p>
                      </li>
                    ) : (
                      playlists.map(playlist => (
                        <li
                          key={playlist.id}
                          className={`p-4 cursor-pointer transition-all duration-300 rounded-xl border-2 ${selectedPlaylistId === playlist.id ? 'border-primary bg-gradient-to-r from-primary/10 to-accent/10' : 'border-transparent hover:border-base-300 hover:bg-base-300'} shadow-soft`}
                          onClick={() => selectPlaylist(playlist.id)}
                        >
                          <h3 className="font-semibold text-base">{playlist.name}</h3>
                          <div className="flex justify-between items-center mt-2">
                            <p className="text-sm text-muted-foreground">{playlist.track_count} songs</p>
                            <span className="text-xs bg-base-300 px-2 py-1 rounded-lg">ID: {playlist.id.substring(0, 8)}...</span>
                          </div>
                        </li>
                      ))
                    )}
                  </ul>
                </div>

                <div className="flex flex-col gap-4">
                  <input
                    type="text"
                    value={playlistIdInput}
                    onChange={(e) => setPlaylistIdInput(e.target.value)}
                    placeholder="Enter playlist ID or select from above"
                    className="input w-full rounded-xl py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary border shadow-soft"
                  />
                  <button
                    onClick={startMigration}
                    disabled={!isMigrateButtonEnabled()}
                    className={`btn px-6 py-3 font-medium text-base shadow-soft ${isMigrateButtonEnabled() ? 'btn-primary' : 'btn-disabled'}`}
                  >
                    Start Migration
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Progress Section */}
          <div className="mt-12 card p-8 shadow-soft hover:shadow-soft-xl transition-all duration-500">
            <h2 className="text-lg font-bold mb-6">Migration Progress</h2>
            <div className="mb-6">
              <div className="w-full rounded-full h-5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-primary via-secondary to-accent h-5 rounded-full transition-all duration-700 ease-in-out flex items-center justify-end relative"
                  style={{ width: `${progress}%` }}
                >
                  <span className="text-xs font-bold text-white mr-2 absolute right-2">{Math.round(progress)}%</span>
                </div>
              </div>
            </div>
            <div className="text-center text-muted-foreground text-base min-h-[2rem] font-medium">{progressText}</div>
            {migrationResult && (
              <div className="mt-6 p-6 rounded-xl bg-gradient-to-r from-success/10 to-secondary/10 border border-success/30 text-center shadow-soft">
                <h3 className="text-xl font-bold text-success mb-3">Migration Complete!</h3>
                <p className="mb-4 text-base">
                  Your playlist has been successfully migrated to YouTube Music.
                </p>
                <div className="bg-base-100 p-4 rounded-xl inline-block shadow-soft">
                  <p className="font-mono break-all">
                    Playlist ID: <span className="font-bold text-secondary">{migrationResult}</span>
                  </p>
                </div>
                <p className="mt-4 text-muted-foreground">
                  You can view the new playlist in YouTube Music.
                </p>
              </div>
            )}
            {error && !error.includes('YouTube authentication has expired') && (
              <div className="mt-6 p-6 rounded-xl bg-gradient-to-r from-error/10 to-red-100 border border-error/30 text-center shadow-soft">
                <h3 className="text-xl font-bold text-error mb-3">Error</h3>
                <p className="break-all text-base">
                  {error}
                </p>
                {error.includes('YouTube authentication has expired') && (
                  <button
                    onClick={handleYoutubeReauth}
                    className="mt-4 btn btn-primary rounded-xl px-5 py-2 font-medium transition-all duration-300 transform hover:scale-105 shadow-soft"
                  >
                    Re-authenticate with YouTube
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App