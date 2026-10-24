import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Empty, ErrorBox, Skeleton } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'

const LABEL: Record<string, string> = { coverage_limit: 'Coverage limit', deductible: 'Deductible', out_of_pocket_max: 'Out-of-pocket maximum', copay: 'Copay', coinsurance: 'Coinsurance',
  waiting_period: 'Waiting period', deadline: 'Deadline', visit_limit: 'Visit limit', eligibility: 'Eligibility', exclusion: 'Exclusion', prior_authorization: 'Prior authorization', required_document: 'Required documents' }

export default function Insights() {
  const [sp, setSp] = useSearchParams()
  const docs = useAsync(() => api.listDocs({ status: 'ready', page_size: 100 }), [])
  const id = sp.get('doc') ?? docs.data?.items[0]?.id ?? ''
  const ins = useAsync(() => (id ? api.insights(id) : Promise.resolve(null)), [id])
  const [open, setOpen] = useState<string | null>(null)
  if (docs.error) return <ErrorBox message={docs.error} onRetry={docs.reload} />
  if (!docs.loading && !docs.data?.items.length) return <Empty title="No processed documents">Upload a document first.</Empty>
  const d = ins.data
  const groups = d ? Object.entries(d.fields.reduce<Record<string, typeof d.fields>>((m, f) => ((m[f.field] ??= []).push(f), m), {})) : []
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Document insights</h1>
      <label className="text-sm">Document <select className="field ml-2" value={id} onChange={(e) => setSp({ doc: e.target.value })}>{docs.data?.items.map((x) => <option key={x.id} value={x.id}>{x.filename}</option>)}</select></label>
      {ins.loading ? <Skeleton h="h-48" /> : ins.error ? <ErrorBox message={ins.error} onRetry={ins.reload} /> : d && (<>
        <section className="card bg-sky"><h2 className="font-semibold">Classification <span className="text-xs font-normal">(inferred, not extracted)</span></h2>
          <p className="mt-1 text-lg">{d.classification.label.replace('_', ' ')}</p><p className="text-xs text-ink/70">{d.classification.method}. Share of keyword hits: {d.classification.score}.</p></section>
        {d.ocr_pages.length > 0 && <p className="rounded-2xl bg-sun/50 p-3 text-sm">Pages {d.ocr_pages.join(', ')} came from OCR and may contain reading errors.</p>}
        <section><h2 className="mb-2 text-xl font-semibold">Extracted fields</h2>
          {groups.length === 0 ? <Empty title="No standard fields were found in this document">Fields are only listed when matching text exists.</Empty> :
            <div className="space-y-3">{groups.map(([k, fs]) => (
              <div key={k} className="card bg-white/80"><h3 className="font-semibold">{LABEL[k] ?? k}</h3>
                <ul className="mt-2 space-y-2 text-sm">{fs.map((f, i) => { const key = `${k}${i}`; return (
                  <li key={key}><div className="flex items-center justify-between gap-2"><span>{f.value}</span>
                    <button className="btn-ghost" aria-expanded={open === key} onClick={() => setOpen(open === key ? null : key)}>Source · p.{f.page_no}</button></div>
                    {open === key && <div className="mt-2 rounded-xl bg-sand p-3"><blockquote className="italic">{f.evidence}</blockquote>
                      <Link className="mt-1 inline-block underline" to={`/documents/${id}?page=${f.page_no}&hl=${encodeURIComponent(f.evidence.slice(0, 120))}`}>Open page</Link>
                      <p className="mt-1 text-xs text-ink/60">Found by a {f.method} match. Not verified by a person.</p></div>}</li>) })}</ul></div>))}</div>}
        </section>
        {d.definitions.length > 0 && <section><h2 className="mb-2 text-xl font-semibold">Defined terms</h2><ul className="space-y-1 text-sm">{d.definitions.map((x, i) => <li key={i}><strong>{x.term}</strong>: {x.definition} <span className="text-ink/60">(p.{x.page_no})</span></li>)}</ul></section>}
        <section><h2 className="mb-2 text-xl font-semibold">Entities</h2><div className="flex flex-wrap gap-2">{d.entities.map((e, i) => <span key={i} className="rounded-full bg-white/80 px-3 py-1 text-xs">{e.label}: {e.text} · p.{e.page_no}</span>)}</div></section>
      </>)}
    </div>
  )
}
