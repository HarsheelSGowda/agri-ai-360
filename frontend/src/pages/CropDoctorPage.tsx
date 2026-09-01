import { Stethoscope, Upload } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'

const steps = ['Image', 'Computer Vision', 'Disease Detection', 'Confidence', 'Recommended Action']

export function CropDoctorPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <GlassCard className="text-center">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-400/10 text-sky-400">
          <Stethoscope size={26} />
        </span>
        <h2 className="text-xl font-semibold text-white">AI Crop Doctor</h2>
        <span className="mt-2 inline-block rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300">
          COMING IN PHASE 2
        </span>
        <p className="mx-auto mt-4 max-w-md text-sm text-white/50">
          Upload a photo of a crop leaf and the planned computer-vision pipeline will identify disease type, confidence and a recommended
          action. No disease-detection model is trained or wired up yet — this is the interface shell only.
        </p>

        <label className="mt-6 flex cursor-not-allowed flex-col items-center gap-2 rounded-xl border border-dashed border-white/15 bg-white/[0.02] py-10 opacity-60">
          <Upload size={22} className="text-white/40" />
          <span className="text-xs text-white/40">Upload disabled until Phase 2 model is trained</span>
          <input type="file" disabled className="hidden" />
        </label>
      </GlassCard>

      <GlassCard hover={false}>
        <h3 className="mb-3 text-xs uppercase tracking-wider text-white/50">Planned Workflow</h3>
        <div className="flex flex-wrap items-center gap-2 text-sm text-white/60">
          {steps.map((s, i) => (
            <span key={s} className="flex items-center gap-2">
              <span className="rounded-lg bg-white/5 px-3 py-1.5">{s}</span>
              {i < steps.length - 1 && <span className="text-white/20">→</span>}
            </span>
          ))}
        </div>
      </GlassCard>
    </div>
  )
}
