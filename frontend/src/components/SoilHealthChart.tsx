import { GlassCard } from './GlassCard'
import type { SoilHealthResult } from '@/types'
import clsx from 'clsx'

const rows: { key: keyof SoilHealthResult['breakdown']; label: string }[] = [
  { key: 'nitrogen', label: 'Nitrogen' },
  { key: 'phosphorus', label: 'Phosphorus' },
  { key: 'potassium', label: 'Potassium' },
  { key: 'ph', label: 'pH Balance' },
]

function scoreColor(score: number) {
  if (score >= 70) return 'bg-emerald-400'
  if (score >= 40) return 'bg-amber-400'
  return 'bg-rose-400'
}

export function SoilHealthChart({ health }: { health: SoilHealthResult }) {
  return (
    <GlassCard>
      <div className="mb-5 flex items-end justify-between">
        <span className="text-xs uppercase tracking-wider text-white/50">Soil Health</span>
        <span className="text-3xl font-bold text-white">
          {health.score}
          <span className="text-base font-normal text-white/40">/100</span>
        </span>
      </div>

      <div className="space-y-3">
        {rows.map(({ key, label }) => {
          const value = health.breakdown[key]
          return (
            <div key={key}>
              <div className="mb-1 flex justify-between text-xs text-white/60">
                <span>{label}</span>
                <span>{value}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                <div
                  className={clsx('h-full rounded-full transition-all duration-700', scoreColor(value))}
                  style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {health.insights.length > 0 && (
        <div className="mt-5 space-y-1.5 border-t border-white/10 pt-4">
          {health.insights.map((insight) => (
            <p key={insight} className="text-xs text-white/55">
              • {insight}
            </p>
          ))}
        </div>
      )}
    </GlassCard>
  )
}
