import { useEffect, useState } from 'react'
import { Bell } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getNotifications } from '@/services/notificationService'

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    function poll() {
      getNotifications(true)
        .then((res) => !cancelled && setUnreadCount(res.length))
        .catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 60_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return (
    <button
      onClick={() => navigate('/app/notifications')}
      className="relative rounded-full border border-white/10 bg-white/5 p-2 text-white/60 transition-colors hover:border-emerald-400/30 hover:text-emerald-300"
      title="Notifications"
    >
      <Bell size={16} />
      {unreadCount > 0 && (
        <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </button>
  )
}
