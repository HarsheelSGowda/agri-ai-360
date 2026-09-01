import { useEffect, useState } from 'react'
import { Sprout, Zap } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { AIRecommendationCard } from '@/components/AIRecommendationCard'
import { CropRanking } from '@/components/CropRanking'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { predictTopCrops } from '@/services/predictionService'
import { getSoil } from '@/services/farmService'
import { getWeather } from '@/services/weatherService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { CropPredictionInput, TopCropsResponse } from '@/types'

const defaultInput: CropPredictionInput = {
  nitrogen: 90,
  phosphorus: 42,
  potassium: 43,
  temperature: 25,
  humidity: 70,
  ph: 6.5,
  rainfall: 200,
}

export function CropRecommendationPage() {
  const { activeFarm, setLastPrediction } = useFarmStore()
  const [input, setInput] = useState<CropPredictionInput>(defaultInput)
  const [result, setResult] = useState<TopCropsResponse | null>(null)
  const [before, setBefore] = useState<TopCropsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [prefillLoading, setPrefillLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function prefill() {
      setPrefillLoading(true)
      try {
        const [soil, weather] = await Promise.all([
          activeFarm ? getSoil(activeFarm.id).catch(() => null) : Promise.resolve(null),
          getWeather(activeFarm?.location).catch(() => null),
        ])
        if (cancelled) return
        setInput((prev) => ({
          ...prev,
          nitrogen: soil?.nitrogen ?? prev.nitrogen,
          phosphorus: soil?.phosphorus ?? prev.phosphorus,
          potassium: soil?.potassium ?? prev.potassium,
          ph: soil?.ph ?? prev.ph,
          temperature: weather?.temperature_c ?? prev.temperature,
          humidity: weather?.humidity_pct ?? prev.humidity,
          rainfall: weather?.rainfall_mm ? weather.rainfall_mm * 40 : prev.rainfall,
        }))
      } finally {
        if (!cancelled) setPrefillLoading(false)
      }
    }
    prefill()
    return () => {
      cancelled = true
    }
  }, [activeFarm])

  function update(key: keyof CropPredictionInput, value: number) {
    setInput((prev) => ({ ...prev, [key]: value }))
  }

  async function runAnalysis() {
    setLoading(true)
    setError(null)
    setBefore(null)
    try {
      const res = await predictTopCrops(input, activeFarm?.id)
      setResult(res)
      setLastPrediction(res)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function runSimulation() {
    if (!result) return
    setSimulating(true)
    setError(null)
    try {
      setBefore(result)
      const res = await predictTopCrops(input, activeFarm?.id)
      setResult(res)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSimulating(false)
    }
  }

  return (
    <div className="space-y-8">
      <GlassCard>
        <div className="mb-5 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
          <Sprout size={14} /> Crop Recommendation Inputs
          {prefillLoading && <span className="text-white/30">(loading farm data…)</span>}
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-7">
          <NumberField label="N" value={input.nitrogen} onChange={(v) => update('nitrogen', v)} min={0} max={300} />
          <NumberField label="P" value={input.phosphorus} onChange={(v) => update('phosphorus', v)} min={0} max={300} />
          <NumberField label="K" value={input.potassium} onChange={(v) => update('potassium', v)} min={0} max={300} />
          <NumberField label="Temp °C" value={input.temperature} onChange={(v) => update('temperature', v)} min={-10} max={55} step={0.1} />
          <NumberField label="Humidity %" value={input.humidity} onChange={(v) => update('humidity', v)} min={0} max={100} step={0.1} />
          <NumberField label="pH" value={input.ph} onChange={(v) => update('ph', v)} min={0} max={14} step={0.1} />
          <NumberField label="Rainfall mm" value={input.rainfall} onChange={(v) => update('rainfall', v)} min={0} max={3000} step={0.1} />
        </div>
        <div className="mt-6 flex gap-3">
          <button onClick={runAnalysis} disabled={loading} className="btn-primary px-6 py-3 disabled:opacity-60">
            {loading ? 'Analyzing…' : 'Analyze Farm'}
          </button>
          {result && (
            <button onClick={runSimulation} disabled={simulating} className="btn-secondary px-6 py-3 disabled:opacity-60">
              <Zap size={16} /> {simulating ? 'Simulating…' : 'Simulate (What-If AI)'}
            </button>
          )}
        </div>
      </GlassCard>

      {error && <ErrorState message={error} onRetry={runAnalysis} />}
      {loading && <LoadingAnimation label="AI is analyzing soil, weather and environmental data…" />}

      {result && !loading && (
        <div className="space-y-6">
          <AIRecommendationCard top={result.top_crops[0]} />

          {before && (
            <div className="grid gap-4 md:grid-cols-2">
              <GlassCard hover={false} className="border-white/10">
                <p className="mb-3 text-xs uppercase tracking-wider text-white/40">Before</p>
                <CropRanking crops={before.top_crops.slice(0, 3)} />
              </GlassCard>
              <GlassCard hover={false} className="border-emerald-400/20">
                <p className="mb-3 text-xs uppercase tracking-wider text-emerald-300/70">After</p>
                <CropRanking crops={result.top_crops.slice(0, 3)} />
              </GlassCard>
            </div>
          )}

          <GlassCard>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">Top 5 AI Recommendations</h3>
            <CropRanking crops={result.top_crops} />
            <p className="mt-4 text-[11px] text-white/30">
              Model: {result.model_used} ({result.model_version}) · Probabilities are direct model output, not guaranteed real-world outcomes.
            </p>
          </GlassCard>
        </div>
      )}
    </div>
  )
}

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min: number
  max: number
  step?: number
}) {
  return (
    <div>
      <label className="label-field">{label}</label>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="input-field"
      />
    </div>
  )
}
