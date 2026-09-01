import { api } from './api'
import type { Farm, SoilHealthResult, SoilRecord } from '@/types'

export interface CreateFarmPayload {
  name: string
  location: string
  area_acres: number
  soil_type: string
  irrigation_available: boolean
}

export async function createFarm(payload: CreateFarmPayload): Promise<Farm> {
  const { data } = await api.post<Farm>('/farms', payload)
  return data
}

export async function listFarms(): Promise<Farm[]> {
  const { data } = await api.get<Farm[]>('/farms')
  return data
}

export async function getFarm(id: number): Promise<Farm> {
  const { data } = await api.get<Farm>(`/farms/${id}`)
  return data
}

export interface SubmitSoilPayload {
  nitrogen: number
  phosphorus: number
  potassium: number
  ph: number
  soil_type: string
  organic_carbon?: number
  moisture?: number
  electrical_conductivity?: number
}

export async function submitSoil(farmId: number, payload: SubmitSoilPayload): Promise<SoilRecord & { health: SoilHealthResult }> {
  const { data } = await api.post(`/farms/${farmId}/soil`, payload)
  return data
}

export async function getSoil(farmId: number): Promise<(SoilRecord & { health: SoilHealthResult }) | null> {
  const { data } = await api.get(`/farms/${farmId}/soil`)
  return data
}
