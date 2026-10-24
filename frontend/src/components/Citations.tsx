import { Link } from 'react-router-dom'
import type { Citation } from '../types'

export function AnswerText({ text, onCite }: { text: string; onCite: (n: number) => void }) {
  return (
    <div className="space-y-1.5 whitespace-pre-line">
      {text.split(/(\[\d+\])/g).map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/)
        return m
          ? <button key={i} className="mx-0.5 rounded-full bg-ink px-2 text-xs text-cream" aria-label={`Open source ${m[1]}`} onClick={() => onCite(Number(m[1]))}>{m[1]}</button>
          : <span key={i}>{part}</span>
      })}
    </div>
  )
}

export function CitationList({ citations, active, onSelect }: { citations: Citation[]; active?: number | null; onSelect: (n: number) => void }) {
  if (!citations.length) return null
  return (
    <ol className="mt-3 space-y-2" aria-label="Sources">
      {citations.map((c) => (
        <li key={c.n} id={`cite-${c.n}`} className={`rounded-2xl border p-3 text-sm ${active === c.n ? 'border-ink bg-white' : 'border-ink/10 bg-white/60'}`}>
          <button className="flex w-full items-center justify-between text-left font-medium" onClick={() => onSelect(c.n)} aria-expanded={active === c.n}>
            <span>[{c.n}] {c.filename} · page {c.page_no}{c.source === 'ocr' ? ' · OCR text' : ''}</span>
            <span className="text-xs text-ink/60">{c.valid ? 'verified in source' : 'not verified'}</span>
          </button>
          {active === c.n && (
            <div className="mt-2 space-y-2">
              <blockquote className="border-l-4 border-sun pl-3 italic">{c.excerpt}</blockquote>
              <Link className="underline" to={`/documents/${c.document_id}?page=${c.page_no}&hl=${encodeURIComponent(c.excerpt.slice(0, 120))}`}>Open page {c.page_no} in document</Link>
            </div>
          )}
        </li>
      ))}
    </ol>
  )
}
