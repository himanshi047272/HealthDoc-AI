import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

const GENERAL = [['/', 'Overview'], ['/documents', 'Documents'], ['/chat', 'Ask'], ['/insights', 'Insights'], ['/search', 'Search'], ['/evaluation', 'Evaluation']]
const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening' }
export { greeting }

export default function Layout() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const nav = useNavigate()
  const link = ({ isActive }: { isActive: boolean }) =>
    `block rounded-xl px-3 py-2 text-sm ${isActive ? 'bg-white/15 text-white' : 'text-white/70 hover:text-white'}`
  return (
    <div className="mx-auto flex min-h-screen max-w-[1500px] gap-4 p-3 md:p-4">
      <aside className={`${open ? 'fixed inset-3 z-30 flex' : 'hidden'} w-60 shrink-0 flex-col rounded-[28px] bg-ink p-5 text-white md:static md:flex`} aria-label="Main navigation">
        <div className="mb-8 flex items-center justify-between"><span className="text-2xl font-semibold tracking-tight">healthdoc</span>
          <button className="md:hidden" onClick={() => setOpen(false)} aria-label="Close menu">✕</button></div>
        <p className="mb-2 text-xs text-white/50">General</p>
        <nav className="space-y-1">{GENERAL.map(([to, label]) => <NavLink key={to} to={to} end={to === '/'} className={link} onClick={() => setOpen(false)}>{label}</NavLink>)}</nav>
        <p className="mb-2 mt-8 text-xs text-white/50">Tools</p>
        <NavLink to="/settings" className={link} onClick={() => setOpen(false)}>Settings &amp; health</NavLink>
        <p className="mt-auto text-xs leading-relaxed text-white/50">Educational search tool. Not medical, legal or insurance advice. Documents stay on this server unless a model provider is configured.</p>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="mb-5 flex items-center gap-3">
          <button className="btn-ghost md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">Menu</button>
          <form className="flex flex-1 items-center gap-2 rounded-full border border-ink/10 bg-sand/70 p-1.5 pl-4" role="search"
            onSubmit={(e) => { e.preventDefault(); if (q.trim()) nav(`/search?q=${encodeURIComponent(q.trim())}`) }}>
            <label htmlFor="global-search" className="sr-only">Search documents</label>
            <input id="global-search" className="min-w-0 flex-1 bg-transparent text-sm outline-none" placeholder="Search inside your documents" value={q} onChange={(e) => setQ(e.target.value)} />
            <button className="btn">Search</button>
          </form>
        </header>
        <main><Outlet /></main>
      </div>
    </div>
  )
}
