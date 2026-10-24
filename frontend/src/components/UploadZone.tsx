import { useRef, useState } from 'react'

const OK = ['.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff']

export function checkFile(f: File, maxMb: number): string | null {
  const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
  if (!OK.includes(ext)) return `${f.name}: unsupported type. Use PDF, PNG, JPG or TIFF.`
  if (f.size > maxMb * 1024 * 1024) return `${f.name}: larger than ${maxMb} MB.`
  if (f.size === 0) return `${f.name}: the file is empty.`
  return null
}

export default function UploadZone({ onFiles, busy, maxMb = 25 }: { onFiles: (files: File[]) => void; busy?: boolean; maxMb?: number }) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  const take = (list: FileList | null) => {
    if (!list) return
    const good: File[] = [], bad: string[] = []
    Array.from(list).forEach((f) => { const e = checkFile(f, maxMb); e ? bad.push(e) : good.push(f) })
    setErrors(bad)
    if (good.length) onFiles(good)
  }
  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true) }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files) }}
        className={`rounded-card border-2 border-dashed p-6 text-center transition ${over ? 'border-ink bg-white' : 'border-ink/25 bg-white/50'}`}
      >
        <p className="font-medium">Drop PDFs or scanned images here</p>
        <p className="mb-3 text-sm text-ink/60">PDF, PNG, JPG, TIFF · up to {maxMb} MB each</p>
        <button type="button" className="btn" disabled={busy} onClick={() => input.current?.click()}>{busy ? 'Uploading…' : 'Choose files'}</button>
        <input ref={input} type="file" multiple hidden aria-label="Upload documents" accept={OK.join(',')} onChange={(e) => { take(e.target.files); e.target.value = '' }} />
      </div>
      {errors.length > 0 && <ul role="alert" className="mt-2 space-y-1 text-sm text-red-800">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
    </div>
  )
}
