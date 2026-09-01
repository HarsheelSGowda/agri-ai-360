import { useEffect, useState } from 'react'
import { History } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { getHistory } from '@/services/predictionService'
import { apiErrorMessage } from '@/services/api'
import type { PredictionHistoryItem } from '@/types'

export function HistoryPage() {
  const [items, setItems] = useState<PredictionHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getHistory()
      .then((res) => !cancelled && setItems(res))
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <LoadingAnimation label="Loading recommendation history…" />
  if (error) return <ErrorState message={error} />

  if (items.length === 0) {
    return (
      <EmptyState icon={History} title="No history yet" description="Run a crop analysis and it will show up here for future reference." />
    )
  }

  return (
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
  )
}
