import { GlassCard } from './GlassCard'
import type { RiskBreakdown } from '@/types'
import clsx from 'clsx'

const toneMap: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
  MEDIUM: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
  HIGH: 'text-rose-400 bg-rose-400/10 border-rose-400/30',
}

const rows: { key: keyof Pick<RiskBreakdown, 'weather_risk' | 'soil_risk' | 'water_risk' | 'disease_risk'>; label: string }[] = [
  { key: 'weather_risk', label: 'Weather Risk' },
  { key: 'soil_risk', label: 'Soil Risk' },
  { key: 'water_risk', label: 'Water Risk' },
  { key: 'disease_risk', label: 'Disease Risk' },
]

export function RiskCard({ risk }: { risk: RiskBreakdown }) {
  return (
    <GlassCard>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-white/50">Farm Risk</span>
        {risk.is_prototype && (
          <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
            PROTOTYPE ASSESSMENT
          </span>
        )}
      </div>
      <span className={clsx('mb-5 mt-2 inline-block rounded-lg border px-3 py-1 text-2xl font-bold', toneMap[risk.overall])}>
        {risk.overall}
      </span>

      <div className="grid grid-cols-2 gap-3">
        {rows.map(({ key, label }) => (
          <div key={key} className="rounded-xl bg-white/5 p-3">
            <p className="text-[10px] uppercase tracking-wider text-white/40">{label}</p>
            <p className={clsx('mt-1 text-sm font-semibold', toneMap[risk[key]].split(' ')[0])}>{risk[key]}</p>
          </div>
        ))}
      </div>

      {risk.notes.length > 0 && (
        <div className="mt-4 space-y-1 border-t border-white/10 pt-3">
          {risk.notes.map((n) => (
            <p key={n} className="text-xs text-white/50">
              • {n}
            </p>
          ))}
        </div>
      )}
    </GlassCard>
  )
}
