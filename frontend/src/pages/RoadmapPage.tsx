import { GlassCard } from '@/components/GlassCard'
import clsx from 'clsx'

type Status = 'done' | 'architecture' | 'planned'

const phases: { title: string; tone: string; items: { label: string; status: Status }[] }[] = [
  {
    title: 'Phase 1 — Current',
    tone: 'emerald',
    items: [
      { label: 'Crop Recommendation', status: 'done' },
      { label: 'Soil Intelligence', status: 'done' },
      { label: 'Weather Intelligence', status: 'done' },
      { label: 'Explainable AI', status: 'done' },
      { label: 'Farmer Dashboard', status: 'done' },
    ],
  },
  {
    title: 'Phase 2',
    tone: 'amber',
    items: [
      { label: 'Yield Prediction', status: 'done' },
      { label: 'Profit Prediction', status: 'done' },
      { label: 'Water Intelligence', status: 'done' },
      { label: 'Risk Prediction (ML-based)', status: 'done' },
      { label: 'Fertilizer Advisor', status: 'done' },
      { label: 'Market Price Intelligence', status: 'done' },
      { label: 'Personalized Notifications', status: 'done' },
    ],
  },
  {
    title: 'Phase 3',
    tone: 'sky',
    items: [
      { label: 'Disease Detection', status: 'done' },
      { label: 'AI Agriculture Assistant (rule-based)', status: 'done' },
      { label: 'AI Assistant with a real LLM/RAG backend', status: 'planned' },
      { label: 'Voice Assistant', status: 'planned' },
      { label: 'Multilingual AI', status: 'planned' },
    ],
  },
  {
    title: 'Phase 4',
    tone: 'lime',
    items: [
      { label: 'Satellite Monitoring — planned/integration-ready architecture', status: 'architecture' },
      { label: 'NDVI — live provider', status: 'planned' },
      { label: 'IoT Sensor Integration — real ingestion + demo data', status: 'architecture' },
      { label: 'IoT with real connected sensors', status: 'planned' },
    ],
  },
]

const toneClasses: Record<string, string> = {
  emerald: 'border-emerald-400/20',
  amber: 'border-amber-400/20',
  sky: 'border-sky-400/20',
  lime: 'border-lime-400/20',
}

const statusIcon: Record<Status, string> = {
  done: '✅',
  architecture: '🏗️',
  planned: '🔄',
}

export function RoadmapPage() {
  return (
    <div className="space-y-4">
      <p className="text-xs text-white/40">
        🏗️ = the real backend/DB architecture exists and works today, but the feature is honestly
        labeled for what it is (e.g. "planned" satellite status, "demo simulation" sensor data) —
        see the AI Roadmap notes on each module's page for details.
      </p>
      <div className="grid gap-5 sm:grid-cols-2">
        {phases.map((phase) => (
          <GlassCard key={phase.title} hover={false} className={clsx('border', toneClasses[phase.tone])}>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/70">{phase.title}</h3>
            <ul className="space-y-2">
              {phase.items.map((item) => (
                <li key={item.label} className="flex items-center gap-2 text-sm text-white/70">
                  <span>{statusIcon[item.status]}</span>
                  {item.label}
                </li>
              ))}
            </ul>
          </GlassCard>
        ))}
      </div>
    </div>
  )
}
