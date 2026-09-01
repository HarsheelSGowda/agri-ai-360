import { useEffect, useState } from 'react'
import { FlaskRound, Database, Cpu } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { getModelPerformance } from '@/services/predictionService'
import { apiErrorMessage } from '@/services/api'
import type { ModelPerformanceResponse } from '@/types'
import clsx from 'clsx'

export function ModelLabPage() {
  const [data, setData] = useState<ModelPerformanceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getModelPerformance()
      .then((res) => !cancelled && setData(res))
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <LoadingAnimation label="Loading model lab data…" />
  if (error) return <ErrorState message={error} />
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <GlassCard className="flex items-center gap-3">
          <span className="rounded-lg bg-emerald-400/10 p-2 text-emerald-400">
            <Cpu size={18} />
          </span>
          <div>
            <p className="text-xs text-white/40">Active Model</p>
            <p className="font-semibold text-white">{data.active_model}</p>
          </div>
        </GlassCard>
        <GlassCard className="flex items-center gap-3">
          <span className="rounded-lg bg-sky-400/10 p-2 text-sky-400">
            <Database size={18} />
          </span>
          <div>
            <p className="text-xs text-white/40">Dataset Records</p>
            <p className="font-semibold text-white">{data.dataset_records.toLocaleString()}</p>
          </div>
        </GlassCard>
        <GlassCard className="flex items-center gap-3">
          <span className="rounded-lg bg-lime-400/10 p-2 text-lime-400">
            <FlaskRound size={18} />
          </span>
          <div>
            <p className="text-xs text-white/40">Training Status</p>
            <p className="font-semibold text-white">{data.models.some((m) => m.status === 'trained') ? 'Trained' : 'Not trained'}</p>
          </div>
        </GlassCard>
      </div>

      <GlassCard>
        <p className="mb-1 text-xs text-white/40">Dataset Source</p>
        <p className="text-sm text-white/70">{data.dataset_source}</p>
      </GlassCard>

      <GlassCard>
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">Model Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs uppercase tracking-wider text-white/40">
                <th className="py-2 pr-4">Algorithm</th>
                <th className="py-2 pr-4 text-right">Accuracy</th>
                <th className="py-2 pr-4 text-right">Precision</th>
                <th className="py-2 pr-4 text-right">Recall</th>
                <th className="py-2 pr-4 text-right">F1</th>
              </tr>
            </thead>
            <tbody>
              {data.models.map((m) => (
                <tr key={m.algorithm} className="border-b border-white/5">
                  <td className="py-3 pr-4 font-medium text-white">{m.algorithm}</td>
                  {m.status === 'trained' ? (
                    <>
                      <td className="py-3 pr-4 text-right font-mono text-emerald-300">{(m.accuracy! * 100).toFixed(2)}%</td>
                      <td className="py-3 pr-4 text-right font-mono text-white/70">{(m.precision! * 100).toFixed(2)}%</td>
                      <td className="py-3 pr-4 text-right font-mono text-white/70">{(m.recall! * 100).toFixed(2)}%</td>
                      <td className="py-3 pr-4 text-right font-mono text-white/70">{(m.f1_score! * 100).toFixed(2)}%</td>
                    </>
                  ) : (
                    <td colSpan={4} className="py-3 text-right text-xs italic text-white/30">
                      Not evaluated yet
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {data.feature_importance && (
        <GlassCard>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">Feature Importance (Active Model)</h3>
          <div className="space-y-2">
            {data.feature_importance.map((f) => (
              <div key={f.feature}>
                <div className="mb-1 flex justify-between text-xs text-white/60">
                  <span>{f.feature}</span>
                  <span>{(f.importance * 100).toFixed(1)}%</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-emerald-400" style={{ width: `${f.importance * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {data.confusion_matrix && (
        <GlassCard>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">Confusion Matrix (Active Model)</h3>
          <div className="overflow-x-auto">
            <table className="text-[10px] font-mono">
              <tbody>
                {data.confusion_matrix.matrix.map((row, i) => (
                  <tr key={data.confusion_matrix!.labels[i]}>
                    <td className="pr-2 text-white/40">{data.confusion_matrix!.labels[i].slice(0, 4)}</td>
                    {row.map((cell, j) => (
                      <td
                        key={j}
                        className={clsx(
                          'h-5 w-5 text-center align-middle',
                          i === j ? 'bg-emerald-400/30 text-emerald-200' : cell > 0 ? 'bg-rose-400/20 text-rose-200' : 'text-white/20',
                        )}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[11px] text-white/30">Rows = actual class, columns = predicted class, diagonal = correct predictions.</p>
        </GlassCard>
      )}
    </div>
  )
}
