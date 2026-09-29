import { useEffect, useState } from 'react'
import { Bell, CloudSun, Sprout, Stethoscope, Store, Beaker, Droplets, AlertTriangle, CheckCheck, RefreshCw } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { getNotifications, generateNotifications, markNotificationRead, markAllNotificationsRead } from '@/services/notificationService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { NotificationCategory, NotificationItem } from '@/types'

const CATEGORY_ICON: Record<NotificationCategory, typeof Bell> = {
  WEATHER: CloudSun,
  CROP: Sprout,
  DISEASE: Stethoscope,
  MARKET: Store,
  FERTILIZER: Beaker,
  WATER: Droplets,
  RISK: AlertTriangle,
}

const PRIORITY_STYLE: Record<string, string> = {
  LOW: 'border-white/15 text-white/50',
  MEDIUM: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  HIGH: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
}

export function NotificationsPage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    getNotifications()
      .then(setItems)
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleGenerate = async () => {
    if (!activeFarm) return
    setGenerating(true)
    try {
      await generateNotifications(activeFarm.id)
      load()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  const handleMarkRead = async (id: number) => {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
    try {
      await markNotificationRead(id)
    } catch {
      /* optimistic update already applied; next load() will reconcile */
    }
  }

  const handleMarkAllRead = async () => {
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })))
    try {
      await markAllNotificationsRead()
    } catch {
      /* see handleMarkRead */
    }
  }

  if (loading) return <LoadingAnimation label="Loading notifications…" />
  if (error) return <ErrorState message={error} />

  const unreadCount = items.filter((n) => !n.is_read).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-white/50">{unreadCount} unread</p>
        <div className="flex gap-2">
          {activeFarm && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="btn-secondary flex items-center gap-1.5 px-4 py-2 text-xs disabled:opacity-60"
            >
              <RefreshCw size={13} className={generating ? 'animate-spin' : ''} /> Refresh for {activeFarm.name}
            </button>
          )}
          {unreadCount > 0 && (
            <button onClick={handleMarkAllRead} className="btn-secondary flex items-center gap-1.5 px-4 py-2 text-xs">
              <CheckCheck size={13} /> Mark all read
            </button>
          )}
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No notifications yet"
          description={
            activeFarm
              ? "Click \"Refresh\" to generate personalized alerts from your farm's current soil, weather, risk, disease and market data."
              : 'Select or create a farm, then refresh to generate personalized alerts.'
          }
        />
      ) : (
        <div className="space-y-2">
          {items.map((n) => {
            const Icon = CATEGORY_ICON[n.category]
            return (
              <GlassCard
                key={n.id}
                hover={false}
                className={`flex items-start gap-3 ${n.is_read ? 'opacity-60' : ''}`}
                onClick={() => !n.is_read && handleMarkRead(n.id)}
              >
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/5 text-white/60">
                  <Icon size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-white">{n.title}</p>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${PRIORITY_STYLE[n.priority]}`}>
                      {n.priority}
                    </span>
                    <span className="text-[10px] uppercase tracking-wide text-white/30">{n.category}</span>
                    {!n.is_read && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />}
                  </div>
                  <p className="mt-1 text-sm text-white/60">{n.message}</p>
                  <p className="mt-1.5 text-[11px] text-white/30">{new Date(n.created_at).toLocaleString()}</p>
                </div>
              </GlassCard>
            )
          })}
        </div>
      )}
    </div>
  )
}
