import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Droplet, ThermometerSun, HeartPulse, ShieldAlert, Plus, Sprout } from 'lucide-react'
import { MetricCard } from '@/components/MetricCard'
import { EmptyState } from '@/components/EmptyState'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { useAuth } from '@/hooks/useAuth'
import { useFarmStore } from '@/hooks/useFarmStore'
import { listFarms } from '@/services/farmService'
import { getSoil } from '@/services/farmService'
import { getWeather } from '@/services/weatherService'
import { apiErrorMessage } from '@/services/api'
import type { SoilHealthResult, WeatherData } from '@/types'

export function DashboardPage() {
  const user = useAuth((s) => s.user)
  const { farms, activeFarm, setFarms } = useFarmStore()
  const [soilHealth, setSoilHealth] = useState<SoilHealthResult | null>(null)
  const [weather, setWeather] = useState<WeatherData | null>(null)
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

        const weatherData = await getWeather(farmList[0]?.location)
        if (cancelled) return
        setWeather(weatherData)

        if (farmList[0]) {
          const soil = await getSoil(farmList[0].id)
          if (!cancelled) setSoilHealth(soil?.health ?? null)
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

  const farmHealth = soilHealth ? Math.round((soilHealth.score + (weather ? 80 : 60)) / 2) : null

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
        <MetricCard label="Soil Health" value={soilHealth ? `${soilHealth.score}/100` : '—'} icon={Droplet} tone="emerald" />
        <MetricCard label="Weather" value={weather ? `${Math.round(weather.temperature_c)}°C` : '—'} subtext={weather?.condition} icon={ThermometerSun} tone="sky" />
        <MetricCard label="Farm Health" value={farmHealth !== null ? `${farmHealth}%` : '—'} icon={HeartPulse} tone="lime" />
        <MetricCard label="Risk" value={farmHealth !== null && farmHealth >= 70 ? 'LOW' : 'MEDIUM'} icon={ShieldAlert} tone="amber" />
      </div>

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
            <Link to="/app/crop-recommendation" className="btn-primary px-4 py-2 text-xs">
              Run AI Analysis
            </Link>
          </div>
        </div>
      </GlassCard>
    </div>
  )
}

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}
