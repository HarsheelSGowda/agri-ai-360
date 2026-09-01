import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="glass-card flex flex-col items-center gap-3 px-8 py-16 text-center">
      <div className="rounded-2xl bg-white/5 p-4">
        <Icon size={28} className="text-white/40" />
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="max-w-sm text-sm text-white/50">{description}</p>
      {action}
    </div>
  )
}
