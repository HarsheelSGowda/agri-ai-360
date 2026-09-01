import { api } from './api'
import type { ProfitOptionsResponse, ProfitPredictionResponse } from '@/types'

export async function getProfitOptions(): Promise<ProfitOptionsResponse> {
  const { data } = await api.get<ProfitOptionsResponse>('/predict/profit/options')
  return data
}

export async function predictProfit(
  crop: string,
  state: string,
  season: string,
  costPerAcre: number,
  areaAcres?: number,
  farmId?: number,
): Promise<ProfitPredictionResponse> {
  const { data } = await api.post<ProfitPredictionResponse>('/predict/profit', {
    crop,
    state,
    season,
    cost_per_acre: costPerAcre,
    area_acres: areaAcres,
    farm_id: farmId,
  })
  return data
}
