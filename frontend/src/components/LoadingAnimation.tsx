import { Sprout } from 'lucide-react'

export function LoadingAnimation({ label = 'AI is analyzing your farm…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="relative flex h-16 w-16 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-emerald-400/20" />
        <span className="absolute inset-2 animate-pulse-glow rounded-full bg-emerald-400/20" />
        <Sprout className="relative z-10 text-emerald-400" size={28} />
      </div>
      <p className="text-sm font-medium text-white/60">{label}</p>
    </div>
  )
}
