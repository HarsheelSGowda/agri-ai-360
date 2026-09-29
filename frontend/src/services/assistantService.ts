import { api } from './api'
import type { AssistantAskResponse, AssistantHistoryResponse } from '@/types'

export async function getAssistantHistory(): Promise<AssistantHistoryResponse> {
  const { data } = await api.get<AssistantHistoryResponse>('/assistant/messages')
  return data
}

export async function askAssistant(message: string, farmId?: number | null): Promise<AssistantAskResponse> {
  const { data } = await api.post<AssistantAskResponse>('/assistant/ask', { message, farm_id: farmId })
  return data
}

export async function resetAssistant(): Promise<AssistantHistoryResponse> {
  const { data } = await api.post<AssistantHistoryResponse>('/assistant/reset')
  return data
}
