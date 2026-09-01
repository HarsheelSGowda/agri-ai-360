import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck } from 'lucide-react'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSent(true)
  }

  if (sent) {
    return (
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-400/10">
          <MailCheck size={22} className="text-emerald-400" />
        </div>
        <h1 className="text-lg font-semibold text-white">Check your email</h1>
        <p className="mt-2 text-sm text-white/50">
          If an account exists for <span className="text-white/80">{email}</span>, a reset link has been sent.
        </p>
        <p className="mt-4 text-xs text-white/30">
          (Password-reset delivery is not wired to a real email provider yet in this MVP build.)
        </p>
        <Link to="/login" className="btn-secondary mt-6 inline-flex px-6 py-2.5 text-sm">
          Back to login
        </Link>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-white">Reset your password</h1>
      <p className="mt-1 text-sm text-white/50">Enter your email and we'll send you a reset link.</p>

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
        <button type="submit" className="btn-primary w-full py-3">
          Send reset link
        </button>
      </form>

      <p className="mt-5 text-center text-xs text-white/40">
        <Link to="/login" className="text-emerald-300 hover:text-emerald-200">
          Back to login
        </Link>
      </p>
    </div>
  )
}
