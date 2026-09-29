import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Droplet,
  ThermometerSun,
  HeartPulse,
  ShieldAlert,
  Plus,
  Sprout,
  Stethoscope,
  Beaker,
  Store,
  Bell,
  History as HistoryIcon,
} from 'lucide-react'
import { MetricCard } from '@/components/MetricCard'
import { EmptyState } from '@/components/EmptyState'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { useAuth } from '@/hooks/useAuth'
import { useFarmStore } from '@/hooks/useFarmStore'
import { listFarms, getSoil } from '@/services/farmService'
import { getDashboardSummary } from '@/services/dashboardService'
import { getHistory } from '@/services/predictionService'
import { getDiseaseHistory } from '@/services/diseaseService'
import { getNotifications } from '@/services/notificationService'
import { getMarketStates, getCurrentPrice } from '@/services/marketPriceService'
import { recommendFertilizer } from '@/services/fertilizerService'
import { apiErrorMessage } from '@/services/api'
import type {
  CurrentPriceResponse,
  DashboardSummary,
  DiseaseHistoryItem,
  FertilizerRecommendationResponse,
  NotificationItem,
  PredictionHistoryItem,
} from '@/types'

function guessState(location: string | undefined, states: string[]): string | null {
  if (!location) return null
  const lower = location.toLowerCase()
  return states.find((s) => lower.includes(s.toLowerCase())) ?? null
}

const RISK_TONE: Record<string, 'emerald' | 'amber' | 'rose'> = { LOW: 'emerald', MEDIUM: 'amber', HIGH: 'rose' }

