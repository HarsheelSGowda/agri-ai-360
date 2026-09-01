import { useState } from 'react'
import type { FormEvent } from 'react'
import { MessageCircle, Send } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'

interface Message {
  role: 'farmer' | 'ai'
  text: string
}

const seedMessages: Message[] = [
  { role: 'farmer', text: 'Why is cotton recommended?' },
  { role: 'ai', text: 'Your current soil and weather conditions are favorable for cotton.' },
]

export function AIAssistantPage() {
  const [messages] = useState<Message[]>(seedMessages)
  const [draft, setDraft] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setDraft('')
  }

  return (
    <div className="mx-auto max-w-2xl">
      <GlassCard hover={false}>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <MessageCircle size={14} /> AI Agriculture Assistant
          </div>
          <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300">
            DEVELOPMENT PREVIEW
          </span>
        </div>

        <div className="space-y-3 rounded-xl bg-black/20 p-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'farmer' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                  m.role === 'farmer' ? 'bg-emerald-500/20 text-emerald-100' : 'bg-white/5 text-white/80'
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="input-field"
            placeholder="This assistant is not connected to a real LLM/RAG backend yet…"
            disabled
          />
          <button type="submit" disabled className="btn-secondary px-4 opacity-50">
            <Send size={16} />
          </button>
        </form>
        <p className="mt-3 text-[11px] text-white/30">
          This is a UI shell only. No language model is wired up in this MVP — responses shown above are static examples, not live AI
          output.
        </p>
      </GlassCard>
    </div>
  )
}
