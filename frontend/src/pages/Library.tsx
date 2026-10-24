import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import UploadZone from '../components/UploadZone'
import { Empty, ErrorBox, Skeleton, StatusBadge, fmtBytes, fmtDate } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'

export default function Library() {
  const [q, setQ] = useState(''), [status, setStatus] = useState(''), [sort, setSort] = useState('created_at'), [page, setPage] = useState(1)
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState<string | null>(null), [err, setErr] = useState<string | null>(null)
  const { data, error, loading, reload } = useAsync(() => api.listDocs({ q, status, sort, order: sort === 'filename' ? 'asc' : 'desc', page, page_size: 10 }), [q, status, sort, page])

  const active = data?.items.some((d) => d.status === 'processing' || d.status === 'uploaded')
  useEffect(() => { if (!active) return; const t = setInterval(() => void reload(true), 1500); return () => clearInterval(t) }, [active, reload])

  const upload = async (files: File[]) => {
    setBusy(true); setErr(null); setMsg(null)
    const notes: string[] = []
    for (const f of files) {
      try { const r = await api.upload(f); notes.push(r.duplicate ? `${f.name} was already uploaded.` : `${f.name} uploaded. Processing…`) }
      catch (e) { setErr(e instanceof Error ? e.message : 'Upload failed.') }
    }
    setMsg(notes.join(' ')); setBusy(false); void reload()
  }
  const act = async (fn: () => Promise<unknown>) => { try { await fn(); setErr(null) } catch (e) { setErr(e instanceof Error ? e.message : 'Action failed.') } void reload() }
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Documents</h1>
      <UploadZone onFiles={upload} busy={busy} />
      {msg && <p role="status" className="rounded-2xl bg-moss/40 px-4 py-2 text-sm">{msg}</p>}
      {err && <ErrorBox message={err} />}
      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="doc-q">Filter by filename</label>
        <input id="doc-q" className="field" placeholder="Filter by filename" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
        <label className="sr-only" htmlFor="doc-status">Status</label>
        <select id="doc-status" className="field" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">All statuses</option><option value="ready">Ready</option><option value="processing">Processing</option><option value="failed">Failed</option>
        </select>
        <label className="sr-only" htmlFor="doc-sort">Sort</label>
        <select id="doc-sort" className="field" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="created_at">Newest first</option><option value="filename">Name</option><option value="page_count">Pages</option>
        </select>
        <button className="btn-ghost ml-auto" onClick={() => void act(api.demo)}>Load synthetic demo documents</button>
      </div>
      {error ? <ErrorBox message={error} onRetry={reload} /> : loading && !data ? <Skeleton h="h-48" /> :
        data && data.items.length === 0 ? <Empty title={q || status ? 'No documents match these filters' : 'No documents yet'}>Upload a file above, or load the demo set (clearly labelled synthetic).</Empty> : (
        <div className="overflow-x-auto rounded-card bg-white/70">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-ink/60"><tr><th className="p-3">Name</th><th>Type</th><th>Uploaded</th><th>Pages</th><th>Status</th><th>Text</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>{data?.items.map((d) => (
              <tr key={d.id} className="border-t border-ink/10">
                <td className="p-3 font-medium"><Link className="underline" to={`/documents/${d.id}`}>{d.filename}</Link>{d.is_demo ? <span className="ml-2 text-xs text-ink/60">synthetic demo</span> : null}<div className="text-xs font-normal text-ink/60">{fmtBytes(d.size_bytes)}</div></td>
                <td className="uppercase">{d.kind}</td><td>{fmtDate(d.created_at)}</td><td>{d.page_count || '—'}</td>
                <td><StatusBadge status={d.status} />{d.status === 'failed' && <div className="max-w-xs text-xs text-red-800">{d.error}</div>}</td>
                <td>{d.status === 'ready' ? (d.ocr_pages ? `${d.ocr_pages} OCR page(s)` : 'native') : '—'}</td>
                <td className="space-x-2 whitespace-nowrap pr-3 text-right">
                  {d.status === 'failed' && <button className="btn-ghost" onClick={() => void act(() => api.reprocess(d.id))}>Reprocess</button>}
                  <button className="btn-ghost" onClick={() => { if (window.confirm(`Delete ${d.filename} and everything extracted from it?`)) void act(() => api.remove(d.id)) }}>Delete</button>
                </td></tr>))}</tbody>
          </table>
        </div>)}
      {data && data.total > data.page_size && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page} of {pages}</span>
          <button className="btn-ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>)}
    </div>
  )
}
