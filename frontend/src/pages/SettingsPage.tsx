import { GlassCard } from '@/components/GlassCard'
import { useAuth } from '@/hooks/useAuth'

export function SettingsPage() {
  const user = useAuth((s) => s.user)

  return (
    <div className="mx-auto max-w-lg">
      <GlassCard>
        <h2 className="mb-6 text-lg font-semibold text-white">Account Settings</h2>
        <div className="space-y-4 text-sm">
          <Row label="Name" value={user?.name ?? '—'} />
          <Row label="Email" value={user?.email ?? '—'} />
          <Row label="Location" value={user?.location ?? '—'} />
          <Row label="Preferred Language" value={user?.preferred_language ?? '—'} />
        </div>
        <p className="mt-6 text-[11px] text-white/30">Profile editing is not yet implemented in this MVP build.</p>
      </GlassCard>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-white/5 pb-3">
      <span className="text-white/40">{label}</span>
      <span className="font-medium text-white">{value}</span>
    </div>
  )
}
