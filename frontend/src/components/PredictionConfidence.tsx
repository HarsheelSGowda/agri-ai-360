import clsx from 'clsx'

const styles: Record<'HIGH' | 'MEDIUM' | 'LOW', string> = {
  HIGH: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
  MEDIUM: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
  LOW: 'text-rose-400 bg-rose-400/10 border-rose-400/30',
}

export function PredictionConfidence({ level }: { level: 'HIGH' | 'MEDIUM' | 'LOW' }) {
  return (
    <span
      title="Model confidence represents the model's prediction score and should not be interpreted as a guarantee of crop success."
      className={clsx('cursor-help rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide', styles[level])}
    >
      {level} CONFIDENCE
    </span>
  )
}
