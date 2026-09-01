import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { RiskCard } from '@/components/RiskCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { EmptyState } from '@/components/EmptyState'
import { getRisk } from '@/services/riskService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { RiskBreakdown } from '@/types'

export function RiskPage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [risk, setRisk] = useState<RiskBreakdown | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!activeFarm) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    getRisk(activeFarm.id)
      .then((res) => !cancelled && setRisk(res))
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [activeFarm])

  if (!activeFarm) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="No active farm"
        description="Create a farm to see its risk breakdown."
        action={
          <Link to="/app/farms/new" className="btn-primary mt-2 px-5 py-2.5 text-sm">
            Create Farm
          </Link>
        }
      />
    )
  }

  if (loading) return <LoadingAnimation label="Computing risk summary…" />
  if (error) return <ErrorState message={error} />
  if (!risk) return null

  return (
    <div className="mx-auto max-w-md">
      <RiskCard risk={risk} />
    </div>
  )
}
