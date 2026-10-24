import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import UploadZone, { checkFile } from '../components/UploadZone'

const file = (name: string, size = 10) => new File([new Uint8Array(size)], name)

describe('checkFile', () => {
  it('accepts supported types', () => expect(checkFile(file('a.pdf'), 25)).toBeNull())
  it('rejects unsupported types', () => expect(checkFile(file('a.exe'), 25)).toMatch(/unsupported/))
  it('rejects oversize and empty files', () => {
    expect(checkFile(file('a.pdf', 2 * 1024 * 1024), 1)).toMatch(/larger/)
    expect(checkFile(file('a.pdf', 0), 25)).toMatch(/empty/)
  })
})

describe('UploadZone', () => {
  it('passes valid files on and shows an alert for invalid ones', async () => {
    const onFiles = vi.fn()
    render(<UploadZone onFiles={onFiles} />)
    await userEvent.upload(screen.getByLabelText('Upload documents'), [file('ok.pdf'), file('bad.exe')], { applyAccept: false })
    expect(onFiles).toHaveBeenCalledWith([expect.objectContaining({ name: 'ok.pdf' })])
    expect(screen.getByRole('alert')).toHaveTextContent('bad.exe')
  })
  it('disables the button while busy', () => {
    render(<UploadZone onFiles={() => {}} busy />)
    expect(screen.getByRole('button', { name: /uploading/i })).toBeDisabled()
  })
})
