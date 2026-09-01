import type { LucideIcon } from 'lucide-react'
import { GlassCard } from './GlassCard'
import clsx from 'clsx'

interface MetricCardProps {
  label: string
  value: string
  subtext?: string
  icon: LucideIcon
  tone?: 'emerald' | 'lime' | 'amber' | 'rose' | 'sky'
}

const toneMap: Record<NonNullable<MetricCardProps['tone']>, string> = {
  emerald: 'text-emerald-400 bg-emerald-400/10',
  lime: 'text-lime-400 bg-lime-400/10',
  amber: 'text-amber-400 bg-amber-400/10',
  rose: 'text-rose-400 bg-rose-400/10',
  sky: 'text-sky-400 bg-sky-400/10',
}

export function MetricCard({ label, value, subtext, icon: Icon, tone = 'emerald' }: MetricCardProps) {
  return (
    <GlassCard className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="label-field">{label}</span>
        <span className={clsx('rounded-lg p-2', toneMap[tone])}>
          <Icon size={18} strokeWidth={2} />
        </span>
      </div>
      <div>
        <p className="text-3xl font-semibold tracking-tight text-white">{value}</p>
        {subtext && <p className="mt-1 text-xs text-white/45">{subtext}</p>}
      </div>
    </GlassCard>
  )
}
