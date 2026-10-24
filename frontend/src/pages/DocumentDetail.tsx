import { useEffect } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ErrorBox, Skeleton, StatusBadge, fmtBytes, fmtDate } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'

function Highlighted({ text, hl }: { text: string; hl: string }) {
  const i = hl ? text.toLowerCase().indexOf(hl.toLowerCase()) : -1
  if (i < 0) return <>{text}</>
  return <>{text.slice(0, i)}<mark className="bg-sun">{text.slice(i, i + hl.length)}</mark>{text.slice(i + hl.length)}</>
}

export default function DocumentDetail() {
  const { id = '' } = useParams()
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const doc = useAsync(() => api.getDoc(id), [id])
  const text = useAsync(() => api.pages(id), [id])
  const target = sp.get('page'), hl = sp.get('hl') ?? ''
  useEffect(() => { if (target && text.data) document.getElementById(`page-${target}`)?.scrollIntoView({ block: 'center' }) }, [target, text.data])
  if (doc.error) return <ErrorBox message={doc.error} onRetry={doc.reload} />
  if (!doc.data) return <Skeleton h="h-48" />
  const d = doc.data
  return (
    <div className="space-y-5">
      <Link to="/documents" className="text-sm underline">← All documents</Link>
      <div className="flex flex-wrap items-center gap-3"><h1 className="text-3xl font-semibold">{d.filename}</h1><StatusBadge status={d.status} />{d.is_demo ? <span className="text-sm text-ink/60">Synthetic demo document</span> : null}</div>
      <section className="card bg-sand" aria-label="Processing diagnostics">
        <h2 className="mb-2 font-semibold">Processing diagnostics</h2>
        <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
          {([['Size', fmtBytes(d.size_bytes)], ['Uploaded', fmtDate(d.created_at)], ['Pages', d.page_count], ['Chunks', d.chunk_count], ['OCR pages', d.ocr_pages],
            ['Extractor', d.extractor ?? '—'], ['Duration', d.duration_ms == null ? '—' : `${d.duration_ms} ms`], ['Last stage', d.job?.stage ?? '—'], ['Inferred type', d.doc_type ? `${d.doc_type} (inferred)` : '—']] as [string, string | number][])
            .map(([k, v]) => <div key={k} className="flex justify-between gap-2"><dt className="text-ink/60">{k}</dt><dd className="font-medium">{v}</dd></div>)}
        </dl>
        {d.error && <p role="alert" className="mt-3 rounded-xl bg-rose/60 p-3 text-sm">{d.error}</p>}
        <div className="mt-3 flex gap-2">
          {d.status === 'failed' && <button className="btn" onClick={async () => { await api.reprocess(id); void doc.reload() }}>Reprocess</button>}
          <Link className="btn-ghost" to={`/insights?doc=${id}`}>View insights</Link>
          <button className="btn-ghost" onClick={async () => { if (window.confirm('Delete this document and its extracted data?')) { await api.remove(id); nav('/documents') } }}>Delete</button>
        </div>
      </section>
      <section aria-label="Extracted text" className="space-y-3">
        <h2 className="text-xl font-semibold">Extracted text</h2>
        <p className="text-sm text-ink/70">OCR text can contain mistakes. Check it against the original page.</p>
        {text.loading ? <Skeleton h="h-40" /> : text.error ? <ErrorBox message={text.error} /> : text.data?.pages.length === 0 ? <p>No text extracted.</p> :
          text.data?.pages.map((p) => (
            <article id={`page-${p.page_no}`} key={p.page_no} className={`rounded-card bg-white/80 p-4 ${String(p.page_no) === target ? 'ring-2 ring-ink' : ''}`}>
              <header className="mb-2 flex items-center justify-between text-xs uppercase text-ink/60"><span>Page {p.page_no}</span>
                <span>{p.source === 'ocr' ? `OCR${p.ocr_conf != null ? ` · confidence ${p.ocr_conf.toFixed(0)}/100` : ''}` : p.source === 'native' ? 'Native PDF text' : 'No text found'}</span></header>
              <p className="whitespace-pre-line text-sm leading-relaxed"><Highlighted text={p.text} hl={String(p.page_no) === target ? hl : ''} /></p>
            </article>))}
      </section>
    </div>
  )
}
