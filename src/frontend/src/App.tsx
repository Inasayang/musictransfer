import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import AlertOverlay from './components/AlertOverlay'
import AppHeader from './components/AppHeader'
import AuthenticationCard from './components/AuthenticationCard'
import Hero from './components/Hero'
import MigrationCard from './components/MigrationCard'
import ProgressCard from './components/ProgressCard'
import type { AuthProviderConfig } from './components/AuthenticationCard'
import type { AlertState, AuthStatus, Playlist } from './types'

const applyTheme = (theme: 'light' | 'dark') => {
  document.documentElement.classList.remove('light', 'dark')
  document.documentElement.classList.add(theme)
  document.documentElement.setAttribute('data-theme', theme)
}

const App = () => {
  const [authStatus, setAuthStatus] = useState<AuthStatus>({ spotify: false, youtube: false })
  const [selectedPlatform, setSelectedPlatform] = useState<'spotify' | 'youtube' | ''>('')
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [selectedPlaylistId, setSelectedPlaylistId] = useState<string | null>(null)
  const [playlistIdInput, setPlaylistIdInput] = useState<string>('')
  const [progress, setProgress] = useState<number>(0)
  const [progressText, setProgressText] = useState<string>('Ready to start migration')
  const [migrationResult, setMigrationResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingPlaylists, setLoadingPlaylists] = useState<boolean>(false)
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [alert, setAlert] = useState<AlertState | null>(null)

  const alertTimeoutRef = useRef<number | null>(null)
  const migrationStatusIntervalRef = useRef<number | null>(null)
  const authPopupCleanupRef = useRef<(() => void) | null>(null)

  const updateAuthStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/status')
      if (!response.ok) {
        throw new Error(`Failed to fetch authentication status: ${response.status}`)
      }

      const data: AuthStatus = await response.json()
      setAuthStatus(data)
    } catch (err) {
      console.error('Failed to get authentication status:', err)
    }
  }, [])

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme')
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const initialTheme = savedTheme === 'dark' || (!savedTheme && systemPrefersDark) ? 'dark' : 'light'

    setTheme(initialTheme)
    applyTheme(initialTheme)
  }, [])

  useEffect(() => {
    updateAuthStatus()
    const interval = window.setInterval(updateAuthStatus, 5000)

    return () => {
      window.clearInterval(interval)
    }
  }, [updateAuthStatus])

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const showAlert = useCallback((type: AlertState['type'], message: string) => {
    if (alertTimeoutRef.current) {
      window.clearTimeout(alertTimeoutRef.current)
    }

    setAlert({ type, message })

    alertTimeoutRef.current = window.setTimeout(() => {
      setAlert(null)
      alertTimeoutRef.current = null
    }, 5000)
  }, [])

  const pollMigrationStatus = useCallback(() => {
    if (migrationStatusIntervalRef.current) {
      window.clearInterval(migrationStatusIntervalRef.current)
      migrationStatusIntervalRef.current = null
    }

    const intervalId = window.setInterval(async () => {
      try {
        const response = await fetch('/api/migration/status')
        if (!response.ok) {
          throw new Error('Failed to get migration status')
        }

        const data = await response.json()
        setProgress(data.progress)
        setProgressText(data.description)

        if (!data.running) {
          window.clearInterval(intervalId)
          migrationStatusIntervalRef.current = null

          if (data.error) {
            setError(data.error)
          } else {
            setMigrationResult(data.result)
          }
        }
      } catch (err) {
        console.error('Failed to get migration status:', err)
        window.clearInterval(intervalId)
        migrationStatusIntervalRef.current = null
      }
    }, 1000)

    migrationStatusIntervalRef.current = intervalId
  }, [])

  const loadPlaylists = useCallback(async () => {
    if (!selectedPlatform) {
      return
    }

    setLoadingPlaylists(true)
    setError(null)

    try {
      const response = await fetch(`/api/playlists?platform=${selectedPlatform}`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      if (data.error) {
        setError(data.error)
        setPlaylists([])
      } else {
        setPlaylists(data)
      }
    } catch (err) {
      console.error('Failed to load playlists:', err)

      const message = err instanceof Error ? err.message : 'Failed to load playlists. Please try again.'
      if (message.includes('401')) {
        setError('Authentication required. Please re-authenticate with the platform.')
      } else if (message.includes('500')) {
        setError('Server error occurred. Please try again later.')
      } else if (message.includes('Failed to fetch')) {
        setError('Network error. Please check your connection and try again.')
      } else {
        setError(message)
      }

      setPlaylists([])
    } finally {
      setLoadingPlaylists(false)
    }
  }, [selectedPlatform])

  const startMigration = useCallback(async () => {
    const playlistId = selectedPlaylistId ?? playlistIdInput.trim()
    if (!playlistId) {
      return
    }

    setProgress(0)
    setProgressText('Starting migration...')
    setMigrationResult(null)
    setError(null)

    try {
      const response = await fetch('/api/migrate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ playlist_id: playlistId }),
      })

      const data = await response.json()
      if (data.error) {
        setError(data.error)
        return
      }

      pollMigrationStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start migration. Please try again.')
    }
  }, [playlistIdInput, selectedPlaylistId, pollMigrationStatus])

  const openAuthPopup = useCallback(
    (url: string) => {
      if (authPopupCleanupRef.current) {
        authPopupCleanupRef.current()
        authPopupCleanupRef.current = null
      }

      const popup = window.open(url, 'Authentication', 'width=600,height=600')
      if (!popup) {
        showAlert('error', 'Unable to open authentication window. Please allow popups.')
        return
      }

      let intervalId: number | null = null

      const cleanup = () => {
        window.removeEventListener('message', handleMessage)
        if (intervalId) {
          window.clearInterval(intervalId)
        }
        authPopupCleanupRef.current = null
      }

      const finish = () => {
        cleanup()
        window.setTimeout(updateAuthStatus, 1000)
      }

      const handleMessage = (event: MessageEvent) => {
        if (event.data?.type === 'auth_complete') {
          finish()
        }
      }

      window.addEventListener('message', handleMessage)

      intervalId = window.setInterval(() => {
        if (popup.closed) {
          finish()
        }
      }, 1000)

      authPopupCleanupRef.current = cleanup
    },
    [showAlert, updateAuthStatus],
  )

  const handleSpotifyAuth = useCallback(() => openAuthPopup('/auth/spotify'), [openAuthPopup])
  const handleSpotifyReauth = useCallback(() => openAuthPopup('/auth/spotify'), [openAuthPopup])

  const handleYoutubeAuth = useCallback(() => openAuthPopup('/auth/youtube'), [openAuthPopup])
  const handleYoutubeReauth = useCallback(() => openAuthPopup('/api/auth/youtube/force'), [openAuthPopup])

  const handleYoutubeTokenRefresh = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/youtube/refresh', {
        method: 'POST',
      })

      const data = await response.json()
      if (data.success) {
        showAlert('success', 'YouTube authentication refreshed successfully!')
        updateAuthStatus()
      } else {
        showAlert('error', 'Automatic refresh failed. Please re-authenticate manually.')
      }
    } catch (err) {
      console.error('Failed to refresh YouTube authentication:', err)
      showAlert('error', 'Automatic refresh failed. Please re-authenticate manually.')
    }
  }, [showAlert, updateAuthStatus])

  const handleSpotifyLogout = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/spotify/logout', {
        method: 'POST',
      })
      const data = await response.json()

      if (data.success) {
        showAlert('success', 'Logged out from Spotify successfully')
        updateAuthStatus()
      } else {
        showAlert('error', 'Failed to logout from Spotify')
      }
    } catch (err) {
      console.error('Failed to logout from Spotify:', err)
      showAlert('error', 'Failed to logout from Spotify')
    }
  }, [showAlert, updateAuthStatus])

  const handleYoutubeLogout = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/youtube/logout', {
        method: 'POST',
      })

      const data = await response.json()
      if (data.success) {
        showAlert('success', 'Logged out from YouTube successfully')
        updateAuthStatus()
      } else {
        showAlert('error', 'Failed to logout from YouTube')
      }
    } catch (err) {
      console.error('Failed to logout from YouTube:', err)
      showAlert('error', 'Failed to logout from YouTube')
    }
  }, [showAlert, updateAuthStatus])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))
  }, [])

  const handlePlatformChange = useCallback((platform: string) => {
    setSelectedPlatform(platform as 'spotify' | 'youtube' | '')
    setPlaylists([])
    setSelectedPlaylistId(null)
    setPlaylistIdInput('')
  }, [])

  const handleSelectPlaylist = useCallback((id: string) => {
    setSelectedPlaylistId(id)
    setPlaylistIdInput(id)
  }, [])

  const handlePlaylistInputChange = useCallback((value: string) => {
    setPlaylistIdInput(value)
    setSelectedPlaylistId(null)
  }, [])

  const canStartMigration = useMemo(() => {
    const playlistId = selectedPlaylistId ?? playlistIdInput.trim()
    return Boolean(playlistId && authStatus.spotify && authStatus.youtube)
  }, [authStatus.spotify, authStatus.youtube, playlistIdInput, selectedPlaylistId])

  const authProviders = useMemo<AuthProviderConfig[]>(
    () => [
      {
        id: 'spotify',
        name: 'Spotify',
        connected: authStatus.spotify,
        actions: authStatus.spotify
          ? [
              { label: 'Re-auth', onClick: handleSpotifyReauth, variant: 'secondary' },
              { label: 'Logout', onClick: handleSpotifyLogout, variant: 'destructive' },
            ]
          : [{ label: 'Connect', onClick: handleSpotifyAuth, variant: 'primary' }],
      },
      {
        id: 'youtube',
        name: 'YouTube Music',
        connected: authStatus.youtube,
        actions: authStatus.youtube
          ? [
              { label: 'Re-auth', onClick: handleYoutubeReauth, variant: 'secondary' },
              { label: 'Refresh', onClick: handleYoutubeTokenRefresh, variant: 'secondary' },
              { label: 'Logout', onClick: handleYoutubeLogout, variant: 'destructive' },
            ]
          : [{ label: 'Connect', onClick: handleYoutubeAuth, variant: 'primary' }],
      },
    ],
    [
      authStatus.spotify,
      authStatus.youtube,
      handleSpotifyAuth,
      handleSpotifyLogout,
      handleSpotifyReauth,
      handleYoutubeAuth,
      handleYoutubeLogout,
      handleYoutubeReauth,
      handleYoutubeTokenRefresh,
    ],
  )

  useEffect(() => {
    return () => {
      if (alertTimeoutRef.current) {
        window.clearTimeout(alertTimeoutRef.current)
      }

      if (migrationStatusIntervalRef.current) {
        window.clearInterval(migrationStatusIntervalRef.current)
      }

      if (authPopupCleanupRef.current) {
        authPopupCleanupRef.current()
      }
    }
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-base-100 font-sans transition-colors duration-300">
      <AlertOverlay alert={alert} />
      <AppHeader theme={theme} onToggleTheme={toggleTheme} />

      <main className="flex-grow container mx-auto px-4 py-12">
        <div className="max-w-5xl mx-auto">
          <Hero />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <AuthenticationCard providers={authProviders} />
            <MigrationCard
              selectedPlatform={selectedPlatform}
              onPlatformChange={handlePlatformChange}
              onLoadPlaylists={loadPlaylists}
              playlists={playlists}
              selectedPlaylistId={selectedPlaylistId}
              onSelectPlaylist={handleSelectPlaylist}
              loading={loadingPlaylists}
              error={error}
              playlistIdInput={playlistIdInput}
              onPlaylistIdInputChange={handlePlaylistInputChange}
              onStartMigration={startMigration}
              canStartMigration={canStartMigration}
              onYoutubeReauth={handleYoutubeReauth}
            />
          </div>

          <ProgressCard
            progress={progress}
            progressText={progressText}
            migrationResult={migrationResult}
            error={error}
          />
        </div>
      </main>
    </div>
  )
}

export default App
