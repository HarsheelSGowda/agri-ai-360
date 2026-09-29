import { api } from './api'
import type { IoTReadingsResponse, SatelliteStatusResponse } from '@/types'

export async function getSatelliteStatus(farmId: number): Promise<SatelliteStatusResponse> {
  const { data } = await api.get<SatelliteStatusResponse>('/satellite/status', { params: { farm_id: farmId } })
  return data
}

export async function getIoTReadings(farmId: number): Promise<IoTReadingsResponse> {
  const { data } = await api.get<IoTReadingsResponse>('/iot/readings', { params: { farm_id: farmId } })
  return data
}

export async function seedIoTDemoReadings(farmId: number): Promise<IoTReadingsResponse> {
  const { data } = await api.post<IoTReadingsResponse>('/iot/demo/seed', null, { params: { farm_id: farmId } })
  return data
}
