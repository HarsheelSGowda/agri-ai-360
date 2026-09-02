import { useEffect, useState } from 'react'
import { Stethoscope, Upload, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { getDiseaseOptions, diagnoseDisease } from '@/services/diseaseService'
import { apiErrorMessage } from '@/services/api'
import type { DiseaseDiagnosisResponse, DiseaseOptionsResponse } from '@/types'

const LOW_CONFIDENCE_THRESHOLD = 0.4

export function CropDoctorPage() {
  const [options, setOptions] = useState<DiseaseOptionsResponse | null>(null)
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [result, setResult] = useState<DiseaseDiagnosisResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getDiseaseOptions()
      .then((res) => !cancelled && setOptions(res))
      .catch((err) => !cancelled && setError(apiErrorMessage(err)))
      .finally(() => !cancelled && setOptionsLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const handleFileChange = (selected: File | null) => {
    setFile(selected)
    setResult(null)
    setError(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(selected ? URL.createObjectURL(selected) : null)
  }

  const handleDiagnose = async () => {
    if (!file) return
    setError(null)
    setLoading(true)
    try {
      const res = await diagnoseDisease(file)
      setResult(res)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const modelReady = (options?.active_model_accuracy ?? null) !== null

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <GlassCard className="text-center">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-400/10 text-sky-400">
          <Stethoscope size={26} />
        </span>
        <h2 className="text-xl font-semibold text-white">AI Crop Doctor</h2>

        {optionsLoading ? (
          <p className="mt-3 text-sm text-white/40">Loading model…</p>
        ) : modelReady ? (
          <>
            <span className="mt-2 inline-block rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
              LIVE — {options?.active_model} ({((options?.active_model_accuracy ?? 0) * 100).toFixed(1)}% test accuracy)
            </span>
            <p className="mx-auto mt-4 max-w-md text-sm text-white/50">
              Upload a photo of a leaf and a real trained image classifier (MobileNetV3 feature extraction +{' '}
              {options?.active_model?.replace('disease_', '').replace('_', ' ')}) will identify the crop and condition. Currently
              supports <span className="text-white/70">{options?.supported_crops.join(', ')}</span> — other crops aren't trained yet and
              will say so honestly rather than guessing.
            </p>

            <label className="mt-6 flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-white/15 bg-white/[0.02] py-10 transition-colors hover:border-emerald-400/30 hover:bg-white/[0.04]">
              {previewUrl ? (
                <img src={previewUrl} alt="Selected leaf" className="h-32 w-32 rounded-lg object-cover" />
              ) : (
                <Upload size={22} className="text-white/40" />
              )}
              <span className="text-xs text-white/40">{file ? file.name : 'Click to select a leaf photo (JPEG/PNG/WebP)'}</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
              />
            </label>

            {error && <p className="mt-4 rounded-lg bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</p>}

            <button
              onClick={handleDiagnose}
              disabled={!file || loading}
              className="btn-primary mt-4 px-6 py-3 disabled:opacity-50"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : 'Diagnose'}
            </button>
          </>
        ) : (
          <>
            <span className="mt-2 inline-block rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300">
              MODEL NOT TRAINED
            </span>
            <p className="mx-auto mt-4 max-w-md text-sm text-white/50">
              Run <code className="text-white/70">python ml/disease_detection/train.py</code> to train the disease model.
            </p>
          </>
        )}
      </GlassCard>

      {result && (
        <GlassCard hover={false}>
          <h3 className="mb-4 text-xs uppercase tracking-wider text-white/50">Diagnosis</h3>

          <div className="flex items-center gap-3">
            {result.top_prediction.is_healthy ? (
              <CheckCircle2 size={28} className="text-emerald-400" />
            ) : (
              <AlertTriangle size={28} className="text-amber-400" />
            )}
            <div>
              <p className="text-lg font-semibold capitalize text-white">
                {result.top_prediction.crop} — {result.top_prediction.condition}
              </p>
              <p className="text-sm text-white/50">Confidence: {(result.top_prediction.probability * 100).toFixed(1)}%</p>
            </div>
          </div>

          {result.top_prediction.probability < LOW_CONFIDENCE_THRESHOLD && (
            <p className="mt-4 rounded-lg bg-amber-400/10 px-3 py-2 text-sm text-amber-300">
              Low confidence — this photo may not clearly show one of the {result.supported_crops.length} supported crops
              ({result.supported_crops.join(', ')}), or the leaf/lighting/angle may be unclear. Treat this result cautiously.
            </p>
          )}

          {result.alternatives.length > 0 && (
            <div className="mt-4 space-y-1.5 border-t border-white/10 pt-4">
              <p className="mb-2 text-[11px] uppercase tracking-wider text-white/40">Other possibilities</p>
              {result.alternatives.map((alt) => (
                <div key={`${alt.crop}-${alt.condition}`} className="flex items-center justify-between text-sm text-white/60">
                  <span className="capitalize">
                    {alt.crop} — {alt.condition}
                  </span>
                  <span className="font-mono text-xs">{(alt.probability * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}

          <p className="mt-4 text-[11px] text-white/30">
            Model: {result.model_used} ({(result.model_accuracy * 100).toFixed(1)}% test accuracy) · trained on real PlantVillage leaf
            images via a frozen, ImageNet-pretrained MobileNetV3 feature extractor — not a guarantee, and not a substitute for an
            agronomist for anything consequential.
          </p>
        </GlassCard>
      )}
    </div>
  )
}
