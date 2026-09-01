import { Link } from 'react-router-dom'
import type { CropRankingItem } from '@/types'
import { PredictionConfidence } from './PredictionConfidence'
import clsx from 'clsx'

const medals = ['🥇', '🥈', '🥉']

export function CropRanking({ crops }: { crops: CropRankingItem[] }) {
  return (
    <div className="space-y-3">
      {crops.map((item, idx) => (
        <Link
          key={item.crop}
          to={`/app/crop-recommendation/${encodeURIComponent(item.crop)}`}
          className={clsx(
            'flex items-center justify-between rounded-xl border px-4 py-3.5 transition-colors',
            idx === 0
              ? 'border-emerald-400/30 bg-emerald-400/10 hover:bg-emerald-400/15'
              : 'border-white/10 bg-white/[0.03] hover:bg-white/[0.06]',
          )}
        >
          <div className="flex items-center gap-3">
            <span className="w-6 text-center text-lg">{medals[idx] ?? idx + 1}</span>
            <span className="font-medium capitalize text-white">{item.crop}</span>
          </div>
          <div className="flex items-center gap-3">
            <PredictionConfidence level={item.confidence} />
            <span className="w-14 text-right font-mono text-sm font-semibold text-white">
              {(item.probability * 100).toFixed(1)}%
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
