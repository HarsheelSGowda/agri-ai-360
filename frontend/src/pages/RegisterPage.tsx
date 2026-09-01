import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { registerUser } from '@/services/authService'
import { apiErrorMessage } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'
import { Loader2 } from 'lucide-react'

const languages = ['English', 'Hindi', 'Marathi', 'Telugu', 'Tamil', 'Kannada']

export function RegisterPage() {
  const navigate = useNavigate()
  const setAuth = useAuth((s) => s.setAuth)
  const [form, setForm] = useState({ name: '', email: '', password: '', location: '', preferred_language: 'English' })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setLoading(true)
    try {
      const res = await registerUser(form)
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
      <h1 className="text-xl font-semibold text-white">Create your account</h1>
      <p className="mt-1 text-sm text-white/50">Start getting AI-powered crop recommendations for your farm.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label-field">Name</label>
          <input required value={form.name} onChange={(e) => update('name', e.target.value)} className="input-field" placeholder="Ramesh Patil" />
        </div>
        <div>
          <label className="label-field">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
            className="input-field"
            placeholder="you@farm.com"
          />
        </div>
        <div>
          <label className="label-field">Password</label>
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => update('password', e.target.value)}
            className="input-field"
            placeholder="At least 6 characters"
          />
        </div>
        <div>
          <label className="label-field">Location</label>
          <input value={form.location} onChange={(e) => update('location', e.target.value)} className="input-field" placeholder="Nagpur, Maharashtra" />
        </div>
        <div>
          <label className="label-field">Preferred Language</label>
          <select
            value={form.preferred_language}
            onChange={(e) => update('preferred_language', e.target.value)}
            className="input-field"
          >
            {languages.map((l) => (
              <option key={l} value={l} className="bg-forest-900">
                {l}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

        <button type="submit" disabled={loading} className="btn-primary w-full py-3 disabled:opacity-60">
          {loading ? <Loader2 size={18} className="animate-spin" /> : 'Create Account'}
        </button>
      </form>

      <p className="mt-5 text-center text-xs text-white/40">
        Already have an account?{' '}
        <Link to="/login" className="text-emerald-300 hover:text-emerald-200">
          Log in
        </Link>
      </p>
    </div>
  )
}
