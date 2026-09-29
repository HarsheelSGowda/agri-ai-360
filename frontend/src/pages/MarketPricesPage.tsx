import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { LineChart as LineChartIcon, TrendingUp, TrendingDown, Minus, Store, Clock, Database } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { MetricCard } from '@/components/MetricCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { EmptyState } from '@/components/EmptyState'
import { apiErrorMessage } from '@/services/api'
import {
  getMarketCrops,
  getMarketStates,
  getMarketDistricts,
  getMarketMarkets,
  getCurrentPrice,
  getPriceTrend,
  getMarketComparison,
} from '@/services/marketPriceService'
import type { CurrentPriceResponse, MarketComparisonResponse, TrendResponse } from '@/types'

const TREND_ICON = { UP: TrendingUp, DOWN: TrendingDown, FLAT: Minus }
const TREND_COLOR = { UP: 'text-emerald-400', DOWN: 'text-rose-400', FLAT: 'text-white/50' }

function Select({
  label,
  value,
  onChange,
  options,
  disabled,
  allowAll,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
  disabled?: boolean
  allowAll?: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[11px] uppercase tracking-wider text-white/40">{label}</label>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white disabled:opacity-40"
      >
        {allowAll && <option value="">All</option>}
        {options.map((o) => (
          <option key={o} value={o} className="bg-forest-950">
            {o}
          </option>
        ))}
      </select>
    </div>
  )
}

