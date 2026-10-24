import { useState } from 'react'
import { ErrorBox, Skeleton, pct } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'

const DEFS: [string, string, string][] = [
  ['retrieval_recall_at_k', 'Recall@5', 'Share of expected (document, page) sources found in the top 5 results.'],
  ['mrr', 'Mean reciprocal rank', 'Average of 1 / rank of the first correct page. 1.0 means it was always first.'],
  ['answer_decision_precision', 'Answer precision', 'Of the questions the system answered, how many were answerable.'],
  ['answer_decision_recall', 'Answer recall', 'Of the answerable questions, how many it answered instead of abstaining.'],
  ['correct_abstention_rate', 'Correct abstention', 'Of the unanswerable questions, how many it refused.'],
  ['answer_support_rate', 'Answer support', 'Answerable questions where every expected fact appears in the cited text.'],
  ['citation_validity_rate', 'Citation validity', 'Citations whose page and excerpt exist in the stored document text.'],
  ['citation_precision', 'Citation precision', 'Citations that point at an expected page.'],
  ['processing_success_rate', 'Processing success', 'Fixture documents that finished processing.'],
]

export default function Evaluation() {
  const latest = useAsync(api.latestEval, [])
  const [run, setRun] = useState<{ metrics: Record<string, any>; results: any[] } | null>(null)
  const [busy, setBusy] = useState(false), [err, setErr] = useState<string | null>(null)
  const cur = run ?? (latest.data?.metrics ? latest.data : null)
  const go = async () => { setBusy(true); setErr(null); try { setRun(await api.runEval()) } catch (e) { setErr(e instanceof Error ? e.message : 'Evaluation failed.') } setBusy(false) }
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Evaluation</h1>
      <p className="max-w-2xl text-sm text-ink/70">Runs a small, version-controlled <strong>synthetic</strong> question set against the three synthetic demo documents, in an isolated temporary store. It checks that retrieval, citations and abstention behave as designed. It says nothing about clinical accuracy or performance on your own documents.</p>
      <button className="btn" onClick={go} disabled={busy}>{busy ? 'Running…' : 'Run evaluation'}</button>
      {err && <ErrorBox message={err} />}
      {latest.loading ? <Skeleton h="h-40" /> : !cur ? <p className="text-sm">No evaluation has been run yet.</p> : (<>
        <p className="text-sm text-ink/70">Embedder: {cur.metrics?.embedder} · {cur.metrics?.n_cases} cases ({cur.metrics?.n_answerable} answerable, {cur.metrics?.n_unanswerable} unanswerable)</p>
        <div className="grid gap-3 md:grid-cols-3">{DEFS.map(([k, label, def]) => (
          <div key={k} className="card bg-white/80"><div className="text-xs uppercase text-ink/60">{label}</div><div className="text-3xl font-semibold">{pct(cur.metrics?.[k])}</div><p className="mt-1 text-xs text-ink/70">{def}</p></div>))}</div>
        <p className="text-sm">Leave-one-out abstention (threshold picked without the scored case): precision {pct(cur.metrics?.leave_one_out?.answer_decision_precision)}, recall {pct(cur.metrics?.leave_one_out?.answer_decision_recall)}.</p>
        <div className="overflow-x-auto rounded-card bg-white/70"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-ink/60"><tr><th className="p-3">Case</th><th>Question</th><th>Tag</th><th>Expected</th><th>Result</th></tr></thead>
          <tbody>{cur.results.map((r: any) => { const answered = !String(r.answer).startsWith('I couldn'); const ok = answered === r.answerable && (!r.answerable || r.supported)
            return <tr key={r.id} className="border-t border-ink/10"><td className="p-3">{r.id}</td><td>{r.question}</td><td>{r.tag}</td><td>{r.answerable ? 'answer' : 'abstain'}</td><td className={ok ? '' : 'font-semibold text-red-800'}>{ok ? 'pass' : 'miss'}</td></tr> })}</tbody></table></div>
      </>)}
    </div>
  )
}
