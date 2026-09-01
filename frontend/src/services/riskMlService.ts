import { api } from './api'
import type { YieldRiskOptionsResponse, YieldRiskResponse } from '@/types'

export async function getYieldRiskOptions(): Promise<YieldRiskOptionsResponse> {
  const { data } = await api.get<YieldRiskOptionsResponse>('/predict/yield-risk/options')
  return data
}

export async function predictYieldRisk(crop: string, state: string, season: string, farmId?: number): Promise<YieldRiskResponse> {
  const { data } = await api.post<YieldRiskResponse>('/predict/yield-risk', { crop, state, season, farm_id: farmId })
  return data
}
