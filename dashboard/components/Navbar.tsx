'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

type Theme = 'light' | 'dark' | 'system'

const links = [
  { href: '/',          label: 'Dashboard'        },
  { href: '/conflicts', label: 'Permit Conflicts'  },
  { href: '/report',    label: 'Violation Report'  },
  { href: '/search',    label: 'Search'            },
  { href: '/mismatch',  label: 'DR vs Bayut'       },
  { href: '/agents',    label: 'Agents'            },
]

function applyTheme(theme: Theme) {
  const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', isDark)
}

export default function Navbar() {
  const path = usePathname()
  const [theme, setTheme] = useState<Theme>('system')
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const saved = (localStorage.getItem('theme') ?? 'system') as Theme
    setTheme(saved)
    applyTheme(saved)
  }, [])

  useEffect(() => {
    if (theme !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => document.documentElement.classList.toggle('dark', e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  function changeTheme(t: Theme) {
    setTheme(t)
    applyTheme(t)
    localStorage.setItem('theme', t)
  }

  const SunIcon = () => (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 5a7 7 0 100 14A7 7 0 0012 5z" />
    </svg>
  )
  const SystemIcon = () => (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  )
  const MoonIcon = () => (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  )

  return (
    <nav className="sticky top-0 z-50 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 shadow-sm print:hidden">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">

          {/* Brand */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center text-white text-xs font-bold">DR</span>
            <span className="font-semibold text-sm text-zinc-900 dark:text-white hidden sm:block">
              Listing Monitor
            </span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-0.5">
            {links.map(l => (
              <Link
                key={l.href}
                href={l.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  path === l.href
                    ? 'bg-violet-50 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
                    : 'text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            {/* 3-way theme toggle */}
            <div className="flex items-center rounded-lg bg-zinc-100 dark:bg-zinc-800 p-0.5 gap-0.5">
              {([
                { key: 'light'  as Theme, Icon: SunIcon,    title: 'Light'  },
                { key: 'system' as Theme, Icon: SystemIcon, title: 'System' },
                { key: 'dark'   as Theme, Icon: MoonIcon,   title: 'Dark'   },
              ]).map(({ key, Icon, title }) => (
                <button
                  key={key}
                  onClick={() => changeTheme(key)}
                  title={title}
                  aria-label={`${title} mode`}
                  className={`p-1.5 rounded-md transition-colors ${
                    theme === key
                      ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm'
                      : 'text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300'
                  }`}
                >
                  <Icon />
                </button>
              ))}
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMenuOpen(o => !o)}
              className="md:hidden w-8 h-8 flex items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              aria-label="Menu"
            >
              {menuOpen ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-2 space-y-1">
          {links.map(l => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setMenuOpen(false)}
              className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                path === l.href
                  ? 'bg-violet-50 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
                  : 'text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  )
}
