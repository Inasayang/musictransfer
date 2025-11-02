interface AuthAction {
  label: string
  onClick: () => void
  variant: 'primary' | 'secondary' | 'destructive'
}

export interface AuthProviderConfig {
  id: 'spotify' | 'youtube'
  name: string
  connected: boolean
  actions: AuthAction[]
}

interface AuthenticationCardProps {
  providers: AuthProviderConfig[]
}

const AuthenticationCard = ({ providers }: AuthenticationCardProps) => {
  return (
    <div className="card p-8 shadow-soft hover:shadow-soft-xl transition-all duration-500 transform hover:-translate-y-1">
      <h2 className="text-lg font-bold mb-6">Platform Authentication</h2>
      <div className="space-y-5">
        {providers.map((provider) => {
          const statusLabel = provider.connected ? 'Connected' : 'Not Authenticated'

          return (
            <div
              key={provider.id}
              className="flex items-center justify-between p-5 rounded-xl transition-all duration-300 hover:shadow-soft-lg"
            >
              <div className="flex items-center space-x-4">
                <div className={`w-4 h-4 rounded-full ${provider.connected ? 'bg-success animate-pulse' : 'bg-error'}`}></div>
                <div>
                  <h3 className="font-semibold text-base">{provider.name}</h3>
                  <p className="text-sm text-muted-foreground">{statusLabel}</p>
                </div>
              </div>
              <div className="flex space-x-2">
                {provider.actions.map((action) => (
                  <button
                    key={action.label}
                    onClick={action.onClick}
                    className={`btn btn-${action.variant} btn-sm`}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AuthenticationCard
