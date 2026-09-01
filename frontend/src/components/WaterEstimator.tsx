import { useEffect, useState } from 'react'
import { Droplets, Loader2 } from 'lucide-react'
import { GlassCard } from './GlassCard'
import { getWaterOptions, predictWater } from '@/services/waterService'
import { getWeather } from '@/services/weatherService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { WaterOptionsResponse, WaterRequirementResponse } from '@/types'

function guessState(location: string | undefined, states: string[]): string {
  if (!location) return ''
  const lower = location.toLowerCase()
  return states.find((s) => lower.includes(s.toLowerCase())) ?? ''
}

export function WaterEstimator({ crop }: { crop: string }) {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [options, setOptions] = useState<WaterOptionsResponse | null>(null)
  const [state, setState] = useState('')
  const [temperature, setTemperature] = useState('')
  const [rainfall, setRainfall] = useState('')
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [result, setResult] = useState<WaterRequirementResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([getWaterOptions(), getWeather(activeFarm?.location)])
      .then(([optRes, weatherRes]) => {
        if (cancelled) return
        setOptions(optRes)
        setState((prev) => prev || guessState(activeFarm?.location, optRes.states))
        setTemperature((prev) => prev || String(weatherRes.temperature_c))
        setRainfall((prev) => prev || String(weatherRes.rainfall_mm))
      })
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setOptionsLoading(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (optionsLoading) {
    return (
      <GlassCard>
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
          <Droplets size={14} /> Water Requirement
        </div>
        <p className="mt-3 text-sm text-white/40">Loading water model…</p>
      </GlassCard>
    )
  }

  const isSupported = options?.supported_crops.includes(crop.toLowerCase())

  if (!isSupported) {
    return (
      <GlassCard>
        <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
          <Droplets size={14} /> Water Requirement
        </div>
        <p className="text-sm text-white/50">
          No FAO-56 crop-coefficient data is available for <span className="capitalize text-white/70">{crop}</span> yet. Supported crops:{' '}
          {options?.supported_crops.join(', ') || 'none available yet'}.
        </p>
      </GlassCard>
    )
  }

  const handleEstimate = async () => {
    const temp = Number(temperature)
    const rain = Number(rainfall)
    if (!state) {
      setError('Select a state.')
      return
    }
    if (!Number.isFinite(temp) || !Number.isFinite(rain) || rain < 0) {
      setError('Enter a valid temperature and rainfall.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await predictWater(crop, state, temp, rain, activeFarm?.area_acres, activeFarm?.id)
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
        <Droplets size={14} /> Water Requirement
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="label-field">State</label>
          <select value={state} onChange={(e) => setState(e.target.value)} className="input-field">
            <option value="" className="bg-forest-900">
              Select state
            </option>
            {options?.states.map((s) => (
              <option key={s} value={s} className="bg-forest-900">
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label-field">Temp °C</label>
          <input type="number" value={temperature} onChange={(e) => setTemperature(e.target.value)} className="input-field" />
        </div>
        <div>
          <label className="label-field">Rainfall mm</label>
          <input type="number" min="0" value={rainfall} onChange={(e) => setRainfall(e.target.value)} className="input-field" />
        </div>
      </div>

      {error && <p className="mt-3 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

      <button onClick={handleEstimate} disabled={loading} className="btn-secondary mt-4 w-full py-2.5 text-sm disabled:opacity-60">
        {loading ? <Loader2 size={16} className="animate-spin" /> : 'Estimate Water Requirement'}
      </button>

      {result?.supported && (
        <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-sky-300">{result.net_irrigation_mm_per_day}</span>
            <span className="text-sm text-white/50">mm/day net irrigation</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-lg bg-white/5 py-2">
              <p className="text-white/40">Crop Water Use</p>
              <p className="font-semibold text-white">{result.crop_water_use_mm_per_day} mm/d</p>
            </div>
            <div className="rounded-lg bg-white/5 py-2">
              <p className="text-white/40">Effective Rain</p>
              <p className="font-semibold text-white">{result.effective_rainfall_mm_per_day} mm/d</p>
            </div>
            <div className="rounded-lg bg-white/5 py-2">
              <p className="text-white/40">Liters / acre / day</p>
              <p className="font-semibold text-white">{result.net_irrigation_liters_per_acre_per_day?.toLocaleString('en-IN')}</p>
            </div>
          </div>
          {result.net_irrigation_liters_total_per_day !== null && (
            <p className="text-xs text-white/50">
              Farm total: <span className="font-semibold text-white">{result.net_irrigation_liters_total_per_day.toLocaleString('en-IN')} L/day</span>
            </p>
          )}
          <p className="text-[11px] text-white/30">
            Reference ET₀ = {result.reference_et0_mm_per_day} mm/d (FAO Blaney-Criddle, {result.state} ≈ {result.latitude_deg}°N,{' '}
            {result.month}) × Kc<sub>mid</sub> {result.kc_mid} ({result.kc_category === 'generic_legume' ? 'generic legume/pulse estimate' : result.kc_source_row}
            , FAO-56 Table 12) − effective rainfall. A planning-level estimate, not a substitute for local agronomic advice.
          </p>
        </div>
      )}

      {result && !result.supported && result.reason && (
        <p className="mt-4 rounded-lg bg-amber-400/10 px-3 py-2 text-sm text-amber-300">{result.reason}</p>
      )}
    </GlassCard>
  )
}
