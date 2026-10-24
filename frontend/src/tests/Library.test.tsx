import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Library from '../pages/Library'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: { listDocs: vi.fn(), upload: vi.fn(), remove: vi.fn(), reprocess: vi.fn(), demo: vi.fn() } }))
const doc = (o = {}) => ({ id: 'a', filename: 'one.pdf', kind: 'pdf', size_bytes: 2048, status: 'ready', error: null, page_count: 3, chunk_count: 5, ocr_pages: 0, created_at: 1, updated_at: 1, is_demo: 0, ...o })
const view = () => render(<MemoryRouter><Library /></MemoryRouter>)

describe('Library', () => {
  beforeEach(() => vi.clearAllMocks())
  it('shows an empty state', async () => {
    vi.mocked(api.listDocs).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    view(); expect(await screen.findByText('No documents yet')).toBeInTheDocument()
  })
  it('lists documents and shows a failure reason with a reprocess action', async () => {
    vi.mocked(api.listDocs).mockResolvedValue({ items: [doc(), doc({ id: 'b', filename: 'bad.pdf', status: 'failed', error: 'The PDF is password-protected.' })], total: 2, page: 1, page_size: 10 } as any)
    view()
    expect(await screen.findByText('one.pdf')).toBeInTheDocument()
    expect(screen.getByText('The PDF is password-protected.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reprocess' })).toBeInTheDocument()
  })
  it('sends the filename filter to the API', async () => {
    vi.mocked(api.listDocs).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    view(); await screen.findByText('No documents yet')
    await userEvent.type(screen.getByLabelText('Filter by filename'), 'claims')
    await waitFor(() => expect(api.listDocs).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'claims' })))
  })
  it('shows an actionable error when the server is unreachable', async () => {
    vi.mocked(api.listDocs).mockRejectedValue(new Error('Cannot reach the server. Is the backend running?'))
    view(); expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
  it('uploads a chosen file through the API', async () => {
    vi.mocked(api.listDocs).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    vi.mocked(api.upload).mockResolvedValue({ document: doc(), duplicate: false } as any)
    view(); await screen.findByText('No documents yet')
    await userEvent.upload(screen.getByLabelText('Upload documents'), new File(['%PDF-1.4'], 'x.pdf', { type: 'application/pdf' }))
    await waitFor(() => expect(api.upload).toHaveBeenCalled())
    expect(await screen.findByText(/x.pdf uploaded/)).toBeInTheDocument()
  })
})
