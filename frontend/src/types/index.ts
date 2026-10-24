export interface Doc {
  id: string; filename: string; kind: string; size_bytes: number; status: 'uploaded' | 'processing' | 'ready' | 'failed'
  error: string | null; page_count: number; chunk_count: number; ocr_pages: number; extractor: string | null
  doc_type: string | null; doc_type_score: number | null; is_demo: number; duration_ms: number | null
  created_at: number; updated_at: number; job?: { stage: string; status: string } | null
}
export interface Page { page_no: number; text: string; source: 'native' | 'ocr' | 'empty'; ocr_conf: number | null }
export interface Citation {
  n: number; document_id: string; filename: string; page_no: number; chunk_id: string; excerpt: string
  valid: boolean | number; source?: string; chunk_text?: string
}
export interface ChatResponse {
  conversation_id: string; answer: string; abstained: boolean; mode: 'extractive' | 'llm' | 'abstain'
  evidence_type: string; citations: Citation[]; conflict: boolean; notes: string[]; latency_ms: number
  injection_filtered: boolean
}
export interface SearchResult {
  document_id: string; filename: string; page_no: number; chunk_id: string; passage: string; source: string
  score: number; bm25: number; dense: number
}
export interface Analytics {
  documents_total: number; documents_ready: number; documents_failed: number; pages_extracted: number
  chunks_indexed: number; questions_asked: number; success_rate: number | null; failure_rate: number | null
  abstention_rate: number | null; citation_validity_rate: number | null; avg_processing_ms: number | null
  processing_series: { filename: string; duration_ms: number; pages: number }[]
  search_latency_avg_ms: Record<string, number>; search_latency_series: { kind: string; ms: number }[]
  questions_per_day: { day: string; count: number }[]
  recent_documents: { id: string; filename: string; status: string; page_count: number; updated_at: number; is_demo: boolean }[]
}
export interface Field { field: string; value: string; page_no: number; evidence: string; method: string }
export interface Insights {
  filename: string; classification: { label: string; score: number; kind: string; method: string }
  fields: Field[]; entities: { label: string; text: string; method: string; page_no: number }[]
  definitions: { term: string; definition: string; evidence: string; page_no: number }[]; ocr_pages: number[]
}
export interface SystemStatus {
  components: Record<string, { ok: boolean; detail: string; fix: string | null }>
  external_processing: boolean; privacy_note: string; limits: Record<string, number>
}
export type EvalMetrics = Record<string, any>
