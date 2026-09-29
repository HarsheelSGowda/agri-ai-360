import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { CheckCircle2, XCircle, BrainCircuit } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { SHAPChart } from '@/charts/SHAPChart'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { YieldEstimator } from '@/components/YieldEstimator'
import { WaterEstimator } from '@/components/WaterEstimator'
import { FertilizerEstimator } from '@/components/FertilizerEstimator'
import { explainCrop } from '@/services/predictionService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { ExplanationResponse } from '@/types'

const CONDITION_RANGES: Record<string, [number, number]> = {
  temperature: [15, 35],
  humidity: [40, 90],
  rainfall: [50, 300],
  ph: [5.5, 7.5],
}

export function RecommendationDetailPage() {
  const { cropName } = useParams<{ cropName: string }>()
  const lastPrediction = useFarmStore((s) => s.lastPrediction)
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!lastPrediction || !cropName) {
        setLoading(false)
        return
      }
      setLoading(true)
      setError(null)
      try {
        const res = await explainCrop(lastPrediction.input, cropName)
        if (!cancelled) setExplanation(res)
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [cropName, lastPrediction])

  if (!lastPrediction) {
    return (
      <EmptyState
        icon={BrainCircuit}
        title="No recent analysis"
        description="Run a crop analysis first to see a detailed explanation here."
        action={
          <Link to="/app/crop-recommendation" className="btn-primary mt-2 px-5 py-2.5 text-sm">
            Go to Crop Recommendation
          </Link>
        }
      />
    )
  }

  if (loading) return <LoadingAnimation label="Computing SHAP explanation…" />
  if (error) return <ErrorState message={error} />
  if (!explanation) return null

  const conditions = Object.entries(CONDITION_RANGES).map(([key, [min, max]]) => {
    const value = (lastPrediction.input as any)[key]
    const suitable = value >= min && value <= max
    return { key, value, suitable }
  })

  return (
    <div className="space-y-6">
      <GlassCard hover={false}>
        <p className="text-xs uppercase tracking-wider text-white/50">Crop</p>
        <h2 className="mt-1 text-3xl font-bold capitalize text-white">{explanation.crop}</h2>
        <p className="mt-2 text-sm text-white/50">
          Suitability score: <span className="font-mono text-emerald-300">{(explanation.predicted_value * 100).toFixed(1)}%</span>
        </p>
      </GlassCard>

      <GlassCard>
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">Conditions</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {conditions.map(({ key, suitable }) => (
            <div key={key} className="flex items-center gap-2 rounded-xl bg-white/5 p-3">
              {suitable ? (
                <CheckCircle2 size={16} className="text-emerald-400" />
              ) : (
                <XCircle size={16} className="text-rose-400" />
              )}
              <div>
                <p className="text-xs capitalize text-white/70">{key}</p>
                <p className={`text-[11px] ${suitable ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {suitable ? 'Suitable' : 'Marginal'}
                </p>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
          <BrainCircuit size={14} /> Why did AI choose this?
        </div>
        <SHAPChart contributions={explanation.contributions} />
        <p className="mt-4 rounded-xl bg-white/5 p-4 text-sm leading-relaxed text-white/70">{explanation.narrative}</p>
        <p className="mt-3 text-[11px] text-white/30">Powered by Explainable AI (SHAP) · values computed from the trained model, not templated text.</p>
      </GlassCard>

      <FertilizerEstimator
        crop={explanation.crop}
        nitrogen={lastPrediction.input.nitrogen}
        phosphorus={lastPrediction.input.phosphorus}
        potassium={lastPrediction.input.potassium}
        ph={lastPrediction.input.ph}
      />
      <YieldEstimator crop={explanation.crop} />
      <WaterEstimator crop={explanation.crop} />
    </div>
  )
}
