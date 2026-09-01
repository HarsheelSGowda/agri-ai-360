import { api } from './api'
import type { WeatherData } from '@/types'

export async function getWeather(location?: string): Promise<WeatherData> {
  const { data } = await api.get<WeatherData>('/weather', { params: location ? { location } : {} })
  return data
}
