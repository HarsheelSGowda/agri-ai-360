import { api } from './api'
import type { DiseaseDiagnosisResponse, DiseaseOptionsResponse } from '@/types'

export async function getDiseaseOptions(): Promise<DiseaseOptionsResponse> {
  const { data } = await api.get<DiseaseOptionsResponse>('/predict/disease/options')
  return data
}

export async function diagnoseDisease(file: File): Promise<DiseaseDiagnosisResponse> {
  const formData = new FormData()
  formData.append('image', file)
  const { data } = await api.post<DiseaseDiagnosisResponse>('/predict/disease', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
