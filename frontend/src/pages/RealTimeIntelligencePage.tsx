import { useEffect, useState } from 'react'
import { Satellite, Cpu, RefreshCw, Droplets, Thermometer, Waves, Radio } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { WeatherCard } from '@/components/WeatherCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { getWeather } from '@/services/weatherService'
import { getSatelliteStatus, getIoTReadings, seedIoTDemoReadings } from '@/services/realtimeService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { IoTReadingsResponse, SatelliteStatusResponse, SensorReading, WeatherData } from '@/types'

const SENSOR_ICON: Record<SensorReading['sensor_type'], typeof Droplets> = {
  soil_moisture: Droplets,
  temperature: Thermometer,
  humidity: Waves,
  ec: Radio,
}

const SENSOR_LABEL: Record<SensorReading['sensor_type'], string> = {
  soil_moisture: 'Soil Moisture',
  temperature: 'Temperature',
  humidity: 'Humidity',
  ec: 'Electrical Conductivity',
}

export function RealTimeIntelligencePage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [satellite, setSatellite] = useState<SatelliteStatusResponse | null>(null)
  const [iot, setIot] = useState<IoTReadingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!activeFarm) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      getWeather(activeFarm.location),
      getSatelliteStatus(activeFarm.id),
      getIoTReadings(activeFarm.id),
    ])
      .then(([w, s, i]) => {
        if (cancelled) return
        setWeather(w)
        setSatellite(s)
        setIot(i)
      })
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [activeFarm])

  async function handleSeed() {
    if (!activeFarm) return
    setSeeding(true)
    try {
      const res = await seedIoTDemoReadings(activeFarm.id)
      setIot(res)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSeeding(false)
    }
  }

  if (!activeFarm) {
    return (
      <EmptyState
        icon={Radio}
        title="No farm selected"
        description="Select or create a farm to view its real-time weather, satellite and IoT sensor intelligence."
      />
    )
  }

  if (loading) return <LoadingAnimation label="Loading real-time intelligence…" />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  return (
    <div className="space-y-6">
      {weather && (
        <div>
          <h2 className="mb-2 text-xs uppercase tracking-wider text-white/50">Weather</h2>
          <WeatherCard weather={weather} />
        </div>
      )}

      <div>
        <h2 className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
          <Satellite size={14} /> Satellite Monitoring
        </h2>
        {satellite && (
          <GlassCard hover={false}>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold text-white">Vegetation &amp; Field Intelligence</p>
              <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300">
                PLANNED / INTEGRATION-READY
              </span>
            </div>
            <p className="mb-4 text-sm text-white/60">{satellite.message}</p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {satellite.planned_metrics.map((m) => (
                <div key={m.key} className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-sm font-medium text-white/80">{m.label}</p>
                  <p className="mt-1 text-xs text-white/40">{m.description}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        )}
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <Cpu size={14} /> IoT Sensor Feed
          </h2>
          <button onClick={handleSeed} disabled={seeding} className="btn-secondary flex items-center gap-1.5 px-3 py-1.5 text-xs disabled:opacity-60">
            <RefreshCw size={12} className={seeding ? 'animate-spin' : ''} /> Generate demo reading
          </button>
        </div>
        <GlassCard hover={false}>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-white">Latest sensor readings</p>
            {iot && (
              <span
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  iot.has_real_device_data
                    ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                    : 'border-amber-400/30 bg-amber-400/10 text-amber-300'
                }`}
              >
                {iot.has_real_device_data ? 'INCLUDES REAL DEVICE DATA' : 'DEMO / SIMULATION'}
              </span>
            )}
          </div>

          {!iot || iot.readings.length === 0 ? (
            <p className="py-8 text-center text-sm text-white/40">
              No sensor data yet — no physical sensors are connected to this deployment. Click "Generate demo reading"
              to see how live soil-moisture/temperature/humidity/EC sensor feeds would appear here, or POST to{' '}
              <code className="rounded bg-white/10 px-1 py-0.5">/api/iot/readings</code> from a real gateway/device.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {iot.readings.slice(0, 4).map((r) => {
                const Icon = SENSOR_ICON[r.sensor_type]
                return (
                  <div key={r.id} className="flex flex-col items-center gap-1 rounded-xl bg-white/5 py-4 text-center">
                    <Icon size={16} className="text-sky-400" />
                    <span className="text-lg font-semibold text-white">
                      {r.value}
                      <span className="ml-0.5 text-xs text-white/40">{r.unit}</span>
                    </span>
                    <span className="text-[10px] text-white/40">{SENSOR_LABEL[r.sensor_type]}</span>
                    <span
                      className={`mt-1 rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${
                        r.source === 'demo_simulation' ? 'bg-amber-400/10 text-amber-300' : 'bg-emerald-400/10 text-emerald-300'
                      }`}
                    >
                      {r.source === 'demo_simulation' ? 'DEMO' : 'DEVICE'}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
          <p className="mt-4 text-[11px] text-white/30">
            Architecture: Sensor → API/MQTT gateway → Backend → Database → Dashboard. Demo readings are clearly
            labeled and never presented as live sensor data.
          </p>
        </GlassCard>
      </div>
    </div>
  )
}
