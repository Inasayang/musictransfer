interface AppHeaderProps {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}

const AppHeader = ({ theme, onToggleTheme }: AppHeaderProps) => {
  return (
    <header className="border-b border-base-300 bg-base-100 sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-primary to-accent flex items-center justify-center shadow-soft">
              <span className="font-bold text-lg" style={{ color: 'hsl(var(--primary-foreground))' }}>
                MT
              </span>
            </div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
              MusicTransfer
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={onToggleTheme}
              className="p-2 rounded-xl hover:bg-base-200 transition-all duration-300 transform hover:scale-105"
              aria-label="Toggle theme"
            >
              {theme === 'light' ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 3v1m0 16v1m9-9h1M3 12H2m15.325-6.675l-.707-.707M6.343 17.657l-.707-.707M16.95 16.95l.707.707M6.343 6.343l-.707-.707M12 7a5 5 0 110 10 5 5 0 010-10z"
                  />
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
  )
}

export default AppHeader
