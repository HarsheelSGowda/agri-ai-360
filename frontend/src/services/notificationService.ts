import { api } from './api'
import type { NotificationItem } from '@/types'

export async function getNotifications(unreadOnly = false): Promise<NotificationItem[]> {
  const { data } = await api.get<NotificationItem[]>('/notifications', { params: unreadOnly ? { unread_only: true } : undefined })
  return data
}

export async function generateNotifications(farmId: number): Promise<{ created: number; notifications: NotificationItem[] }> {
  const { data } = await api.post('/notifications/generate', null, { params: { farm_id: farmId } })
  return data
}

export async function markNotificationRead(id: number): Promise<NotificationItem> {
  const { data } = await api.patch<NotificationItem>(`/notifications/${id}/read`)
  return data
}

export async function markAllNotificationsRead(): Promise<{ updated: number }> {
  const { data } = await api.patch('/notifications/read-all')
  return data
}
