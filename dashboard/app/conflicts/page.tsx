'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

type Conflict = {
  id: number
  permit_number: string
  dr_bayut_url: string
  dr_reference: string
  dr_location: string
  dr_beds: number
  dr_baths: number
  unauthorized_url: string
  unauthorized_reference: string
  unauthorized_location: string
  unauthorized_beds: number
  unauthorized_baths: number
  agent_name: string
  agency_name: string
  agent_mobile: string | null
  community: string | null
  created_at: string
}

type SortKey = 'community' | 'agency_name' | 'permit_number' | 'dr_location'
type SortDir = 'asc' | 'desc'

const COMMUNITIES = [
  'All', 'The Gardens', 'Gardens Apartments', 'Garden View Apartments',
  'Garden View Villas', 'Bluewaters', 'Citywalk', 'Meydan Residence 1',
  'International City', 'Discovery Gardens', 'Manazel Al Khor',
]

export default function ConflictsPage() {
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [loading, setLoading]     = useState(true)
  const [community, setCommunity] = useState('All')
  const [search, setSearch]       = useState('')
  const [sortKey, setSortKey]     = useState<SortKey>('community')
  const [sortDir, setSortDir]     = useState<SortDir>('asc')

  useEffect(() => {
    async function load() {
      const { data } = await supabase.from('permit_conflicts').select('*').limit(500)
      setConflicts((data ?? []) as Conflict[])
      setLoading(false)
    }
    load()
  }, [])

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  const filtered = conflicts
    .filter(c => {
      if (community !== 'All' && c.community !== community) return false
      if (search) {
        const s = search.toLowerCase()
        return (
          c.permit_number?.includes(s) ||
          c.agent_name?.toLowerCase().includes(s) ||
          c.agency_name?.toLowerCase().includes(s) ||
          c.dr_location?.toLowerCase().includes(s) ||
          c.unauthorized_reference?.toLowerCase().includes(s)
        )
      }
      return true
    })
    .sort((a, b) => {
      const av = (a[sortKey] ?? '') as string
      const bv = (b[sortKey] ?? '') as string
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    })

  // Summary stats
  const agencyCounts = conflicts.reduce<Record<string, number>>((acc, c) => {
    const k = c.agency_name ?? 'Unknown'
    acc[k] = (acc[k] ?? 0) + 1
    return acc
  }, {})
  const topAgencies = Object.entries(agencyCounts).sort((a, b) => b[1] - a[1]).slice(0, 5)

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="text-zinc-300 dark:text-zinc-600 ml-1">↕</span>
    return <span className="text-violet-500 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-[#0a0a0a]">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-6">

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div>
            <h1 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              Confirmed Permit Conflicts
              <span className="text-sm font-semibold bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-2 py-0.5 rounded-full">
                {conflicts.length}
              </span>
            </h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
              Same DLD permit found on DR&apos;s official listing and an unauthorized agent — confirmed same physical unit.
            </p>
          </div>
        </div>

        {/* Stats + top agencies */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white dark:bg-[#111] rounded-xl border border-zinc-200 dark:border-[#2a2a2a] p-4">
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Total Conflicts</p>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">{conflicts.length}</p>
          </div>
          <div className="bg-white dark:bg-[#111] rounded-xl border border-zinc-200 dark:border-[#2a2a2a] p-4">
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Unique Permits</p>
            <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {new Set(conflicts.map(c => c.permit_number)).size}
            </p>
          </div>
          <div className="bg-white dark:bg-[#111] rounded-xl border border-zinc-200 dark:border-[#2a2a2a] p-4">
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Agencies</p>
            <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {new Set(conflicts.map(c => c.agency_name)).size}
            </p>
          </div>
          <div className="bg-white dark:bg-[#111] rounded-xl border border-zinc-200 dark:border-[#2a2a2a] p-4">
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-2">Top Offender</p>
            {topAgencies[0] && (
              <>
                <p className="text-sm font-bold text-zinc-800 dark:text-white leading-tight truncate">{topAgencies[0][0]}</p>
                <p className="text-xs text-zinc-400 dark:text-zinc-500">{topAgencies[0][1]} listings</p>
              </>
            )}
          </div>
        </div>

        {/* Agency bar */}
        <div className="bg-white dark:bg-[#111] rounded-xl border border-zinc-200 dark:border-[#2a2a2a] p-4 mb-6">
          <p className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest mb-3">Top Offending Agencies</p>
          <div className="space-y-2">
            {topAgencies.map(([agency, count]) => (
              <div key={agency} className="flex items-center gap-3">
                <span className="text-sm text-zinc-700 dark:text-zinc-300 w-56 truncate shrink-0">{agency}</span>
                <div className="flex-1 bg-zinc-100 dark:bg-[#1a1a1a] rounded-full h-2">
                  <div className="bg-red-400 h-2 rounded-full transition-all"
                    style={{ width: `${(count / (topAgencies[0]?.[1] ?? 1)) * 100}%` }} />
                </div>
                <span className="text-sm font-semibold text-zinc-600 dark:text-zinc-300 w-6 text-right shrink-0">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <select
            className="border border-zinc-200 dark:border-[#2a2a2a] rounded-lg px-2.5 py-1.5 text-sm bg-white dark:bg-[#111] text-zinc-700 dark:text-zinc-200 shadow-sm"
            value={community} onChange={e => setCommunity(e.target.value)}>
            {COMMUNITIES.map(c => <option key={c}>{c}</option>)}
          </select>
          <input
            type="text"
            placeholder="Search permit, agent, agency, location…"
            value={search} onChange={e => setSearch(e.target.value)}
            className="border border-zinc-200 dark:border-[#2a2a2a] rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-[#111] text-zinc-700 dark:text-zinc-200 shadow-sm w-full sm:w-72"
          />
          <span className="text-sm text-zinc-400 dark:text-zinc-500 ml-auto">{filtered.length} results</span>
        </div>

        {/* Table */}
        {loading ? (
          <div className="text-center py-20 text-zinc-400 dark:text-zinc-600">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-zinc-400 dark:text-zinc-600">No conflicts found</div>
        ) : (
          <div className="bg-white dark:bg-[#111] rounded-xl border border-zinc-200 dark:border-[#2a2a2a] shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-[#2a2a2a] bg-zinc-50 dark:bg-[#1a1a1a]">
                    {[
                      { key: 'community' as SortKey,     label: 'Community'    },
                      { key: 'permit_number' as SortKey, label: 'Permit'       },
                      { key: 'dr_location' as SortKey,   label: 'DR Unit'      },
                      { key: 'agency_name' as SortKey,   label: 'Agency'       },
                    ].map(col => (
                      <th key={col.key}
                        onClick={() => toggleSort(col.key)}
                        className="text-left text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide px-4 py-3 cursor-pointer hover:text-zinc-700 dark:hover:text-zinc-200 select-none whitespace-nowrap">
                        {col.label}<SortIcon col={col.key} />
                      </th>
                    ))}
                    <th className="text-left text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide px-4 py-3 whitespace-nowrap">Agent</th>
                    <th className="text-left text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide px-4 py-3 whitespace-nowrap">Links</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-[#1a1a1a]">
                  {filtered.map(c => (
                    <tr key={c.id} className="hover:bg-zinc-50 dark:hover:bg-[#1a1a1a]/50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs font-medium text-indigo-400 dark:text-indigo-400">
                          {c.community ?? '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-mono text-xs text-zinc-600 dark:text-zinc-300">{c.permit_number}</span>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-zinc-800 dark:text-zinc-200 font-medium text-xs max-w-xs truncate">{c.dr_location}</p>
                        <p className="text-zinc-400 dark:text-zinc-500 text-xs mt-0.5">{c.dr_beds}bd · {c.dr_baths}ba · Ref: {c.dr_reference}</p>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-semibold text-red-600 dark:text-red-400 text-xs whitespace-nowrap">{c.agency_name}</p>
                        <p className="text-xs font-mono text-zinc-400 dark:text-zinc-500 mt-0.5">{c.unauthorized_reference}</p>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-zinc-700 dark:text-zinc-300 text-xs whitespace-nowrap">{c.agent_name}</p>
                        {c.agent_mobile && (
                          <a href={`tel:${c.agent_mobile}`} className="text-xs text-violet-500 hover:underline">{c.agent_mobile}</a>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex gap-2">
                          <a href={c.dr_bayut_url} target="_blank" rel="noopener noreferrer"
                            className="text-xs bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/40 px-2.5 py-1 rounded-lg border border-green-200 dark:border-green-800 whitespace-nowrap">
                            DR ↗
                          </a>
                          <a href={c.unauthorized_url} target="_blank" rel="noopener noreferrer"
                            className="text-xs bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 px-2.5 py-1 rounded-lg border border-red-200 dark:border-red-800 whitespace-nowrap">
                            Stolen ↗
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
