import { Link } from 'react-router-dom'
import Chart from '../components/Chart'
import { greeting } from '../components/Layout'
import { Empty, ErrorBox, Skeleton, Stat, StatusBadge, fmtDate, pct } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'

export default function Overview() {
  const { data: a, error, loading, reload } = useAsync(api.analytics)
  if (error) return <ErrorBox message={error} onRetry={reload} />
  if (loading || !a) return <div className="grid gap-4 md:grid-cols-2"><Skeleton /><Skeleton /><Skeleton /><Skeleton /></div>
  const empty = a.documents_total === 0
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-4xl font-semibold tracking-tight">{greeting()}</h1>
        <p className="mt-1 max-w-xl text-sm text-ink/70">
          {empty ? 'No documents yet. Upload a PDF or load the synthetic demo set to get started.'
            : `${a.documents_ready} of ${a.documents_total} documents are ready to search.`}
        </p>
      </div>
      {empty && <Empty title="Nothing to show yet"><Link className="underline" to="/documents">Go to Documents</Link> to upload files or load the demo set.</Empty>}
      <div className="grid gap-4 md:grid-cols-2">
        <section className="card bg-sun" aria-label="Documents">
          <h2 className="text-lg font-semibold">Documents</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Stat label="Uploaded" value={a.documents_total} /><Stat label="Processed" value={a.documents_ready} /><Stat label="Pages" value={a.pages_extracted} />
          </div>
          {a.processing_series.length > 0
            ? <Chart title="Processing time per document (ms)" data={[{ type: 'bar', x: a.processing_series.map((p) => p.filename), y: a.processing_series.map((p) => p.duration_ms), marker: { color: '#141414' } }]} />
            : <p className="mt-4 text-sm text-ink/70">Processing times appear after the first document finishes.</p>}
        </section>
        <section className="card bg-rose" aria-label="Questions">
          <h2 className="text-lg font-semibold">Questions</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Stat label="Asked" value={a.questions_asked} /><Stat label="Abstained" value={pct(a.abstention_rate)} /><Stat label="Valid cites" value={pct(a.citation_validity_rate)} />
          </div>
          {a.questions_per_day.length > 0
            ? <Chart title="Questions per day" data={[{ type: 'scatter', mode: 'lines+markers', x: a.questions_per_day.map((d) => d.day), y: a.questions_per_day.map((d) => d.count), line: { color: '#141414' } }]} />
            : <p className="mt-4 text-sm text-ink/70">No questions asked yet.</p>}
        </section>
        <section className="card bg-moss/80" aria-label="Processing health">
          <h2 className="text-lg font-semibold">Processing health</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Stat label="Success" value={pct(a.success_rate)} hint="ready ÷ (ready + failed)" /><Stat label="Failure" value={pct(a.failure_rate)} /><Stat label="Avg time" value={a.avg_processing_ms == null ? '—' : `${a.avg_processing_ms} ms`} />
          </div>
        </section>
        <section className="card bg-sky" aria-label="Index and latency">
          <h2 className="text-lg font-semibold">Index and speed</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Stat label="Chunks" value={a.chunks_indexed} />
            {['hybrid', 'chat'].map((k) => <Stat key={k} label={`${k} avg`} value={a.search_latency_avg_ms[k] == null ? '—' : `${a.search_latency_avg_ms[k]} ms`} />)}
          </div>
          {a.search_latency_series.length > 0 && <Chart title="Retrieval latency (ms)" data={[{ type: 'scatter', mode: 'lines', y: a.search_latency_series.map((s) => s.ms), line: { color: '#141414' } }]} />}
        </section>
      </div>
      <section className="card bg-sand" aria-label="Recent activity">
        <h2 className="mb-3 text-lg font-semibold">Recent document activity</h2>
        {a.recent_documents.length === 0 ? <p className="text-sm text-ink/70">No activity yet.</p> : (
          <ul className="space-y-2">{a.recent_documents.map((d) => (
            <li key={d.id}><Link to={`/documents/${d.id}`} className="flex items-center justify-between rounded-2xl bg-white/70 px-4 py-3 text-sm hover:bg-white">
              <span className="font-medium">{d.filename}{d.is_demo && <em className="ml-2 text-xs not-italic text-ink/60">(synthetic demo)</em>}</span>
              <span className="flex items-center gap-3"><span className="text-ink/60">{fmtDate(d.updated_at)}</span><StatusBadge status={d.status} /></span>
            </Link></li>))}
          </ul>)}
      </section>
    </div>
  )
}
