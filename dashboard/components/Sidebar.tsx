'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const links = [
  { href: '/',           label: 'Dashboard',        icon: '⚡' },
  { href: '/conflicts',  label: 'Permit Conflicts',  icon: '🚨' },
  { href: '/report',     label: 'Violation Report',  icon: '📄' },
  { href: '/search',     label: 'Search',            icon: '🔍' },
  { href: '/mismatch',   label: 'DR vs Bayut',       icon: '⚖️' },
  { href: '/agents',     label: 'Agents',            icon: '👤' },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-56 shrink-0 bg-gray-900 text-white flex flex-col min-h-screen">
      <div className="px-5 py-6 border-b border-gray-700">
        <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">Dubai Residentials</p>
        <p className="font-semibold text-sm">Listing Monitor</p>
      </div>
      <nav className="flex flex-col gap-1 p-3 flex-1">
        {links.map(l => (
          <Link
            key={l.href}
            href={l.href}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
              path === l.href
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-800'
            }`}
          >
            <span>{l.icon}</span>
            {l.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
