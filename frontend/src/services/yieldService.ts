import { api } from './api'
import type { YieldOptionsResponse, YieldPredictionResponse } from '@/types'

export async function getYieldOptions(): Promise<YieldOptionsResponse> {
  const { data } = await api.get<YieldOptionsResponse>('/predict/yield/options')
  return data
}

export async function predictYield(crop: string, state: string, season: string, farmId?: number): Promise<YieldPredictionResponse> {
  const { data } = await api.post<YieldPredictionResponse>('/predict/yield', { crop, state, season, farm_id: farmId })
  return data
}
