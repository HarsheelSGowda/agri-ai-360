import { useState } from 'react'
import type { FormEvent } from 'react'
import { GlassCard } from '@/components/GlassCard'
import { SoilHealthChart } from '@/components/SoilHealthChart'
import { EmptyState } from '@/components/EmptyState'
import { submitSoil } from '@/services/farmService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { SoilHealthResult } from '@/types'
import { FlaskConical, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

const soilTypes = ['Alluvial', 'Black (Regur)', 'Red', 'Laterite', 'Sandy', 'Loamy', 'Clay']

export function SoilInputPage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [form, setForm] = useState({
    nitrogen: '',
    phosphorus: '',
    potassium: '',
    ph: '',
    soil_type: soilTypes[0],
    organic_carbon: '',
    moisture: '',
    electrical_conductivity: '',
  })
  const [health, setHealth] = useState<SoilHealthResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  if (!activeFarm) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No active farm"
        description="Create a farm first so soil data can be attached to it."
        action={
          <Link to="/app/farms/new" className="btn-primary mt-2 px-5 py-2.5 text-sm">
            Create Farm
          </Link>
        }
      />
    )
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    const n = Number(form.nitrogen)
    const p = Number(form.phosphorus)
    const k = Number(form.potassium)
    const ph = Number(form.ph)

    if ([n, p, k].some((v) => !Number.isFinite(v) || v < 0 || v > 300)) {
      setError('Nitrogen, phosphorus and potassium must be between 0 and 300 (kg/ha).')
      return
    }
    if (!Number.isFinite(ph) || ph < 0 || ph > 14) {
      setError('pH must be between 0 and 14.')
      return
    }

    setLoading(true)
    try {
      const payload: Parameters<typeof submitSoil>[1] = {
        nitrogen: n,
        phosphorus: p,
        potassium: k,
        ph,
        soil_type: form.soil_type,
      }
      if (form.organic_carbon) payload.organic_carbon = Number(form.organic_carbon)
      if (form.moisture) payload.moisture = Number(form.moisture)
      if (form.electrical_conductivity) payload.electrical_conductivity = Number(form.electrical_conductivity)

      const result = await submitSoil(activeFarm.id, payload)
      setHealth(result.health)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <GlassCard>
        <h2 className="text-lg font-semibold text-white">Soil Analysis</h2>
        <p className="mt-1 text-sm text-white/50">Enter your latest soil test values for {activeFarm.name}.</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label-field">Nitrogen (N)</label>
              <input type="number" required value={form.nitrogen} onChange={(e) => update('nitrogen', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="label-field">Phosphorus (P)</label>
              <input type="number" required value={form.phosphorus} onChange={(e) => update('phosphorus', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="label-field">Potassium (K)</label>
              <input type="number" required value={form.potassium} onChange={(e) => update('potassium', e.target.value)} className="input-field" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-field">pH</label>
              <input type="number" step="0.1" required value={form.ph} onChange={(e) => update('ph', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="label-field">Soil Type</label>
              <select value={form.soil_type} onChange={(e) => update('soil_type', e.target.value)} className="input-field">
                {soilTypes.map((s) => (
                  <option key={s} value={s} className="bg-forest-900">
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <p className="pt-2 text-xs uppercase tracking-wider text-white/40">Optional</p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label-field">Organic Carbon</label>
              <input type="number" step="0.1" value={form.organic_carbon} onChange={(e) => update('organic_carbon', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="label-field">Moisture %</label>
              <input type="number" step="0.1" value={form.moisture} onChange={(e) => update('moisture', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="label-field">EC (dS/m)</label>
              <input type="number" step="0.1" value={form.electrical_conductivity} onChange={(e) => update('electrical_conductivity', e.target.value)} className="input-field" />
            </div>
          </div>

          {error && <p className="rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary w-full py-3 disabled:opacity-60">
            {loading ? <Loader2 size={18} className="animate-spin" /> : 'Analyze Soil'}
          </button>
        </form>
      </GlassCard>

      {health ? (
        <SoilHealthChart health={health} />
      ) : (
        <EmptyState icon={FlaskConical} title="No soil analysis yet" description="Submit the form to see your soil health breakdown." />
      )}
    </div>
  )
}
