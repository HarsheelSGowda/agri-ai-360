import { GlassCard } from '@/components/GlassCard'
import clsx from 'clsx'

const phases = [
  {
    title: 'Phase 1 — Current',
    tone: 'emerald',
    items: [
      { label: 'Crop Recommendation', done: true },
      { label: 'Soil Intelligence', done: true },
      { label: 'Weather Intelligence', done: true },
      { label: 'Explainable AI', done: true },
      { label: 'Farmer Dashboard', done: true },
    ],
  },
  {
    title: 'Phase 2',
    tone: 'amber',
    items: [
      { label: 'Yield Prediction', done: true },
      { label: 'Profit Prediction', done: true },
      { label: 'Water Intelligence', done: true },
      { label: 'Risk Prediction (ML-based)', done: true },
    ],
  },
  {
    title: 'Phase 3',
    tone: 'sky',
    items: [
      { label: 'Disease Detection', done: true },
      { label: 'AI Agriculture Assistant', done: false },
      { label: 'Voice Assistant', done: false },
      { label: 'Multilingual AI', done: false },
    ],
  },
  {
    title: 'Phase 4',
    tone: 'lime',
    items: [
      { label: 'Satellite Monitoring', done: false },
      { label: 'NDVI', done: false },
      { label: 'IoT Sensor Integration', done: false },
    ],
  },
]

const toneClasses: Record<string, string> = {
  emerald: 'border-emerald-400/20',
  amber: 'border-amber-400/20',
  sky: 'border-sky-400/20',
  lime: 'border-lime-400/20',
}

export function RoadmapPage() {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {phases.map((phase) => (
        <GlassCard key={phase.title} hover={false} className={clsx('border', toneClasses[phase.tone])}>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/70">{phase.title}</h3>
          <ul className="space-y-2">
            {phase.items.map((item) => (
              <li key={item.label} className="flex items-center gap-2 text-sm text-white/70">
                <span>{item.done ? '✅' : phase.title === 'Phase 4' ? '🚀' : '🔄'}</span>
                {item.label}
              </li>
            ))}
          </ul>
        </GlassCard>
      ))}
    </div>
  )
}
