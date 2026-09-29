import { useEffect, useState } from 'react'
import { History, Stethoscope, CheckCircle2, AlertTriangle } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { getHistory } from '@/services/predictionService'
import { getDiseaseHistory } from '@/services/diseaseService'
import { apiErrorMessage } from '@/services/api'
import type { DiseaseHistoryItem, PredictionHistoryItem } from '@/types'

type Tab = 'crop' | 'disease'

export function HistoryPage() {
  const [tab, setTab] = useState<Tab>('crop')
  const [items, setItems] = useState<PredictionHistoryItem[]>([])
  const [diseaseItems, setDiseaseItems] = useState<DiseaseHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([getHistory(), getDiseaseHistory()])
      .then(([crop, disease]) => {
        if (cancelled) return
        setItems(crop)
        setDiseaseItems(disease)
      })
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <LoadingAnimation label="Loading history…" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => setTab('crop')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            tab === 'crop' ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/20' : 'text-white/50 hover:text-white'
          }`}
        >
          Crop Recommendations ({items.length})
        </button>
        <button
          onClick={() => setTab('disease')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            tab === 'disease' ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/20' : 'text-white/50 hover:text-white'
          }`}
        >
          Disease Diagnoses ({diseaseItems.length})
        </button>
      </div>

      {tab === 'crop' &&
        (items.length === 0 ? (
          <EmptyState icon={History} title="No history yet" description="Run a crop analysis and it will show up here for future reference." />
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <GlassCard key={item.id} className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="font-semibold capitalize text-white">{item.crop}</p>
                  <p className="text-xs text-white/40">
                    {item.farm_name} · {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1 text-xs text-white/50">
                  <span className="font-mono text-emerald-300">{(item.score * 100).toFixed(1)}%</span>
                  <span>{item.soil_summary}</span>
                  <span>{item.weather_summary}</span>
                </div>
              </GlassCard>
            ))}
          </div>
        ))}

      {tab === 'disease' &&
        (diseaseItems.length === 0 ? (
          <EmptyState
            icon={Stethoscope}
            title="No diagnoses yet"
            description="Diagnose a leaf photo on the Crop Doctor page (with an active farm selected) and it will show up here."
          />
        ) : (
          <div className="space-y-3">
            {diseaseItems.map((item) => (
              <GlassCard key={item.id} className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  {item.is_healthy ? (
                    <CheckCircle2 size={20} className="text-emerald-400" />
                  ) : (
                    <AlertTriangle size={20} className="text-amber-400" />
                  )}
                  <div>
                    <p className="font-semibold capitalize text-white">
                      {item.crop} — {item.condition}
                    </p>
                    <p className="text-xs text-white/40">
                      {item.farm_name} · {new Date(item.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 text-xs text-white/50">
                  <span className="font-mono text-emerald-300">{(item.probability * 100).toFixed(1)}%</span>
                  <span>{item.model_used}</span>
                </div>
              </GlassCard>
            ))}
          </div>
        ))}
    </div>
  )
}