export function DashboardPage() {
  const user = useAuth((s) => s.user)
  const { farms, activeFarm, setFarms } = useFarmStore()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [recentPredictions, setRecentPredictions] = useState<PredictionHistoryItem[]>([])
  const [latestDisease, setLatestDisease] = useState<DiseaseHistoryItem | null>(null)
  const [alerts, setAlerts] = useState<NotificationItem[]>([])
  const [marketPrice, setMarketPrice] = useState<CurrentPriceResponse | null>(null)
  const [fertilizer, setFertilizer] = useState<FertilizerRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const farmList = await listFarms()
        if (cancelled) return
        setFarms(farmList)

        const farm = farmList[0]
        if (!farm) {
          setLoading(false)
          return
        }

        const [dashboardRes, history, diseaseHistory, notifications] = await Promise.all([
          getDashboardSummary(farm.id),
          getHistory(farm.id).catch(() => []),
          getDiseaseHistory(farm.id).catch(() => []),
          getNotifications(true).catch(() => []),
        ])
        if (cancelled) return

        setSummary(dashboardRes)
        setRecentPredictions(history.slice(0, 4))
        setLatestDisease(diseaseHistory[0] ?? null)
        setAlerts(notifications.slice(0, 3))

        const topCrop = history[0]?.crop
        if (topCrop) {
          const states = await getMarketStates(topCrop).catch(() => [])
          const state = guessState(farm.location, states)
          if (state) {
            const price = await getCurrentPrice({ crop: topCrop, state }).catch(() => null)
            if (!cancelled && price?.found) setMarketPrice(price)
          }
        }

        if (dashboardRes.soil_health && topCrop) {
          const soil = await getSoil(farm.id).catch(() => null)
          if (soil) {
            const fert = await recommendFertilizer({
              crop: topCrop,
              nitrogen: soil.nitrogen,
              phosphorus: soil.phosphorus,
              potassium: soil.potassium,
              ph: soil.ph,
              growth_stage: 'vegetative',
              organic_carbon: soil.organic_carbon ?? undefined,
              moisture: soil.moisture ?? undefined,
              farm_area_acres: farm.area_acres,
              farm_id: farm.id,
            }).catch(() => null)
            if (!cancelled && fert) setFertilizer(fert)
          }
        }
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setFarms])

  const greeting = getGreeting()

  if (loading) return <LoadingAnimation label="Loading your farm overview…" />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  if (farms.length === 0) {
    return (
      <EmptyState
        icon={Sprout}
        title="No farms yet"
        description="Create your first farm to start getting AI-powered crop recommendations."
        action={
          <Link to="/app/farms/new" className="btn-primary mt-2 px-5 py-2.5 text-sm">
            <Plus size={16} /> Create Farm
          </Link>
        }
      />
    )
  }

  const recommendedCrop = recentPredictions[0]?.crop ?? null

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-white">
          {greeting}, {user?.name?.split(' ')[0] ?? 'Farmer'} 🌱
        </h2>
        <Link to="/app/crop-recommendation" className="btn-primary px-5 py-2.5 text-sm">
          <Sprout size={16} /> Analyze My Farm
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Soil Health" value={summary?.soil_health ? `${summary.soil_health.score}/100` : '—'} icon={Droplet} tone="emerald" />
        <MetricCard
          label="Weather"
          value={summary ? `${Math.round(summary.weather.temperature_c)}°C` : '—'}
          subtext={summary?.weather.condition}
          icon={ThermometerSun}
          tone="sky"
        />
        <MetricCard label="Farm Health" value={summary?.farm_health != null ? `${summary.farm_health}%` : '—'} icon={HeartPulse} tone="lime" />
        <MetricCard
          label="Risk"
          value={summary?.risk.overall ?? '—'}
          subtext={summary?.risk.notes[0]}
          icon={ShieldAlert}
          tone={summary ? RISK_TONE[summary.risk.overall] : 'amber'}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <GlassCard>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <Sprout size={14} /> Recommended Crop
          </div>
          {recommendedCrop ? (
            <>
              <p className="text-lg font-semibold capitalize text-white">{recommendedCrop}</p>
              <p className="text-xs text-white/40">{(recentPredictions[0].score * 100).toFixed(1)}% suitability · last run</p>
              <Link to={`/app/crop-recommendation/${recommendedCrop}`} className="mt-2 inline-block text-xs text-emerald-300/80 hover:text-emerald-300">
                View details →
              </Link>
            </>
          ) : (
            <p className="text-sm text-white/40">Run an analysis to get a recommendation.</p>
          )}
        </GlassCard>

        <GlassCard>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <Stethoscope size={14} /> Disease Status
          </div>
          {latestDisease ? (
            <>
              <p className={`text-lg font-semibold capitalize ${latestDisease.is_healthy ? 'text-emerald-300' : 'text-amber-300'}`}>
                {latestDisease.is_healthy ? 'Healthy' : latestDisease.condition}
              </p>
              <p className="text-xs text-white/40">
                {latestDisease.crop} · {(latestDisease.probability * 100).toFixed(0)}% confidence
              </p>
            </>
          ) : (
            <p className="text-sm text-white/40">No leaf diagnoses yet.</p>
          )}
          <Link to="/app/crop-doctor" className="mt-2 inline-block text-xs text-emerald-300/80 hover:text-emerald-300">
            Diagnose a leaf →
          </Link>
        </GlassCard>

        <GlassCard>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <Store size={14} /> Market Price
          </div>
          {marketPrice?.found ? (
            <>
              <p className="text-lg font-semibold text-white">₹{marketPrice.modal_price?.toLocaleString('en-IN')}/qtl</p>
              <p className="text-xs text-white/40 capitalize">
                {marketPrice.crop} · {marketPrice.state} · as of {marketPrice.as_of_date}
              </p>
            </>
          ) : (
            <p className="text-sm text-white/40">No mandi price data for this crop/state yet.</p>
          )}
          <Link to="/app/market-prices" className="mt-2 inline-block text-xs text-emerald-300/80 hover:text-emerald-300">
            View market prices →
          </Link>
        </GlassCard>

        <GlassCard>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <Beaker size={14} /> Fertilizer Status
          </div>
          {fertilizer ? (
            (() => {
              const deficient = fertilizer.deficiencies.filter((d) => d.status === 'DEFICIENT')
              return deficient.length > 0 ? (
                <>
                  <p className="text-lg font-semibold text-amber-300">{deficient.length} nutrient(s) low</p>
                  <p className="text-xs text-white/40">{deficient.map((d) => d.nutrient).join(', ')}</p>
                </>
              ) : (
                <p className="text-lg font-semibold text-emerald-300">Nutrients adequate</p>
              )
            })()
          ) : (
            <p className="text-sm text-white/40">Submit soil data to see fertilizer status.</p>
          )}
          <Link to="/app/fertilizer" className="mt-2 inline-block text-xs text-emerald-300/80 hover:text-emerald-300">
            Open Fertilizer Advisor →
          </Link>
        </GlassCard>
      </div>

      <GlassCard>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <Bell size={14} /> Personalized Alerts
          </div>
          <Link to="/app/notifications" className="text-xs text-emerald-300/80 hover:text-emerald-300">
            View all →
          </Link>
        </div>
        {alerts.length === 0 ? (
          <p className="text-sm text-white/40">
            No unread alerts. Visit{' '}
            <Link to="/app/notifications" className="text-emerald-300/80 hover:text-emerald-300">
              Notifications
            </Link>{' '}
            to generate personalized alerts for this farm.
          </p>
        ) : (
          <div className="space-y-2">
            {alerts.map((a) => (
              <div key={a.id} className="rounded-lg bg-white/5 px-3 py-2">
                <p className="text-sm font-medium text-white">{a.title}</p>
                <p className="text-xs text-white/50">{a.message}</p>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      <GlassCard>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white/50">Active Farm</h3>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-lg font-semibold text-white">{activeFarm?.name}</p>
            <p className="text-sm text-white/50">
              {activeFarm?.location} · {activeFarm?.area_acres} acres · {activeFarm?.soil_type} soil
            </p>
          </div>
          <div className="flex gap-2">
            <Link to="/app/soil" className="btn-secondary px-4 py-2 text-xs">
              Soil Input
            </Link>
            <Link to="/app/fertilizer" className="btn-secondary flex items-center gap-1.5 px-4 py-2 text-xs">
              <Beaker size={13} /> Fertilizer Advisor
            </Link>
            <Link to="/app/crop-recommendation" className="btn-primary px-4 py-2 text-xs">
              Run AI Analysis
            </Link>
          </div>
        </div>
      </GlassCard>

      {recentPredictions.length > 0 && (
        <GlassCard>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
              <HistoryIcon size={14} /> Recent Predictions
            </div>
            <Link to="/app/history" className="text-xs text-emerald-300/80 hover:text-emerald-300">
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {recentPredictions.map((p) => (
              <div key={p.id} className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm">
                <span className="capitalize text-white/80">{p.crop}</span>
                <span className="font-mono text-xs text-emerald-300">{(p.score * 100).toFixed(1)}%</span>
                <span className="text-xs text-white/40">{new Date(p.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  )
}

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}
