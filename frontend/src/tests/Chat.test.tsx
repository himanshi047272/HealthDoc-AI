import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Chat from '../pages/Chat'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: { listDocs: vi.fn(), chat: vi.fn() } }))
const docs = { items: [{ id: 'd1', filename: 'policy.pdf' }], total: 1, page: 1, page_size: 100 }
const view = () => render(<MemoryRouter><Chat /></MemoryRouter>)
const base = { conversation_id: 'c1', mode: 'extractive', evidence_type: 'direct_source_text', conflict: false, notes: [], latency_ms: 5, injection_filtered: false }

describe('Chat', () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.listDocs).mockResolvedValue(docs as any) })
  it('prompts to upload when nothing is ready', async () => {
    vi.mocked(api.listDocs).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    view(); expect(await screen.findByText('No processed documents yet')).toBeInTheDocument()
  })
  it('renders an answer with a citation that opens its excerpt', async () => {
    vi.mocked(api.chat).mockResolvedValue({ ...base, abstained: false, answer: 'From the selected documents:\n• The limit is $250,000. [1]',
      citations: [{ n: 1, document_id: 'd1', filename: 'policy.pdf', page_no: 1, chunk_id: 'x', excerpt: 'The limit is $250,000.', valid: true }] } as any)
    view()
    await userEvent.type(await screen.findByLabelText('Your question'), 'What is the limit?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText(/Direct text from your documents/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Open source 1' }))
    expect(screen.getByRole('link', { name: /Open page 1/ })).toBeInTheDocument()
    expect(api.chat).toHaveBeenCalledWith('What is the limit?', undefined, undefined)
  })
  it('shows the abstention message without citations', async () => {
    vi.mocked(api.chat).mockResolvedValue({ ...base, mode: 'abstain', abstained: true, answer: 'I couldn’t find enough supporting information in the selected documents to answer that confidently.', citations: [] } as any)
    view()
    await userEvent.type(await screen.findByLabelText('Your question'), 'Acupuncture?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText(/couldn’t find enough supporting information/)).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Sources' })).not.toBeInTheDocument()
  })
  it('reuses the conversation id for follow-ups and shows request errors', async () => {
    vi.mocked(api.chat).mockResolvedValueOnce({ ...base, abstained: true, mode: 'abstain', answer: 'x', citations: [] } as any).mockRejectedValueOnce(new Error('Server down'))
    view()
    const input = await screen.findByLabelText('Your question')
    await userEvent.type(input, 'first'); await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    await screen.findByText('x')
    await userEvent.type(input, 'second'); await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Server down')
    expect(vi.mocked(api.chat).mock.calls[1][1]).toBe('c1')
  })
})
