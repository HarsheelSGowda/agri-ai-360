import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { GlassCard } from '@/components/GlassCard'
import { createFarm } from '@/services/farmService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import { Loader2 } from 'lucide-react'

const soilTypes = ['Alluvial', 'Black (Regur)', 'Red', 'Laterite', 'Sandy', 'Loamy', 'Clay']

export function FarmCreatePage() {
  const navigate = useNavigate()
  const setActiveFarm = useFarmStore((s) => s.setActiveFarm)
  const [form, setForm] = useState({
    name: '',
    location: '',
    area_acres: '',
    soil_type: soilTypes[0],
    irrigation_available: true,
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const area = Number(form.area_acres)
    if (!Number.isFinite(area) || area <= 0) {
      setError('Enter a valid farm area greater than 0.')
      return
    }
    setLoading(true)
    try {
      const farm = await createFarm({ ...form, area_acres: area })
      setActiveFarm(farm)
      navigate('/app/soil')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <GlassCard>
        <h2 className="text-lg font-semibold text-white">Create Farm</h2>
        <p className="mt-1 text-sm text-white/50">Tell us about your farm so the AI can tailor its recommendations.</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="label-field">Farm Name</label>
            <input required value={form.name} onChange={(e) => update('name', e.target.value)} className="input-field" placeholder="Patil Family Farm" />
          </div>
          <div>
            <label className="label-field">Location</label>
            <input
              required
              value={form.location}
              onChange={(e) => update('location', e.target.value)}
              className="input-field"
              placeholder="Nagpur, Maharashtra"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label-field">Area (acres)</label>
              <input
                type="number"
                step="0.1"
                required
                value={form.area_acres}
                onChange={(e) => update('area_acres', e.target.value)}
                className="input-field"
                placeholder="5.5"
              />
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
          <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
            <input
              type="checkbox"
              checked={form.irrigation_available}
              onChange={(e) => update('irrigation_available', e.target.checked)}
              className="h-4 w-4 accent-emerald-500"
            />
            <span className="text-sm text-white/80">Irrigation available</span>
          </label>

          {error && <p className="rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary w-full py-3 disabled:opacity-60">
            {loading ? <Loader2 size={18} className="animate-spin" /> : 'Create Farm'}
          </button>
        </form>
      </GlassCard>
    </div>
  )
}
