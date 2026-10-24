import type { Analytics, ChatResponse, Doc, Insights, Page, SearchResult, SystemStatus } from '../types'

const BASE = (import.meta as any).env?.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response
  try { r = await fetch(BASE + path, init) } catch { throw new ApiError('Cannot reach the server. Is the backend running?', 0) }
  if (!r.ok) {
    let msg = `Request failed (${r.status})`
    try { const b = await r.json(); msg = b.error?.message ?? (b.detail ? 'The request was not valid.' : msg) } catch { /* keep default */ }
    throw new ApiError(msg, r.status)
  }
  return r.status === 204 ? (undefined as T) : r.json()
}
const json = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  listDocs: (p: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => [k, String(v)]))
    return req<{ items: Doc[]; total: number; page: number; page_size: number }>(`/api/documents?${qs}`)
  },
  getDoc: (id: string) => req<Doc>(`/api/documents/${id}`),
  pages: (id: string) => req<{ pages: Page[] }>(`/api/documents/${id}/text`),
  upload: (file: File) => { const f = new FormData(); f.append('file', file); return req<{ document: Doc; duplicate: boolean }>('/api/documents', { method: 'POST', body: f }) },
  remove: (id: string) => req<void>(`/api/documents/${id}`, { method: 'DELETE' }),
  reprocess: (id: string) => req<Doc>(`/api/documents/${id}/reprocess`, { method: 'POST' }),
  demo: () => req<{ documents: Doc[] }>('/api/demo/load', { method: 'POST' }),
  insights: (id: string) => req<Insights>(`/api/documents/${id}/insights`),
  chat: (question: string, conversation_id?: string, document_ids?: string[]) => req<ChatResponse>('/api/chat', json({ question, conversation_id, document_ids })),
  search: (b: Record<string, unknown>) => req<{ latency_ms: number; total: number; results: SearchResult[] }>('/api/search', json(b)),
  analytics: () => req<Analytics>('/api/analytics'),
  runEval: () => req<{ metrics: Record<string, any>; results: any[] }>('/api/evaluation/run', { method: 'POST' }),
  latestEval: () => req<{ metrics: Record<string, any> | null; results: any[] }>('/api/evaluation/latest'),
  system: () => req<SystemStatus>('/api/system/status'),
}
