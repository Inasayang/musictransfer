import { AlertState } from '../types'

interface AlertOverlayProps {
  alert: AlertState | null
}

const AlertOverlay = ({ alert }: AlertOverlayProps) => {
  if (!alert) {
    return null
  }

  const isSuccess = alert.type === 'success'

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
      <div className={`alert alert-${alert.type} shadow-xl z-10 max-w-md mx-4 pointer-events-auto`}>
        <div className="flex items-center space-x-3">
          {isSuccess ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="stroke-current flex-shrink-0 h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="stroke-current flex-shrink-0 h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          )}
          <span>{alert.message}</span>
        </div>
      </div>
    </div>
  )
}

export default AlertOverlay
