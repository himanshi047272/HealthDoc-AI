import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AnswerText, CitationList } from '../components/Citations'

const c = { n: 1, document_id: 'd1', filename: 'policy.pdf', page_no: 2, chunk_id: 'd1:2:0', excerpt: 'The limit is $250,000.', valid: true }

describe('citations', () => {
  it('turns [n] markers into buttons that report the number', async () => {
    const onCite = vi.fn()
    render(<AnswerText text={'The limit is $250,000. [1]'} onCite={onCite} />)
    await userEvent.click(screen.getByRole('button', { name: 'Open source 1' }))
    expect(onCite).toHaveBeenCalledWith(1)
  })
  it('shows file, page and excerpt only when expanded, with a link to the page', () => {
    render(<MemoryRouter><CitationList citations={[c]} active={1} onSelect={() => {}} /></MemoryRouter>)
    expect(screen.getByText(/policy.pdf · page 2/)).toBeInTheDocument()
    expect(screen.getByText('The limit is $250,000.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open page 2/ })).toHaveAttribute('href', expect.stringContaining('/documents/d1?page=2'))
  })
  it('renders nothing when there are no citations', () => {
    const { container } = render(<MemoryRouter><CitationList citations={[]} onSelect={() => {}} /></MemoryRouter>)
    expect(container).toBeEmptyDOMElement()
  })
})
