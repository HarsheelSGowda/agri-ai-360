import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Sprout,
  FlaskConical,
  CloudSun,
  BrainCircuit,
  FlaskRound,
  AlertTriangle,
  History,
  MessageCircle,
  Stethoscope,
  Settings,
  Compass,
  Leaf,
  Store,
  Beaker,
  Bell,
  Satellite,
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/crop-recommendation', label: 'Crop Recommendation', icon: Sprout },
  { to: '/app/soil', label: 'Soil Intelligence', icon: FlaskConical },
  { to: '/app/weather', label: 'Weather', icon: CloudSun },
  { to: '/app/real-time', label: 'Real-Time Intelligence', icon: Satellite },
  { to: '/app/explanation', label: 'AI Explanation', icon: BrainCircuit },
  { to: '/app/model-lab', label: 'Model Lab', icon: FlaskRound },
  { to: '/app/risk', label: 'Risk', icon: AlertTriangle },
  { to: '/app/history', label: 'History', icon: History },
  { to: '/app/assistant', label: 'AI Assistant', icon: MessageCircle },
  { to: '/app/crop-doctor', label: 'Crop Doctor', icon: Stethoscope },
  { to: '/app/market-prices', label: 'Market Prices', icon: Store },
  { to: '/app/fertilizer', label: 'Fertilizer Advisor', icon: Beaker },
  { to: '/app/notifications', label: 'Notifications', icon: Bell },
  { to: '/app/roadmap', label: 'AI Roadmap', icon: Compass },
  { to: '/app/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-white/10 bg-black/20 px-4 py-6 backdrop-blur-xl lg:flex">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-lime-400">
          <Leaf size={18} className="text-forest-950" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-white">AgriAI 360</p>
          <p className="text-[10px] uppercase tracking-widest text-white/40">Decision Support</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/20'
                  : 'text-white/55 hover:bg-white/5 hover:text-white border border-transparent',
              )
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
