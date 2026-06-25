'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Sidebar from '@/components/Sidebar'

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

const COMMUNITIES = ['All', 'The Gardens', 'Gardens Apartments', 'Bluewaters', 'Citywalk', 'Meydan Residence 1', 'Garden View Apartments', 'Garden View Villas', 'International City', 'Discovery Gardens', 'Manazel Al Khor']

export default function ConflictsPage() {
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [loading, setLoading]     = useState(true)
  const [community, setCommunity] = useState('All')
  const [search, setSearch]       = useState('')

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('permit_conflicts')
        .select('*')
        .order('community', { ascending: true })
        .limit(500)
      setConflicts((data ?? []) as Conflict[])
      setLoading(false)
    }
    load()
  }, [])

  const filtered = conflicts.filter(c => {
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

  // Group by permit so we can show multiple conflicts per permit together
  const byPermit = filtered.reduce<Record<string, Conflict[]>>((acc, c) => {
    acc[c.permit_number] = acc[c.permit_number] ?? []
    acc[c.permit_number].push(c)
    return acc
  }, {})

  const permitGroups = Object.entries(byPermit)

  const agencyCounts = conflicts.reduce<Record<string, number>>((acc, c) => {
    const k = c.agency_name ?? 'Unknown'
    acc[k] = (acc[k] ?? 0) + 1
    return acc
  }, {})
  const topAgencies = Object.entries(agencyCounts).sort((a, b) => b[1] - a[1]).slice(0, 5)

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-6xl mx-auto">

          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">Confirmed Permit Conflicts</h1>
              <span className="bg-red-100 text-red-700 text-sm font-semibold px-2.5 py-0.5 rounded-full">
                {conflicts.length} conflicts
              </span>
            </div>
            <p className="text-sm text-gray-500">
              Same DLD permit number found on both DR&apos;s official listing and an unauthorized agent&apos;s listing — confirmed same physical unit.
            </p>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl border border-red-200 p-5 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Total Conflicts</p>
              <p className="text-3xl font-bold text-red-600">{conflicts.length}</p>
              <p className="text-xs text-gray-400 mt-1">unique stolen listings</p>
            </div>
            <div className="bg-white rounded-xl border border-orange-200 p-5 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Unique Permits</p>
              <p className="text-3xl font-bold text-orange-600">{Object.keys(byPermit).length}</p>
              <p className="text-xs text-gray-400 mt-1">units compromised</p>
            </div>
            <div className="bg-white rounded-xl border border-purple-200 p-5 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Offending Agencies</p>
              <p className="text-3xl font-bold text-purple-600">
                {new Set(conflicts.map(c => c.agency_name)).size}
              </p>
              <p className="text-xs text-gray-400 mt-1">distinct agencies</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-xs text-gray-500 mb-2">Top Offender</p>
              {topAgencies[0] && (
                <>
                  <p className="text-sm font-bold text-gray-800 leading-tight">{topAgencies[0][0]}</p>
                  <p className="text-xs text-gray-400 mt-1">{topAgencies[0][1]} listings</p>
                </>
              )}
            </div>
          </div>

          {/* Top agencies bar */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Top Offending Agencies</p>
            <div className="space-y-2">
              {topAgencies.map(([agency, count]) => (
                <div key={agency} className="flex items-center gap-3">
                  <span className="text-sm text-gray-700 w-64 truncate">{agency}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-red-400 h-2 rounded-full"
                      style={{ width: `${(count / (topAgencies[0]?.[1] ?? 1)) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-gray-600 w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-5">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Community</label>
              <select
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm"
                value={community} onChange={e => setCommunity(e.target.value)}
              >
                {COMMUNITIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <input
              type="text"
              placeholder="Search permit, agent, agency, location..."
              value={search} onChange={e => setSearch(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm w-72"
            />
            <span className="text-sm text-gray-400 ml-auto">
              {permitGroups.length} permit{permitGroups.length !== 1 ? 's' : ''} · {filtered.length} conflict{filtered.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Conflict cards */}
          {loading ? (
            <div className="text-center py-20 text-gray-400">Loading...</div>
          ) : permitGroups.length === 0 ? (
            <div className="text-center py-20 text-gray-400">No conflicts found</div>
          ) : (
            <div className="space-y-4">
              {permitGroups.map(([permit, rows]) => {
                const first = rows[0]
                return (
                  <div key={permit} className="bg-white rounded-xl border border-red-200 shadow-sm overflow-hidden">
                    {/* Red top bar */}
                    <div className="h-1 w-full bg-red-500" />

                    {/* Permit header */}
                    <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-red-50">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded">
                          CONFIRMED CONFLICT
                        </span>
                        <span className="text-xs text-gray-500">Permit:</span>
                        <span className="text-xs font-mono font-semibold text-gray-800">{permit}</span>
                        {first.community && (
                          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">{first.community}</span>
                        )}
                      </div>
                      {rows.length > 1 && (
                        <span className="text-xs text-red-600 font-semibold">{rows.length} agents on same unit</span>
                      )}
                    </div>

                    <div className="p-5">
                      {/* DR official listing */}
                      <div className="flex items-start gap-4 mb-4 pb-4 border-b border-gray-100">
                        <div className="w-24 shrink-0">
                          <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-1 rounded border border-green-200 block text-center">
                            DR Official
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{first.dr_location}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {first.dr_beds}bd · {first.dr_baths}ba · Ref: {first.dr_reference}
                          </p>
                        </div>
                        <a
                          href={first.dr_bayut_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="shrink-0 text-xs bg-green-50 hover:bg-green-100 text-green-700 px-3 py-1.5 rounded-lg whitespace-nowrap border border-green-200"
                        >
                          View on Bayut ↗
                        </a>
                      </div>

                      {/* Unauthorized listings */}
                      <div className="space-y-3">
                        {rows.map(c => (
                          <div key={c.id} className="flex items-start gap-4">
                            <div className="w-24 shrink-0">
                              <span className="text-xs font-semibold text-red-700 bg-red-50 px-2 py-1 rounded border border-red-200 block text-center">
                                Unauthorized
                              </span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">{c.unauthorized_location}</p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {c.unauthorized_beds}bd · {c.unauthorized_baths}ba · Ref: {c.unauthorized_reference}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs font-medium text-gray-700">{c.agent_name}</span>
                                <span className="text-xs text-gray-400">·</span>
                                <span className="text-xs text-orange-600 font-medium">{c.agency_name}</span>
                                {c.agent_mobile && (
                                  <>
                                    <span className="text-xs text-gray-400">·</span>
                                    <a href={`tel:${c.agent_mobile}`} className="text-xs text-blue-500 hover:underline">
                                      {c.agent_mobile}
                                    </a>
                                  </>
                                )}
                              </div>
                            </div>
                            <a
                              href={c.unauthorized_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0 text-xs bg-red-50 hover:bg-red-100 text-red-700 px-3 py-1.5 rounded-lg whitespace-nowrap border border-red-200"
                            >
                              View on Bayut ↗
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
