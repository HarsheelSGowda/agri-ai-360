import { Sprout, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { CropRankingItem } from '@/types'
import { PredictionConfidence } from './PredictionConfidence'

export function AIRecommendationCard({ top }: { top: CropRankingItem }) {
  return (
    <div className="glass-card relative overflow-hidden border-emerald-400/20 p-8">
      <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-emerald-500/20 blur-[100px]" />
      <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-widest text-emerald-300/80">
            <Sprout size={14} />
            AI Recommendation
          </div>
          <h2 className="glow-text text-4xl font-bold capitalize tracking-tight text-white">{top.crop}</h2>
          <div className="mt-3 flex items-center gap-3">
            <span className="font-mono text-2xl font-semibold text-emerald-300">{(top.probability * 100).toFixed(1)}%</span>
            <PredictionConfidence level={top.confidence} />
          </div>
        </div>
        <Link to={`/app/crop-recommendation/${encodeURIComponent(top.crop)}`} className="btn-primary shrink-0">
          Why this crop? <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  )
}
