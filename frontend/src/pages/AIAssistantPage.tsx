import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { MessageCircle, Send, RotateCcw, Sparkles } from 'lucide-react'
import { GlassCard } from '@/components/GlassCard'
import { LoadingAnimation } from '@/components/LoadingAnimation'
import { ErrorState } from '@/components/ErrorState'
import { askAssistant, getAssistantHistory, resetAssistant } from '@/services/assistantService'
import { apiErrorMessage } from '@/services/api'
import { useFarmStore } from '@/hooks/useFarmStore'
import type { AssistantMessage } from '@/types'

const DEFAULT_SUGGESTIONS = [
  'Which crop is suitable for my soil?',
  'Why was this crop recommended?',
  'What does my soil condition mean?',
  'Why is my risk medium?',
  'How can I improve my soil?',
  'What should I check before irrigation?',
]

export function AIAssistantPage() {
  const activeFarm = useFarmStore((s) => s.activeFarm)
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUsedData, setLastUsedData] = useState<string[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getAssistantHistory()
      .then((res) => setMessages(res.messages))
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function sendMessage(text: string) {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    setError(null)
    setSending(true)
    setMessages((prev) => [...prev, { role: 'farmer', content: trimmed, created_at: new Date().toISOString() }])
    setDraft('')
    try {
      const res = await askAssistant(trimmed, activeFarm?.id ?? null)
      setMessages((prev) => [...prev, res.reply])
      setSuggestions(res.suggested_questions.length ? res.suggested_questions : DEFAULT_SUGGESTIONS)
      setLastUsedData(res.used_data)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    sendMessage(draft)
  }

  async function handleReset() {
    setError(null)
    try {
      const res = await resetAssistant()
      setMessages(res.messages)
      setLastUsedData([])
      setSuggestions(DEFAULT_SUGGESTIONS)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  if (loading) return <LoadingAnimation label="Loading assistant…" />

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <GlassCard hover={false}>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/50">
            <MessageCircle size={14} /> AI Agriculture Assistant
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-xs font-semibold text-sky-300">
              RULE-BASED, NOT AN LLM
            </span>
            {messages.length > 0 && (
              <button onClick={handleReset} className="btn-secondary flex items-center gap-1 px-3 py-1.5 text-xs">
                <RotateCcw size={12} /> Reset
              </button>
            )}
          </div>
        </div>

        {!activeFarm && (
          <div className="mb-3 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
            No farm selected — pick a farm from the top of the app so I can answer using its real data.
          </div>
        )}

        {error && <div className="mb-3"><ErrorState message={error} /></div>}

        <div ref={scrollRef} className="max-h-[26rem] space-y-3 overflow-y-auto rounded-xl bg-black/20 p-4">
          {messages.length === 0 ? (
            <p className="py-8 text-center text-sm text-white/40">
              Ask me about your crop recommendation, soil health, risk, irrigation, fertilizer, disease result or market
              price — I'll answer using {activeFarm ? activeFarm.name : 'your farm'}'s actual data.
            </p>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'farmer' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === 'farmer' ? 'bg-emerald-500/20 text-emerald-100' : 'bg-white/5 text-white/80'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))
          )}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-white/5 px-4 py-2.5 text-sm text-white/40">Thinking…</div>
            </div>
          )}
        </div>

        {lastUsedData.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-white/30">
            <Sparkles size={11} /> Answered using: {lastUsedData.join(', ')}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="input-field"
            placeholder="Ask about your farm's soil, risk, irrigation, fertilizer, disease or market price…"
            disabled={sending}
          />
          <button type="submit" disabled={sending || !draft.trim()} className="btn-secondary px-4 disabled:opacity-50">
            <Send size={16} />
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={sending}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/60 transition-colors hover:border-emerald-400/30 hover:text-emerald-300 disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        <p className="mt-3 text-[11px] text-white/30">
          This assistant is rule-based, not a language model — no LLM/RAG API is configured in this project. It answers
          only from your farm's real, already-computed data (soil health, weather, risk, disease, fertilizer, market
          price, crop-recommendation explanation) and says so when data is missing, rather than guessing.
        </p>
      </GlassCard>
    </div>
  )
}
