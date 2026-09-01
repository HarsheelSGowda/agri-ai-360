import { AlertTriangle } from 'lucide-react'

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="glass-card flex flex-col items-center gap-3 border-rose-400/20 px-8 py-12 text-center">
      <div className="rounded-2xl bg-rose-400/10 p-3">
        <AlertTriangle size={24} className="text-rose-400" />
      </div>
      <p className="text-sm font-medium text-white/70">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary mt-2 px-4 py-2 text-xs">
          Try again
        </button>
      )}
    </div>
  )
}
