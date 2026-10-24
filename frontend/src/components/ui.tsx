import type { ReactNode } from 'react'
import type { Doc } from '../types'

const STYLE: Record<string, string> = {
  ready: 'bg-moss/40 text-ink', processing: 'bg-sky text-ink', uploaded: 'bg-sky text-ink', failed: 'bg-rose text-ink',
}
export function StatusBadge({ status }: { status: Doc['status'] | string }) {
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STYLE[status] ?? 'bg-sand'}`}>{status}</span>
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-ink/20 bg-white/50 p-8 text-center" role="status">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-ink/70">{children}</div>}
    </div>
  )
}
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-card bg-rose/60 p-4 text-sm">
      <span>{message}</span>
      {onRetry && <button className="btn-ghost" onClick={onRetry}>Try again</button>}
    </div>
  )
}
export const Skeleton = ({ h = 'h-28' }: { h?: string }) => <div className={`skeleton ${h}`} aria-hidden />
export const fmtBytes = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)
export const fmtDate = (t: number) => new Date(t * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
export const pct = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)
export const Stat = ({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) => (
  <div><div className="text-xs uppercase tracking-wide text-ink/60">{label}</div><div className="text-3xl font-semibold">{value}</div>{hint && <div className="text-xs text-ink/60">{hint}</div>}</div>
)
