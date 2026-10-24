import { useRef, useState } from 'react'
import { AnswerText, CitationList } from '../components/Citations'
import { Empty, ErrorBox } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'
import type { ChatResponse } from '../types'

interface Turn { q: string; a?: ChatResponse; error?: string }
const EXAMPLES = ['What is the annual coverage limit?', 'Which services are excluded?', 'Which documents must be submitted with a claim?', 'What is the waiting period for maternity care?']

export default function Chat() {
  const docs = useAsync(() => api.listDocs({ status: 'ready', page_size: 100 }), [])
  const [scope, setScope] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [q, setQ] = useState(''), [busy, setBusy] = useState(false)
  const [active, setActive] = useState<Record<number, number | null>>({})
  const conv = useRef<string | undefined>(undefined)
  const ready = docs.data?.items ?? []

  const ask = async (question: string) => {
    if (!question.trim() || busy) return
    const i = turns.length
    setTurns((t) => [...t, { q: question }]); setQ(''); setBusy(true)
    try {
      const a = await api.chat(question, conv.current, scope ? [scope] : undefined)
      conv.current = a.conversation_id
      setTurns((t) => t.map((x, k) => (k === i ? { ...x, a } : x)))
    } catch (e) { setTurns((t) => t.map((x, k) => (k === i ? { ...x, error: e instanceof Error ? e.message : 'Failed' } : x))) }
    setBusy(false)
  }
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">Ask your documents</h1>
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="scope" className="text-sm">Search in</label>
        <select id="scope" className="field" value={scope} onChange={(e) => { setScope(e.target.value); conv.current = undefined; setTurns([]) }}>
          <option value="">All ready documents ({ready.length})</option>
          {ready.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
        </select>
        <span className="text-xs text-ink/60">Changing the scope starts a new conversation.</span>
      </div>
      {docs.error && <ErrorBox message={docs.error} onRetry={docs.reload} />}
      {!docs.loading && ready.length === 0 && <Empty title="No processed documents yet">Upload a document or load the demo set on the Documents page first.</Empty>}
      {turns.length === 0 && ready.length > 0 && (
        <div><p className="mb-2 text-xs uppercase text-ink/60">Example questions (not your activity)</p>
          <div className="flex flex-wrap gap-2">{EXAMPLES.map((e) => <button key={e} className="btn-ghost" onClick={() => void ask(e)}>{e}</button>)}</div></div>)}
      <div className="space-y-5" aria-live="polite">
        {turns.map((t, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-3xl bg-ink px-4 py-2 text-sm text-cream">{t.q}</p>
            {t.error ? <ErrorBox message={t.error} /> : !t.a ? <p className="text-sm text-ink/60">Searching the documents…</p> : (
              <div className={`max-w-3xl rounded-card p-4 text-sm ${t.a.abstained ? 'bg-sand' : 'bg-white/80'}`}>
                {t.a.conflict && <p className="mb-2 rounded-xl bg-sun/60 px-3 py-1.5 font-medium">Sources disagree. Both are shown below.</p>}
                <AnswerText text={t.a.answer} onCite={(n) => setActive((s) => ({ ...s, [i]: n }))} />
                <p className="mt-3 text-xs text-ink/60">
                  {t.a.mode === 'llm' ? 'Model-written summary. Check it against the sources.' : t.a.mode === 'extractive' ? 'Direct text from your documents. No language model was used, and nothing is interpreted.' : 'No answer given.'}
                  {' '}· {t.a.latency_ms} ms</p>
                {t.a.notes.map((n) => <p key={n} className="mt-1 text-xs text-ink/70">{n}</p>)}
                <CitationList citations={t.a.citations} active={active[i]} onSelect={(n) => setActive((s) => ({ ...s, [i]: s[i] === n ? null : n }))} />
              </div>)}
          </div>))}
      </div>
      <form className="sticky bottom-3 flex gap-2 rounded-full bg-sand/90 p-1.5 pl-4 shadow" onSubmit={(e) => { e.preventDefault(); void ask(q) }}>
        <label htmlFor="q" className="sr-only">Your question</label>
        <input id="q" className="min-w-0 flex-1 bg-transparent text-sm outline-none" placeholder="Ask a question about the selected documents" value={q} onChange={(e) => setQ(e.target.value)} maxLength={1000} />
        <button className="btn" disabled={busy || !q.trim()}>{busy ? 'Working…' : 'Ask'}</button>
      </form>
    </div>
  )
}
