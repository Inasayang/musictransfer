export interface Playlist {
  id: string
  name: string
  track_count: number
}

export interface AuthStatus {
  spotify: boolean
  youtube: boolean
}

export type AlertType = 'success' | 'error'

export interface AlertState {
  type: AlertType
  message: string
}
