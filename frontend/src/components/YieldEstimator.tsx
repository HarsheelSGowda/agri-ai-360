import { useEffect, useState } from 'react'
import { TrendingUp, Loader2, IndianRupee, ShieldAlert } from 'lucide-react'
import { GlassCard } from './GlassCard'
import { getYieldOptions, predictYield } from '@/services/yieldService'
import { getProfitOptions, predictProfit } from '@/services/profitService'
import { getYieldRiskOptions, predictYieldRisk } from '@/services/riskMlService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type {
  ProfitOptionsResponse,
  ProfitPredictionResponse,
  YieldOptionsResponse,
  YieldPredictionResponse,
  YieldRiskOptionsResponse,
  YieldRiskResponse,
} from '@/types'
import clsx from 'clsx'

function guessState(location: string | undefined, states: string[]): string {
  if (!location) return ''
  const lower = location.toLowerCase()
  return states.find((s) => lower.includes(s.toLowerCase())) ?? ''
}

export function YieldEstimator({ crop }: { crop: string }) {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [options, setOptions] = useState<YieldOptionsResponse | null>(null)
  const [profitOptions, setProfitOptions] = useState<ProfitOptionsResponse | null>(null)
  const [state, setState] = useState('')
  const [season, setSeason] = useState('')
  const [result, setResult] = useState<YieldPredictionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [costPerAcre, setCostPerAcre] = useState('')
  const [profitResult, setProfitResult] = useState<ProfitPredictionResponse | null>(null)
  const [profitLoading, setProfitLoading] = useState(false)
  const [profitError, setProfitError] = useState<string | null>(null)

  const [riskOptions, setRiskOptions] = useState<YieldRiskOptionsResponse | null>(null)
  const [riskResult, setRiskResult] = useState<YieldRiskResponse | null>(null)
  const [riskLoading, setRiskLoading] = useState(false)
  const [riskError, setRiskError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([getYieldOptions(), getProfitOptions(), getYieldRiskOptions()])
      .then(([yieldRes, profitRes, riskRes]) => {
        if (cancelled) return
        setOptions(yieldRes)
        setProfitOptions(profitRes)
        setRiskOptions(riskRes)
        setState((prev) => prev || guessState(activeFarm?.location, yieldRes.states))
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
          <TrendingUp size={14} /> Yield Prediction
        </div>
        <p className="mt-3 text-sm text-white/40">Loading yield model…</p>
      </GlassCard>
    )
  }

  const isCropSupported = options?.supported_crops.includes(crop.toLowerCase())
  const isProfitSupported = profitOptions?.supported_crops.includes(crop.toLowerCase())
  const isRiskSupported = riskOptions?.supported_crops.includes(crop.toLowerCase())

  if (!isCropSupported) {
    return (
      <GlassCard>
        <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
          <TrendingUp size={14} /> Yield Prediction
        </div>
        <p className="text-sm text-white/50">
          Yield data isn't available for <span className="capitalize text-white/70">{crop}</span> yet. Supported crops:{' '}
          {options?.supported_crops.join(', ') || 'none trained yet'}.
        </p>
      </GlassCard>
    )
  }

  const handleEstimate = async () => {
    if (!state || !season) {
      setError('Select both a state and a season.')
      return
    }
    setError(null)
    setLoading(true)
    setProfitResult(null)
    setRiskResult(null)
    try {
      const res = await predictYield(crop, state, season, activeFarm?.id)
      setResult(res)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleProfitEstimate = async () => {
    const cost = Number(costPerAcre)
    if (!Number.isFinite(cost) || cost < 0) {
      setProfitError('Enter a valid cost per acre (0 or more).')
      return
    }
    setProfitError(null)
    setProfitLoading(true)
    try {
      const res = await predictProfit(crop, state, season, cost, activeFarm?.area_acres, activeFarm?.id)
      setProfitResult(res)
    } catch (err) {
      setProfitError(apiErrorMessage(err))
    } finally {
      setProfitLoading(false)
    }
  }

  const handleRiskEstimate = async () => {
    setRiskError(null)
    setRiskLoading(true)
    try {
      const res = await predictYieldRisk(crop, state, season, activeFarm?.id)
      setRiskResult(res)
    } catch (err) {
      setRiskError(apiErrorMessage(err))
    } finally {
      setRiskLoading(false)
    }
  }

  return (
    <GlassCard>
      <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
        <TrendingUp size={14} /> Yield Prediction
      </div>

      <div className="grid grid-cols-2 gap-3">
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
          <label className="label-field">Season</label>
          <select value={season} onChange={(e) => setSeason(e.target.value)} className="input-field">
            <option value="" className="bg-forest-900">
              Select season
            </option>
            {options?.seasons.map((s) => (
              <option key={s} value={s} className="bg-forest-900">
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="mt-3 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

      <button onClick={handleEstimate} disabled={loading} className="btn-secondary mt-4 w-full py-2.5 text-sm disabled:opacity-60">
        {loading ? <Loader2 size={16} className="animate-spin" /> : 'Estimate Yield'}
      </button>

      {result?.supported && (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{result.predicted_yield_tonnes_per_ha}</span>
            <span className="text-sm text-white/50">tonnes / hectare</span>
          </div>
          <p className="mt-1 text-xs text-white/40">≈ {result.predicted_yield_quintal_per_acre} quintal / acre</p>
          <p className="mt-3 text-[11px] text-white/30">
            Model: {result.model_used} (R² = {result.r2_score?.toFixed(3)}, MAE = {result.mae?.toFixed(2)} t/ha) · based on historical{' '}
            {result.state} {result.season?.toLowerCase()} records for {result.mapped_crop}, 1997–2020 — not a guarantee for your specific
            plot.
          </p>
        </div>
      )}

      {result && !result.supported && result.reason && (
        <p className="mt-4 rounded-lg bg-amber-400/10 px-3 py-2 text-sm text-amber-300">{result.reason}</p>
      )}

      {result?.supported && isProfitSupported && (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <IndianRupee size={14} /> Profit Estimate
          </div>

          <label className="label-field">Your estimated cost (₹ / acre)</label>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              value={costPerAcre}
              onChange={(e) => setCostPerAcre(e.target.value)}
              placeholder="e.g. 18000"
              className="input-field"
            />
            <button
              onClick={handleProfitEstimate}
              disabled={profitLoading}
              className="btn-secondary shrink-0 px-4 text-sm disabled:opacity-60"
            >
              {profitLoading ? <Loader2 size={16} className="animate-spin" /> : 'Calculate'}
            </button>
          </div>
          <p className="mt-1 text-[11px] text-white/30">
            Revenue is calculated from the real yield estimate above × real 2016 mandi price data. Cost is your own input — no dataset can
            honestly predict your specific farm's costs.
          </p>

          {profitError && <p className="mt-3 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{profitError}</p>}

          {profitResult?.supported && (
            <div className="mt-4 space-y-3">
              <div className="flex items-baseline gap-2">
                <span className={`text-2xl font-bold ${profitResult.profit_per_acre! >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  ₹{profitResult.profit_per_acre?.toLocaleString('en-IN')}
                </span>
                <span className="text-sm text-white/50">profit / acre</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-lg bg-white/5 py-2">
                  <p className="text-white/40">Revenue</p>
                  <p className="font-semibold text-white">₹{profitResult.revenue_per_acre?.toLocaleString('en-IN')}</p>
                </div>
                <div className="rounded-lg bg-white/5 py-2">
                  <p className="text-white/40">Margin</p>
                  <p className="font-semibold text-white">{profitResult.margin_pct}%</p>
                </div>
                <div className="rounded-lg bg-white/5 py-2">
                  <p className="text-white/40">Farm Total</p>
                  <p className="font-semibold text-white">
                    {profitResult.total_farm_profit !== null ? `₹${profitResult.total_farm_profit.toLocaleString('en-IN')}` : '—'}
                  </p>
                </div>
              </div>
              <p className="text-[11px] text-white/30">
                Price: ₹{profitResult.price_rs_per_quintal}/quintal ({profitResult.price_source === 'state' ? profitResult.state : 'national median'},
                2016 mandi data, not inflation-adjusted) · this is a benchmark estimate, not a guaranteed return.
              </p>
            </div>
          )}

          {profitResult && !profitResult.supported && profitResult.reason && (
            <p className="mt-4 rounded-lg bg-amber-400/10 px-3 py-2 text-sm text-amber-300">{profitResult.reason}</p>
          )}
        </div>
      )}

      {result?.supported && isRiskSupported && (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
              <ShieldAlert size={14} /> Yield Risk (ML)
            </div>
            <button onClick={handleRiskEstimate} disabled={riskLoading} className="btn-secondary px-4 py-1.5 text-xs disabled:opacity-60">
              {riskLoading ? <Loader2 size={14} className="animate-spin" /> : 'Check'}
            </button>
          </div>

          {riskError && <p className="mt-2 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{riskError}</p>}

          {riskResult?.supported && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span
                  className={clsx(
                    'rounded-lg border px-3 py-1 text-xl font-bold',
                    riskResult.risk_level === 'LOW' && 'border-emerald-400/30 bg-emerald-400/10 text-emerald-400',
                    riskResult.risk_level === 'MEDIUM' && 'border-amber-400/30 bg-amber-400/10 text-amber-400',
                    riskResult.risk_level === 'HIGH' && 'border-rose-400/30 bg-rose-400/10 text-rose-400',
                  )}
                >
                  {riskResult.risk_level}
                </span>
                <div className="flex gap-3 text-xs text-white/50">
                  <span>L {((riskResult.probabilities?.LOW ?? 0) * 100).toFixed(0)}%</span>
                  <span>M {((riskResult.probabilities?.MEDIUM ?? 0) * 100).toFixed(0)}%</span>
                  <span>H {((riskResult.probabilities?.HIGH ?? 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
              <p className="text-[11px] text-white/30">
                Model: {riskResult.model_used} (accuracy {((riskResult.model_accuracy ?? 0) * 100).toFixed(1)}%) · reflects where{' '}
                {riskResult.mapped_crop} in {riskResult.state} has historically ranked nationally by yield tertile (1997–2020) — a
                regional historical performance tier, not a forecast of this year's weather or disease risk.
              </p>
            </div>
          )}

          {riskResult && !riskResult.supported && riskResult.reason && (
            <p className="rounded-lg bg-amber-400/10 px-3 py-2 text-sm text-amber-300">{riskResult.reason}</p>
          )}
        </div>
      )}
    </GlassCard>
  )
}
