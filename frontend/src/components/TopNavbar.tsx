import { LogOut, User as UserIcon } from 'lucide-react'
import { AIStatusBadge } from './AIStatusBadge'
import { NotificationBell } from './NotificationBell'
import { useAuth } from '@/hooks/useAuth'
import { useNavigate } from 'react-router-dom'

export function TopNavbar({ title }: { title: string }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <header className="flex items-center justify-between border-b border-white/10 bg-black/10 px-6 py-4 backdrop-blur-xl">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      <div className="flex items-center gap-4">
        <AIStatusBadge online modelName="Random Forest v1" />
        <NotificationBell />
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pl-1 pr-3 text-sm text-white/80">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-400/20 text-emerald-300">
            <UserIcon size={14} />
          </span>
          {user?.name ?? 'Farmer'}
        </div>
        <button
          onClick={() => {
            logout()
            navigate('/login')
          }}
          className="rounded-full border border-white/10 bg-white/5 p-2 text-white/60 transition-colors hover:border-rose-400/30 hover:text-rose-400"
          title="Log out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  )
}
