import { CloudSun, Droplets, CloudRain, Wind } from 'lucide-react'
import { GlassCard } from './GlassCard'
import type { WeatherData } from '@/types'

export function WeatherCard({ weather }: { weather: WeatherData }) {
  return (
    <GlassCard>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-white/50">
          <CloudSun size={16} />
          <span className="text-xs uppercase tracking-wider">Weather Intelligence</span>
        </div>
        {weather.source === 'mock' && (
          <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
            MOCK PROVIDER
          </span>
        )}
      </div>

      <div className="mb-6 flex items-end gap-3">
        <span className="text-5xl font-bold tracking-tight text-white">{Math.round(weather.temperature_c)}°C</span>
        <span className="mb-1.5 text-sm text-white/50">{weather.condition}</span>
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="flex flex-col items-center gap-1 rounded-xl bg-white/5 py-3">
          <Droplets size={16} className="text-sky-400" />
          <span className="font-semibold text-white">{weather.humidity_pct}%</span>
          <span className="text-[10px] text-white/40">Humidity</span>
        </div>
        <div className="flex flex-col items-center gap-1 rounded-xl bg-white/5 py-3">
          <CloudRain size={16} className="text-emerald-400" />
          <span className="font-semibold text-white">{weather.rainfall_mm} mm</span>
          <span className="text-[10px] text-white/40">Rainfall</span>
        </div>
        <div className="flex flex-col items-center gap-1 rounded-xl bg-white/5 py-3">
          <Wind size={16} className="text-lime-400" />
          <span className="font-semibold text-white">{weather.wind_kmh} km/h</span>
          <span className="text-[10px] text-white/40">Wind</span>
        </div>
      </div>

      {weather.forecast?.length > 0 && (
        <div className="mt-5 flex justify-between border-t border-white/10 pt-4">
          {weather.forecast.map((f) => (
            <div key={f.day} className="flex flex-col items-center gap-1 text-center">
              <span className="text-[10px] text-white/40">{f.day}</span>
              <span className="text-sm font-medium text-white">{Math.round(f.temp_c)}°</span>
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  )
}
