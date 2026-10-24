import { ErrorBox, Skeleton } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { api } from '../services/api'

export default function Settings() {
  const { data, error, loading, reload } = useAsync(api.system, [])
  if (error) return <ErrorBox message={error} onRetry={reload} />
  if (loading || !data) return <Skeleton h="h-64" />
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Settings and system health</h1>
      <p className={`rounded-2xl p-3 text-sm ${data.external_processing ? 'bg-sun/60' : 'bg-moss/30'}`}>{data.privacy_note}</p>
      <section className="space-y-2" aria-label="Components">{Object.entries(data.components).map(([k, c]) => (
        <div key={k} className="card bg-white/80 py-3"><div className="flex items-center justify-between"><span className="font-medium capitalize">{k.replace('_', ' ')}</span>
          <span className={`rounded-full px-2.5 py-1 text-xs ${c.ok ? 'bg-moss/40' : 'bg-rose'}`}>{c.ok ? 'available' : 'not available'}</span></div>
          <p className="text-sm text-ink/70">{c.detail}</p>{c.fix && <p className="mt-1 text-sm">{c.fix}</p>}</div>))}</section>
      <section className="card bg-sand"><h2 className="mb-2 font-semibold">Processing limits</h2>
        <p className="mb-2 text-xs text-ink/60">Set on the server through HEALTHDOC_* environment variables (see .env.example). They are read-only here so secrets and limits never pass through the browser.</p>
        <dl className="grid gap-1 text-sm sm:grid-cols-2">{Object.entries(data.limits).map(([k, v]) => <div key={k} className="flex justify-between"><dt className="text-ink/60">{k.replace(/_/g, ' ')}</dt><dd className="font-medium">{v}</dd></div>)}</dl></section>
    </div>
  )
}
