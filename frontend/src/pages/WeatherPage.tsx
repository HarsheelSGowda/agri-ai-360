import { useEffect, useState } from 'react'
import { WeatherCard } from '@/components/WeatherCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { getWeather } from '@/services/weatherService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { WeatherData } from '@/types'

export function WeatherPage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const setLastWeather = useFarmStore((s) => s.setLastWeather)
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await getWeather(activeFarm?.location)
        if (!cancelled) {
          setWeather(data)
          setLastWeather(data)
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
  }, [activeFarm?.location, setLastWeather])

  if (loading) return <LoadingAnimation label="Fetching latest weather…" />
  if (error) return <ErrorState message={error} />
  if (!weather) return null

  return (
    <div className="mx-auto max-w-md">
      <WeatherCard weather={weather} />
      {weather.source === 'mock' && (
        <p className="mt-4 text-center text-xs text-white/30">
          Live weather API not yet configured — showing a clearly-labeled mock provider via a swappable WeatherProvider service.
        </p>
      )}
    </div>
  )
}
