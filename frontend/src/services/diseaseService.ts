import { api } from './api'
import type { DiseaseDiagnosisResponse, DiseaseHistoryItem, DiseaseOptionsResponse } from '@/types'

export async function getDiseaseOptions(): Promise<DiseaseOptionsResponse> {
  const { data } = await api.get<DiseaseOptionsResponse>('/predict/disease/options')
  return data
}

export async function diagnoseDisease(file: File, farmId?: number | null): Promise<DiseaseDiagnosisResponse> {
  const formData = new FormData()
  formData.append('image', file)
  if (farmId != null) formData.append('farm_id', String(farmId))
  const { data } = await api.post<DiseaseDiagnosisResponse>('/predict/disease', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getDiseaseHistory(farmId?: number | null): Promise<DiseaseHistoryItem[]> {
  const { data } = await api.get<DiseaseHistoryItem[]>('/history/disease', {
    params: farmId != null ? { farm_id: farmId } : undefined,
  })
  return data
}
