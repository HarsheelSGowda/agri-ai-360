import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/Sidebar'
import { TopNavbar } from '@/components/TopNavbar'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { useFarmStore } from '@/hooks/useFarmStore'
import { listFarms } from '@/services/farmService'

const titles: Record<string, string> = {
  '/app': 'Dashboard',
  '/app/crop-recommendation': 'Crop Recommendation',
  '/app/soil': 'Soil Intelligence',
  '/app/weather': 'Weather Intelligence',
  '/app/real-time': 'Real-Time Agri Intelligence',
  '/app/explanation': 'Explainable AI',
  '/app/model-lab': 'Model Lab · Research Center',
  '/app/risk': 'Risk Dashboard',
  '/app/history': 'Recommendation History',
  '/app/assistant': 'AI Agriculture Assistant',
  '/app/crop-doctor': 'AI Crop Doctor',
  '/app/market-prices': 'Market Price Intelligence',
  '/app/fertilizer': 'Fertilizer Advisor',
  '/app/notifications': 'Notifications',
  '/app/roadmap': 'AI Roadmap',
  '/app/settings': 'Settings',
  '/app/farms/new': 'Create Farm',
}

export function AppLayout() {
  const location = useLocation()
  const title =
    titles[location.pathname] ??
    (location.pathname.startsWith('/app/crop-recommendation/') ? 'Recommendation Detail' : 'AgriAI 360')
  const { farms, setFarms } = useFarmStore()
  const [farmsHydrated, setFarmsHydrated] = useState(false)

  // Zustand state is in-memory only, so a full page load/refresh (or a
  // direct link into a sub-page) starts with an empty farm list. Hydrate it
  // once here so every page under /app can rely on `activeFarm` being set
  // without duplicating this fetch in each page.
  useEffect(() => {
    let cancelled = false
    if (farms.length > 0) {
      setFarmsHydrated(true)
      return
    }
    listFarms()
      .then((list) => !cancelled && setFarms(list))
      .catch(() => {
        /* dashboard/page-level error states handle a failed fetch */
      })
      .finally(() => !cancelled && setFarmsHydrated(true))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-screen bg-forest-950">
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <TopNavbar title={title} />
        <main className="flex-1 overflow-y-auto bg-grid px-6 py-8">
          {farmsHydrated ? <Outlet /> : <LoadingAnimation label="Loading your farm data…" />}
        </main>
      </div>
    </div>
  )
}
