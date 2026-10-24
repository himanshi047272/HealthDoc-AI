import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Empty, ErrorBox } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'
import type { SearchResult } from '../types'

export default function Search() {
  const [sp] = useSearchParams()
  const [q, setQ] = useState(sp.get('q') ?? ''), [mode, setMode] = useState('hybrid'), [doc, setDoc] = useState(''), [type, setType] = useState('')
  const [from, setFrom] = useState(''), [to, setTo] = useState('')
  const [res, setRes] = useState<{ latency_ms: number; total: number; results: SearchResult[] } | null>(null)
  const [error, setError] = useState<string | null>(null), [busy, setBusy] = useState(false)
  const docs = useAsync(() => api.listDocs({ status: 'ready', page_size: 100 }), [])

  const run = async (query = q) => {
    if (!query.trim()) return
    setBusy(true); setError(null)
    try {
      setRes(await api.search({ query, mode, document_ids: doc ? [doc] : undefined, doc_type: type || undefined,
        date_from: from ? new Date(from).toISOString() : undefined, date_to: to ? new Date(`${to}T23:59:59`).toISOString() : undefined, k: 10 }))
    } catch (e) { setError(e instanceof Error ? e.message : 'Search failed.') }
    setBusy(false)
  }
  useEffect(() => { if (sp.get('q')) void run(sp.get('q') ?? '') }, []) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">Search</h1>
      <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); void run() }}>
        <label className="flex-1 text-sm">Query<input className="field mt-1 w-full" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <label className="text-sm">Method<select className="field mt-1 block" value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="hybrid">Hybrid</option><option value="keyword">Keyword (BM25)</option><option value="semantic">Vector similarity</option></select></label>
        <label className="text-sm">Document<select className="field mt-1 block" value={doc} onChange={(e) => setDoc(e.target.value)}><option value="">All</option>{docs.data?.items.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}</select></label>
        <label className="text-sm">Type<select className="field mt-1 block" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Any</option><option value="insurance_policy">Insurance policy</option><option value="benefits_guide">Benefits guide</option><option value="claims_guide">Claims guide</option></select></label>
        <label className="text-sm">From<input type="date" className="field mt-1 block" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label className="text-sm">To<input type="date" className="field mt-1 block" value={to} onChange={(e) => setTo(e.target.value)} /></label>
        <button className="btn" disabled={busy || !q.trim()}>{busy ? 'Searching…' : 'Search'}</button>
      </form>
      {error && <ErrorBox message={error} />}
      {res && <p className="text-sm text-ink/70" role="status">{res.total} result(s) in {res.latency_ms} ms (measured on the server)</p>}
      {res && res.total === 0 && <Empty title="No matching passages">Try different words or a different method.</Empty>}
      <ul className="space-y-3">{res?.results.map((r) => (
        <li key={r.chunk_id} className="card bg-white/80 text-sm">
          <div className="mb-1 flex flex-wrap items-center justify-between gap-2 font-medium"><span>{r.filename} · page {r.page_no}{r.source === 'ocr' ? ' · OCR' : ''}</span>
            <span className="text-xs font-normal text-ink/60">score {r.score} · bm25 {r.bm25.toFixed(2)} · vector {r.dense.toFixed(2)}</span></div>
          <p>{r.passage}</p>
          <Link className="mt-2 inline-block underline" to={`/documents/${r.document_id}?page=${r.page_no}&hl=${encodeURIComponent(r.passage.slice(0, 80))}`}>Open page {r.page_no}</Link>
        </li>))}</ul>
    </div>
  )
}
