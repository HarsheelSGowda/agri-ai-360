import { api } from './api'
import type { DashboardSummary } from '@/types'

export async function getDashboardSummary(farmId: number): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>(`/dashboard/${farmId}`)
  return data
}
