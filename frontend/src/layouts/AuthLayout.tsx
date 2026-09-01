import { Outlet, Link } from 'react-router-dom'
import { Leaf } from 'lucide-react'

export function AuthLayout() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-forest-950 bg-grid px-4">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-emerald-500/20 blur-[120px]" />
      <div className="relative z-10 w-full max-w-md">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-lime-400">
            <Leaf size={20} className="text-forest-950" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">AgriAI 360</span>
        </Link>
        <div className="glass-card p-8">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
