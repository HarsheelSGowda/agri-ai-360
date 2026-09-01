import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { loginUser } from '@/services/authService'
import { apiErrorMessage } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'
import { Loader2 } from 'lucide-react'

export function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuth((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await loginUser({ email, password })
      setAuth(res.user, res.access_token)
      navigate('/app')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-white">Welcome back</h1>
      <p className="mt-1 text-sm text-white/50">Log in to access your farm intelligence dashboard.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label-field">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-field"
            placeholder="you@farm.com"
          />
        </div>
        <div>
          <label className="label-field">Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-field"
            placeholder="••••••••"
          />
        </div>

        {error && <p className="rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

        <button type="submit" disabled={loading} className="btn-primary w-full py-3 disabled:opacity-60">
          {loading ? <Loader2 size={18} className="animate-spin" /> : 'Log In'}
        </button>
      </form>

      <div className="mt-5 flex items-center justify-between text-xs">
        <Link to="/forgot-password" className="text-white/40 hover:text-emerald-300">
          Forgot password?
        </Link>
        <Link to="/register" className="text-emerald-300 hover:text-emerald-200">
          Create an account
        </Link>
      </div>
    </div>
  )
}
