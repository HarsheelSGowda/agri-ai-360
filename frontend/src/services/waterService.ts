import { api } from './api'
import type { WaterOptionsResponse, WaterRequirementResponse } from '@/types'

export async function getWaterOptions(): Promise<WaterOptionsResponse> {
  const { data } = await api.get<WaterOptionsResponse>('/predict/water/options')
  return data
}

export async function predictWater(
  crop: string,
  state: string,
  temperatureC: number,
  rainfallMm: number,
  areaAcres?: number,
  farmId?: number,
): Promise<WaterRequirementResponse> {
  const { data } = await api.post<WaterRequirementResponse>('/predict/water', {
    crop,
    state,
    temperature_c: temperatureC,
    rainfall_mm: rainfallMm,
    area_acres: areaAcres,
    farm_id: farmId,
  })
  return data
}
