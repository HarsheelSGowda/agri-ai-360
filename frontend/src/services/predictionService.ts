import { api } from './api'
import type {
  CropPredictionInput,
  ExplanationResponse,
  ModelPerformanceResponse,
  PredictionHistoryItem,
  TopCropsResponse,
} from '@/types'

export async function predictTopCrops(input: CropPredictionInput, farmId?: number): Promise<TopCropsResponse> {
  const { data } = await api.post<TopCropsResponse>('/predict/top-crops', { ...input, farm_id: farmId })
  return data
}

export async function explainCrop(input: CropPredictionInput, crop: string): Promise<ExplanationResponse> {
  const { data } = await api.post<ExplanationResponse>('/explain/crop', { ...input, crop })
  return data
}

export async function getModelPerformance(): Promise<ModelPerformanceResponse> {
  const { data } = await api.get<ModelPerformanceResponse>('/models/performance')
  return data
}

export async function getHistory(farmId?: number): Promise<PredictionHistoryItem[]> {
  const { data } = await api.get<PredictionHistoryItem[]>('/history', { params: farmId ? { farm_id: farmId } : {} })
  return data
}
