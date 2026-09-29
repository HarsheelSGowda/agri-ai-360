import { api } from './api'
import type { FertilizerOptionsResponse, FertilizerRecommendationResponse } from '@/types'

export async function getFertilizerOptions(): Promise<FertilizerOptionsResponse> {
  const { data } = await api.get<FertilizerOptionsResponse>('/fertilizer/options')
  return data
}

export interface FertilizerRecommendationPayload {
  crop: string
  nitrogen: number
  phosphorus: number
  potassium: number
  ph: number
  growth_stage: string
  organic_carbon?: number
  moisture?: number
  farm_area_acres?: number
  farm_id?: number | null
}

export async function recommendFertilizer(payload: FertilizerRecommendationPayload): Promise<FertilizerRecommendationResponse> {
  const { data } = await api.post<FertilizerRecommendationResponse>('/fertilizer/recommend', payload)
  return data
}
