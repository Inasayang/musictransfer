import type { Playlist } from '../types'

interface MigrationCardProps {
  selectedPlatform: string
  onPlatformChange: (platform: string) => void
  onLoadPlaylists: () => void
  playlists: Playlist[]
  selectedPlaylistId: string | null
  onSelectPlaylist: (playlistId: string) => void
  loading: boolean
  error: string | null
  playlistIdInput: string
  onPlaylistIdInputChange: (value: string) => void
  onStartMigration: () => void
  canStartMigration: boolean
  onYoutubeReauth: () => void
}

const MigrationCard = ({
  selectedPlatform,
  onPlatformChange,
  onLoadPlaylists,
  playlists,
  selectedPlaylistId,
  onSelectPlaylist,
  loading,
  error,
  playlistIdInput,
  onPlaylistIdInputChange,
  onStartMigration,
  canStartMigration,
  onYoutubeReauth,
}: MigrationCardProps) => {
  const hasNoPlaylists = !loading && !error && playlists.length === 0
  const youtubeAuthExpired = Boolean(error && error.includes('YouTube authentication has expired'))

  const renderPlaylistContent = () => {
    if (loading) {
      return (
        <li className="p-6 text-center text-muted-foreground">
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
          <p className="mt-3">Loading playlists...</p>
        </li>
      )
    }

    if (youtubeAuthExpired) {
      return (
        <li className="p-6 text-center bg-error/10 rounded-xl border border-error/30">
          <p className="text-error font-medium mb-3">Failed to load: {error}</p>
          <button
            onClick={onYoutubeReauth}
            className="btn btn-primary rounded-xl px-5 py-2 font-medium transition-all duration-300 transform hover:scale-105 shadow-soft"
          >
            Re-authenticate with YouTube
          </button>
        </li>
      )
    }

    if (error) {
      return (
        <li className="p-6 text-center bg-error/10 rounded-xl border border-error/30">
          <p className="text-error font-medium">Failed to load: {error}</p>
        </li>
      )
    }

    if (hasNoPlaylists) {
      return (
        <li className="p-6 text-center text-muted-foreground">
          <p className="text-base">No playlists found</p>
          <p className="text-sm mt-2">Connect to a platform and load playlists to get started</p>
        </li>
      )
    }

    return playlists.map((playlist) => (
      <li
        key={playlist.id}
        className={`p-4 cursor-pointer transition-all duration-300 rounded-xl border-2 ${
          selectedPlaylistId === playlist.id
            ? 'border-primary bg-gradient-to-r from-primary/10 to-accent/10'
            : 'border-transparent hover:border-base-300 hover:bg-base-300'
        } shadow-soft`}
        onClick={() => onSelectPlaylist(playlist.id)}
      >
        <h3 className="font-semibold text-base">{playlist.name}</h3>
        <div className="flex justify-between items-center mt-2">
          <p className="text-sm text-muted-foreground">{playlist.track_count} songs</p>
          <span className="text-xs bg-base-300 px-2 py-1 rounded-lg">ID: {playlist.id.substring(0, 8)}...</span>
        </div>
      </li>
    ))
  }

  return (
    <div className="card p-8 shadow-soft hover:shadow-soft-xl transition-all duration-500 transform hover:-translate-y-1">
      <h2 className="text-lg font-bold mb-6">Migrate Playlist</h2>
      <div className="space-y-7">
        <div className="flex flex-col sm:flex-row gap-4">
          <select
            value={selectedPlatform}
            onChange={(event) => onPlatformChange(event.target.value)}
            className="select flex-1 rounded-xl py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary border shadow-soft leading-normal"
          >
            <option value="">Select Source Platform</option>
            <option value="spotify">Spotify</option>
            <option value="youtube">YouTube Music</option>
          </select>
          <button
            onClick={onLoadPlaylists}
            disabled={!selectedPlatform}
            className="btn btn-primary px-6 py-3 font-medium transition-all shadow-soft"
          >
            Load Playlists
          </button>
        </div>

        <div className="border rounded-xl max-h-72 overflow-y-auto p-2 shadow-soft">
          <ul className="space-y-2">{renderPlaylistContent()}</ul>
        </div>

        <div className="flex flex-col gap-4">
          <input
            type="text"
            value={playlistIdInput}
            onChange={(event) => onPlaylistIdInputChange(event.target.value)}
            placeholder="Enter playlist ID or select from above"
            className="input w-full rounded-xl py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary border shadow-soft"
          />
          <button
            onClick={onStartMigration}
            disabled={!canStartMigration}
            className="btn btn-primary px-6 py-3 font-medium text-base shadow-soft"
          >
            Start Migration
          </button>
        </div>
      </div>
    </div>
  )
}

export default MigrationCard
