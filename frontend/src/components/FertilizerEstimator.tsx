import { useEffect, useState } from 'react'
import { Beaker, Loader2, AlertTriangle } from 'lucide-react'
import { GlassCard } from './GlassCard'
import { getFertilizerOptions, recommendFertilizer } from '@/services/fertilizerService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { FertilizerOptionsResponse, FertilizerRecommendationResponse } from '@/types'

const STATUS_STYLE: Record<string, string> = {
  DEFICIENT: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
  EXCESS: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  ADEQUATE: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
}

interface Props {
  crop: string
  nitrogen: number
  phosphorus: number
  potassium: number
  ph: number
}

export function FertilizerEstimator({ crop, nitrogen, phosphorus, potassium, ph }: Props) {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [options, setOptions] = useState<FertilizerOptionsResponse | null>(null)
  const [growthStage, setGrowthStage] = useState('vegetative')
  const [result, setResult] = useState<FertilizerRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getFertilizerOptions()
      .then((res) => {
        setOptions(res)
        if (res.growth_stages.length) setGrowthStage((prev) => (res.growth_stages.includes(prev) ? prev : res.growth_stages[0]))
      })
      .catch(() => {})
  }, [])

  const handleRecommend = async () => {
    setError(null)
    setLoading(true)
    try {
      const res = await recommendFertilizer({
        crop,
        nitrogen,
        phosphorus,
        potassium,
        ph,
        growth_stage: growthStage,
        farm_area_acres: activeFarm?.area_acres,
        farm_id: activeFarm?.id ?? null,
      })
      setResult(res)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassCard>
      <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
        <Beaker size={14} /> Fertilizer Recommendation
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="label-field">Growth stage</label>
          <select value={growthStage} onChange={(e) => setGrowthStage(e.target.value)} className="input-field capitalize">
            {(options?.growth_stages ?? ['vegetative']).map((s) => (
              <option key={s} value={s} className="bg-forest-900 capitalize">
                {s}
              </option>
            ))}
          </select>
        </div>
        <button onClick={handleRecommend} disabled={loading} className="btn-secondary px-5 py-2.5 text-sm disabled:opacity-60">
          {loading ? <Loader2 size={16} className="animate-spin" /> : 'Get Recommendation'}
        </button>
      </div>

      {error && <p className="mt-3 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

      {result && (
        <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
          <div className="grid grid-cols-3 gap-2">
            {result.deficiencies.map((d) => (
              <div key={d.nutrient} className={`rounded-lg border p-2.5 text-center ${STATUS_STYLE[d.status]}`}>
                <p className="text-[10px] uppercase tracking-wide opacity-80">{d.nutrient}</p>
                <p className="text-sm font-semibold">{d.status}</p>
                <p className="text-[10px] opacity-70">
                  {d.current_value} (opt {d.optimal_range})
                </p>
              </div>
            ))}
          </div>

          {result.deficiencies.some((d) => d.recommended_category) && (
            <ul className="space-y-1 text-sm text-white/70">
              {result.deficiencies
                .filter((d) => d.recommended_category)
                .map((d) => (
                  <li key={d.nutrient} className="flex gap-2">
                    <span className="text-emerald-400/70">•</span> {d.recommended_category}
                  </li>
                ))}
            </ul>
          )}

          <p className="text-sm text-white/60">{result.application_timing}</p>

          {result.organic_matter_guidance && <p className="text-sm text-white/60">{result.organic_matter_guidance}</p>}

          {result.warnings.length > 0 && (
            <div className="space-y-1.5">
              {result.warnings.map((w, i) => (
                <p key={i} className="flex items-start gap-1.5 rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-300">
                  <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {w}
                </p>
              ))}
            </div>
          )}

          <p className="text-[11px] text-white/30">{result.disclaimer}</p>
        </div>
      )}
    </GlassCard>
  )
}
