import { api } from './api'
import type { RiskBreakdown } from '@/types'

export async function getRisk(farmId: number): Promise<RiskBreakdown> {
  const { data } = await api.get<RiskBreakdown>('/risk', { params: { farm_id: farmId } })
  return data
}
