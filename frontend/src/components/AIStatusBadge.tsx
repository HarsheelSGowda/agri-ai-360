interface AIStatusBadgeProps {
  online: boolean
  modelName?: string
}

export function AIStatusBadge({ online, modelName }: AIStatusBadgeProps) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${online ? 'bg-emerald-400 animate-pulse-glow' : 'bg-rose-400'}`} />
      <span className="font-medium text-white/80">{online ? 'AI ENGINE ONLINE' : 'AI ENGINE OFFLINE'}</span>
      {modelName && <span className="text-white/40">· {modelName}</span>}
    </div>
  )
}