export function MarketPricesPage() {
  const [crops, setCrops] = useState<string[]>([])
  const [states, setStates] = useState<string[]>([])
  const [districts, setDistricts] = useState<string[]>([])
  const [markets, setMarkets] = useState<string[]>([])

  const [crop, setCrop] = useState('')
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [market, setMarket] = useState('')

  const [current, setCurrent] = useState<CurrentPriceResponse | null>(null)
  const [trend, setTrend] = useState<TrendResponse | null>(null)
  const [comparison, setComparison] = useState<MarketComparisonResponse | null>(null)

  const [loadingOptions, setLoadingOptions] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMarketCrops()
      .then((res) => {
        setCrops(res)
        if (res.length) setCrop(res[0])
      })
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoadingOptions(false))
  }, [])

  useEffect(() => {
    if (!crop) return
    setState('')
    setDistrict('')
    setMarket('')
    getMarketStates(crop)
      .then((res) => {
        setStates(res)
        if (res.length) setState(res[0])
      })
      .catch((err) => setError(apiErrorMessage(err)))
  }, [crop])

  useEffect(() => {
    if (!crop || !state) return
    setDistrict('')
    setMarket('')
    getMarketDistricts(crop, state)
      .then(setDistricts)
      .catch((err) => setError(apiErrorMessage(err)))
  }, [crop, state])

  useEffect(() => {
    if (!crop || !state) return
    setMarket('')
    getMarketMarkets(crop, state, district || undefined)
      .then(setMarkets)
      .catch((err) => setError(apiErrorMessage(err)))
  }, [crop, state, district])

  useEffect(() => {
    if (!crop || !state) return
    let cancelled = false
    setLoadingData(true)
    setError(null)
    const query = { crop, state, district: district || undefined, market: market || undefined }
    Promise.all([getCurrentPrice(query), getPriceTrend({ ...query, days: 15 }), getMarketComparison({ crop, state, district: district || undefined })])
      .then(([c, t, m]) => {
        if (cancelled) return
        setCurrent(c)
        setTrend(t)
        setComparison(m)
      })
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setLoadingData(false))
    return () => {
      cancelled = true
    }
  }, [crop, state, district, market])

  if (loadingOptions) return <LoadingAnimation label="Loading market price data…" />

  if (crops.length === 0) {
    return (
      <EmptyState
        icon={Database}
        title="No market price data available"
        description="Run ml/market_price/seed_market_prices.py to load historical Agmarknet mandi price records into the database."
      />
    )
  }

  const TrendIcon = trend?.trend_direction ? TREND_ICON[trend.trend_direction] : Minus

  return (
    <div className="space-y-6">
      <GlassCard hover={false}>
        <h2 className="mb-1 text-xl font-semibold text-white">Market Price Intelligence</h2>
        <p className="mb-4 text-sm text-white/50">
          Real historical Agmarknet (Government of India) mandi price records — not a live feed. See "Source & date" below each figure.
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Select label="Crop" value={crop} onChange={setCrop} options={crops} />
          <Select label="State" value={state} onChange={setState} options={states} disabled={!states.length} />
          <Select label="District" value={district} onChange={setDistrict} options={districts} disabled={!districts.length} allowAll />
          <Select label="Market" value={market} onChange={setMarket} options={markets} disabled={!markets.length} allowAll />
        </div>
      </GlassCard>

      {error && <p className="rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

      {loadingData ? (
        <LoadingAnimation label="Fetching prices…" />
      ) : current?.found === false ? (
        <EmptyState icon={Database} title="No data for this selection" description={current.reason ?? 'Try a different crop/state/district/market.'} />
      ) : (
        current && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <MetricCard label="Min Price" value={`₹${current.min_price?.toLocaleString('en-IN')}/qtl`} tone="sky" icon={Store} />
              <MetricCard label="Max Price" value={`₹${current.max_price?.toLocaleString('en-IN')}/qtl`} tone="amber" icon={Store} />
              <MetricCard label="Modal Price" value={`₹${current.modal_price?.toLocaleString('en-IN')}/qtl`} tone="emerald" icon={Store} />
            </div>

            <GlassCard hover={false} className="flex flex-wrap items-center justify-between gap-3 text-xs text-white/50">
              <span className="flex items-center gap-1.5">
                <Clock size={13} /> As of {current.as_of_date} · {current.markets_reporting} market(s) reporting
              </span>
              <span className="flex items-center gap-1.5">
                <Database size={13} /> Source: {current.source} {current.is_live === false && '(historical, not live)'}
              </span>
            </GlassCard>

            {trend && trend.found && (
              <GlassCard hover={false}>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
                    <LineChartIcon size={16} /> Recent Price Trend
                  </h3>
                  {trend.trend_direction && (
                    <span className={`flex items-center gap-1 text-xs font-semibold ${TREND_COLOR[trend.trend_direction]}`}>
                      <TrendIcon size={14} /> {trend.trend_direction} {trend.change_pct != null && `${trend.change_pct}%`}
                    </span>
                  )}
                </div>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trend.points} margin={{ left: -12, right: 12, top: 8, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: '#0b2c1c', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 12, color: '#fff' }}
                      />
                      <Line type="monotone" dataKey="modal_price" stroke="#34d399" strokeWidth={2} dot={false} name="Modal Price" />
                      <Line type="monotone" dataKey="min_price" stroke="#38bdf8" strokeWidth={1.5} dot={false} strokeDasharray="4 4" name="Min" />
                      <Line type="monotone" dataKey="max_price" stroke="#fbbf24" strokeWidth={1.5} dot={false} strokeDasharray="4 4" name="Max" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </GlassCard>
            )}

            {comparison && comparison.found && (
              <GlassCard hover={false}>
                <h3 className="mb-4 text-sm font-semibold text-white">Market Comparison ({state}{district ? `, ${district}` : ''})</h3>
                {comparison.best_market && (
                  <p className="mb-3 rounded-lg bg-emerald-400/10 px-3 py-2 text-xs text-emerald-300">
                    Best nearby market by modal price: <span className="font-semibold">{comparison.best_market.market}</span> (
                    {comparison.best_market.district}) — ₹{comparison.best_market.modal_price.toLocaleString('en-IN')}/qtl
                  </p>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-white/40">
                        <th className="pb-2 pr-4 font-medium">Market</th>
                        <th className="pb-2 pr-4 font-medium">District</th>
                        <th className="pb-2 pr-4 font-medium">Min</th>
                        <th className="pb-2 pr-4 font-medium">Max</th>
                        <th className="pb-2 pr-4 font-medium">Modal</th>
                        <th className="pb-2 font-medium">Arrivals (t)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.markets.slice(0, 15).map((m) => (
                        <tr key={m.market} className="border-t border-white/5 text-white/70">
                          <td className="py-1.5 pr-4">{m.market}</td>
                          <td className="py-1.5 pr-4 text-white/45">{m.district}</td>
                          <td className="py-1.5 pr-4 font-mono">₹{m.min_price.toLocaleString('en-IN')}</td>
                          <td className="py-1.5 pr-4 font-mono">₹{m.max_price.toLocaleString('en-IN')}</td>
                          <td className="py-1.5 pr-4 font-mono text-emerald-300">₹{m.modal_price.toLocaleString('en-IN')}</td>
                          <td className="py-1.5 font-mono text-white/45">{m.arrivals_tonnes ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            )}
          </>
        )
      )}
    </div>
  )
}
