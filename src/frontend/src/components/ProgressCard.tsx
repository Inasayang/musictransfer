interface ProgressCardProps {
  progress: number
  progressText: string
  migrationResult: string | null
  error: string | null
}

const ProgressCard = ({ progress, progressText, migrationResult, error }: ProgressCardProps) => {
  const youtubeAuthExpired = Boolean(error && error.includes('YouTube authentication has expired'))
  const shouldRenderError = error && !youtubeAuthExpired

  return (
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
          <p className="mb-4 text-base">Your playlist has been successfully migrated to YouTube Music.</p>
          <div className="bg-base-100 p-4 rounded-xl inline-block shadow-soft">
            <p className="font-mono break-all">
              Playlist ID: <span className="font-bold text-secondary">{migrationResult}</span>
            </p>
          </div>
          <p className="mt-4 text-muted-foreground">You can view the new playlist in YouTube Music.</p>
        </div>
      )}

      {shouldRenderError && (
        <div className="mt-6 p-6 rounded-xl bg-gradient-to-r from-error/10 to-red-100 border border-error/30 text-center shadow-soft">
          <h3 className="text-xl font-bold text-error mb-3">Error</h3>
          <p className="break-all text-base">{error}</p>
        </div>
      )}
    </div>
  )
}

export default ProgressCard
