import { useEffect, useState } from 'react'
import { Beaker, Loader2, AlertTriangle } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { getFertilizerOptions, recommendFertilizer } from '@/services/fertilizerService'
import { getSoil } from '@/services/farmService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { FertilizerOptionsResponse, FertilizerRecommendationResponse } from '@/types'

const STATUS_STYLE: Record<string, string> = {
  DEFICIENT: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
  EXCESS: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  ADEQUATE: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
}

export function FertilizerAdvisorPage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [options, setOptions] = useState<FertilizerOptionsResponse | null>(null)
  const [form, setForm] = useState({
    crop: '',
    nitrogen: '90',
    phosphorus: '42',
    potassium: '43',
    ph: '6.5',
    growth_stage: 'vegetative',
    organic_carbon: '',
    moisture: '',
  })
  const [result, setResult] = useState<FertilizerRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getFertilizerOptions()
      .then(setOptions)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!activeFarm) return
    getSoil(activeFarm.id)
      .then((soil) => {
        if (!soil) return
        setForm((f) => ({
          ...f,
          nitrogen: String(soil.nitrogen),
          phosphorus: String(soil.phosphorus),
          potassium: String(soil.potassium),
          ph: String(soil.ph),
          organic_carbon: soil.organic_carbon != null ? String(soil.organic_carbon) : f.organic_carbon,
          moisture: soil.moisture != null ? String(soil.moisture) : f.moisture,
        }))
      })
      .catch(() => {})
  }, [activeFarm])

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit() {
    if (!form.crop.trim()) {
      setError('Enter a crop name.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await recommendFertilizer({
        crop: form.crop.trim(),
        nitrogen: Number(form.nitrogen),
        phosphorus: Number(form.phosphorus),
        potassium: Number(form.potassium),
        ph: Number(form.ph),
        growth_stage: form.growth_stage,
        organic_carbon: form.organic_carbon ? Number(form.organic_carbon) : undefined,
        moisture: form.moisture ? Number(form.moisture) : undefined,
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
    <div className="mx-auto max-w-2xl space-y-6">
      <GlassCard hover={false}>
        <div className="mb-4 flex items-center gap-2">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-lime-400/10 text-lime-400">
            <Beaker size={20} />
          </span>
          <div>
            <h2 className="text-lg font-semibold text-white">Fertilizer Advisor</h2>
            <p className="text-xs text-white/45">Rule-based nutrient deficiency &amp; application guidance — not a calibrated dosage prescription.</p>
          </div>
        </div>

        {activeFarm && <p className="mb-4 text-xs text-white/40">Prefilled from {activeFarm.name}'s latest soil record where available.</p>}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div className="col-span-2 sm:col-span-1">
            <label className="label-field">Crop</label>
            <input value={form.crop} onChange={(e) => update('crop', e.target.value)} placeholder="e.g. rice" className="input-field" />
          </div>
          <div>
            <label className="label-field">Growth stage</label>
            <select value={form.growth_stage} onChange={(e) => update('growth_stage', e.target.value)} className="input-field capitalize">
              {(options?.growth_stages ?? ['seedling', 'vegetative', 'flowering', 'fruiting', 'maturity']).map((s) => (
                <option key={s} value={s} className="bg-forest-900 capitalize">
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label-field">Nitrogen (N)</label>
            <input type="number" value={form.nitrogen} onChange={(e) => update('nitrogen', e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-field">Phosphorus (P)</label>
            <input type="number" value={form.phosphorus} onChange={(e) => update('phosphorus', e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-field">Potassium (K)</label>
            <input type="number" value={form.potassium} onChange={(e) => update('potassium', e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-field">pH</label>
            <input type="number" step="0.1" value={form.ph} onChange={(e) => update('ph', e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-field">Organic carbon % (optional)</label>
            <input type="number" step="0.1" value={form.organic_carbon} onChange={(e) => update('organic_carbon', e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-field">Moisture % (optional)</label>
            <input type="number" value={form.moisture} onChange={(e) => update('moisture', e.target.value)} className="input-field" />
          </div>
        </div>

        {error && <p className="mt-4 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

        <button onClick={handleSubmit} disabled={loading} className="btn-primary mt-5 w-full py-3 text-sm disabled:opacity-60">
          {loading ? <Loader2 size={18} className="animate-spin" /> : 'Get Fertilizer Recommendation'}
        </button>
      </GlassCard>

      {result && (
        <GlassCard hover={false}>
          <h3 className="mb-4 text-xs uppercase tracking-wider text-white/50">Recommendation for {result.crop}</h3>

          <div className="grid grid-cols-3 gap-2">
            {result.deficiencies.map((d) => (
              <div key={d.nutrient} className={`rounded-lg border p-3 text-center ${STATUS_STYLE[d.status]}`}>
                <p className="text-[10px] uppercase tracking-wide opacity-80">{d.nutrient}</p>
                <p className="text-sm font-semibold">{d.status}</p>
                <p className="text-[10px] opacity-70">
                  {d.current_value} (opt {d.optimal_range})
                </p>
              </div>
            ))}
          </div>

          {result.deficiencies.some((d) => d.recommended_category) && (
            <ul className="mt-4 space-y-1 text-sm text-white/70">
              {result.deficiencies
                .filter((d) => d.recommended_category)
                .map((d) => (
                  <li key={d.nutrient} className="flex gap-2">
                    <span className="text-emerald-400/70">•</span> {d.recommended_category}
                  </li>
                ))}
            </ul>
          )}

          <p className="mt-4 text-sm text-white/60">{result.application_timing}</p>

          {result.organic_matter_guidance && <p className="mt-2 text-sm text-white/60">{result.organic_matter_guidance}</p>}

          {result.warnings.length > 0 && (
            <div className="mt-4 space-y-1.5">
              {result.warnings.map((w, i) => (
                <p key={i} className="flex items-start gap-1.5 rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-300">
                  <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {w}
                </p>
              ))}
            </div>
          )}

          <p className="mt-4 text-[11px] text-white/30">{result.disclaimer}</p>
        </GlassCard>
      )}
    </div>
  )
}
