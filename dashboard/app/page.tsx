'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import ScoreBadge from '@/components/ScoreBadge'

type Match = {
  id: number
  dr_url: string
  bayut_id: number
  score: number
  score_beds: number
  score_baths: number
  score_size: number
  score_price: number
  building_match: boolean | null
  is_authorized: boolean
  dr_building: string | null
  bayut_building: string | null
  created_at: string
  dubai_residentials_full: {
    location: string
    beds: number
    baths: number
    size_sqft: number
    price_aed: number
    community: string
    photos: string[]
    unit_id: string
    property_id: string
  }
  bayut_community_rentals: {
    url: string
    title: string
    beds: number
    baths: number
    area_sqft: number
    price: { amount: number; currency: string }
    agent: { name: string; mobile: string }
    agency: { name: string }
    permit_number: string
    cover_photo: string
  }
}

type Stats = { total_dr: number; total_bayut: number; high_risk: number; conflicts: number }
type AuthFilter = 'hide' | 'show'

const COMMUNITIES = [
  'All', 'Al Khail Gate', 'Bluewaters', 'Citywalk', 'Discovery Gardens',
  'Dubai Wharf', 'Garden View Apartments', 'Garden View Villas', 'Gardens Apartments',
  'International City', 'Manazel Al Khor', 'Meydan Residence 1', 'The Gardens',
]

export default function Dashboard() {
  const [matches, setMatches]       = useState<Match[]>([])
  const [stats, setStats]           = useState<Stats>({ total_dr: 0, total_bayut: 0, high_risk: 0, conflicts: 0 })
  const [threshold, setThreshold]   = useState(95)
  const [community, setCommunity]   = useState('All')
  const [authFilter, setAuthFilter] = useState<AuthFilter>('hide')
  const [loading, setLoading]       = useState(true)
  const [newAlert, setNewAlert]     = useState<Match | null>(null)

  const fetchMatches = useCallback(async () => {
    setLoading(true)
    let q = supabase
      .from('listing_matches')
      .select(`
        id, dr_url, bayut_id, score, score_beds, score_baths, score_size, score_price,
        building_match, is_authorized, dr_building, bayut_building, created_at,
        dubai_residentials_full!listing_matches_dr_url_fkey(location, beds, baths, size_sqft, price_aed, community, photos, unit_id, property_id),
        bayut_community_rentals!listing_matches_bayut_id_fkey(url, title, beds, baths, area_sqft, price, agent, agency, permit_number, cover_photo)
      `)
      .gte('score', threshold)
      .order('score', { ascending: false })
      .limit(2000)

    if (authFilter === 'hide') q = q.eq('is_authorized', false)

    const { data } = await q
    if (data) setMatches(data as unknown as Match[])
    setLoading(false)
  }, [threshold, authFilter])

  const fetchStats = useCallback(async () => {
    const [drRes, bayutRes, highRes, conflictsRes] = await Promise.all([
      supabase.from('dubai_residentials_full').select('url', { count: 'exact', head: true }),
      supabase.from('bayut_community_rentals').select('id', { count: 'exact', head: true }),
      supabase.from('listing_matches').select('id', { count: 'exact', head: true }).gte('score', 95).eq('is_authorized', false),
      supabase.from('permit_conflicts').select('id', { count: 'exact', head: true }),
    ])
    setStats({
      total_dr:  drRes.count ?? 0,
      total_bayut: bayutRes.count ?? 0,
      high_risk: highRes.count ?? 0,
      conflicts: conflictsRes.count ?? 0,
    })
  }, [])

  useEffect(() => { fetchMatches(); fetchStats() }, [fetchMatches, fetchStats])

  useEffect(() => {
    const channel = supabase
      .channel('listing_matches_live')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'listing_matches' }, (payload) => {
        const row = payload.new as Match
        setNewAlert(row)
        setMatches(prev => [row, ...prev])
        setStats(s => ({ ...s, high_risk: s.high_risk + 1 }))
        setTimeout(() => setNewAlert(null), 6000)
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [])

  // One best match per DR unit
  const dedupedMatches = (() => {
    const seen = new Set<string>()
    const out: Match[] = []
    const filtered = community === 'All'
      ? matches
      : matches.filter(m => m.dubai_residentials_full?.community === community)
    for (const m of filtered) {
      if (!seen.has(m.dr_url)) { seen.add(m.dr_url); out.push(m) }
    }
    return out
  })()

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">

      {/* Alert banner */}
      {newAlert && (
        <div className="bg-red-600 text-white text-sm font-medium px-4 py-2.5 flex items-center gap-3">
          <span className="animate-pulse">🚨</span>
          New high-score match detected — Score: {newAlert.score}%
          <button onClick={() => setNewAlert(null)} className="ml-auto opacity-70 hover:opacity-100">✕</button>
        </div>
      )}

      <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-6">

        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-zinc-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Live feed of similar listings found on Bayut</p>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'DR Properties',     value: stats.total_dr,   color: 'text-violet-600 dark:text-violet-400',   bg: 'bg-violet-50 dark:bg-violet-900/20'   },
            { label: 'Bayut Monitored',   value: stats.total_bayut, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-900/20' },
            { label: 'High-Risk Matches', value: stats.high_risk,  color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-900/20' },
            { label: 'Confirmed Stolen',  value: stats.conflicts,  color: 'text-red-600 dark:text-red-400',     bg: 'bg-red-50 dark:bg-red-900/20',
              href: '/conflicts' },
          ].map(s => (
            s.href
              ? <Link key={s.label} href={s.href}
                  className={`${s.bg} rounded-xl p-4 flex flex-col gap-1 border border-transparent hover:border-red-200 dark:hover:border-red-800 transition-colors`}>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">{s.label}</p>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value.toLocaleString()}</p>
                </Link>
              : <div key={s.label} className={`${s.bg} rounded-xl p-4 flex flex-col gap-1`}>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">{s.label}</p>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value.toLocaleString()}</p>
                </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Min score</label>
            <select
              className="border border-zinc-200 dark:border-zinc-700 rounded-lg px-2.5 py-1.5 text-sm bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 shadow-sm"
              value={threshold} onChange={e => setThreshold(Number(e.target.value))}>
              {[60, 70, 75, 80, 85, 90, 95].map(v => <option key={v} value={v}>{v}%</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Community</label>
            <select
              className="border border-zinc-200 dark:border-zinc-700 rounded-lg px-2.5 py-1.5 text-sm bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 shadow-sm"
              value={community} onChange={e => setCommunity(e.target.value)}>
              {COMMUNITIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">DR listings</label>
            <select
              className="border border-zinc-200 dark:border-zinc-700 rounded-lg px-2.5 py-1.5 text-sm bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 shadow-sm"
              value={authFilter} onChange={e => setAuthFilter(e.target.value as AuthFilter)}>
              <option value="hide">Hide authorized</option>
              <option value="show">Show all</option>
            </select>
          </div>
          <span className="text-sm text-zinc-400 dark:text-zinc-500 ml-auto">
            {loading ? 'Loading…' : `${dedupedMatches.length} properties`}
          </span>
        </div>

        {/* Cards */}
        {loading ? (
          <div className="flex items-center justify-center py-32 text-zinc-400 dark:text-zinc-600">
            <svg className="animate-spin w-6 h-6 mr-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Loading matches…
          </div>
        ) : dedupedMatches.length === 0 ? (
          <div className="text-center py-32 text-zinc-400 dark:text-zinc-600">No matches found for this filter</div>
        ) : (
          <div className="space-y-3">
            {dedupedMatches.map(m => {
              const dr = m.dubai_residentials_full
              const b  = m.bayut_community_rentals
              if (!dr || !b) return null
              const riskColor =
                m.score >= 95 ? 'border-l-red-500'
                : m.score >= 75 ? 'border-l-orange-400'
                : 'border-l-yellow-400'

              return (
                <div key={m.id}
                  className={`bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-700 border-l-4 ${riskColor} shadow-sm hover:shadow-md transition-shadow overflow-hidden`}>

                  <div className="flex flex-col sm:flex-row">
                    {/* Photos strip */}
                    {(dr.photos?.[0] || b.cover_photo) && (
                      <div className="flex sm:flex-col w-full sm:w-28 h-24 sm:h-auto shrink-0">
                        <div className="flex-1 relative bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                          {dr.photos?.[0]
                            ? <img src={dr.photos[0]} alt="" className="w-full h-full object-cover" /> // eslint-disable-line
                            : <div className="w-full h-full flex items-center justify-center text-zinc-300 text-xs">No photo</div>}
                          <span className="absolute bottom-1 left-1 text-[10px] bg-violet-600 text-white px-1.5 py-0.5 rounded font-medium">DR</span>
                        </div>
                        <div className="flex-1 relative bg-zinc-100 dark:bg-zinc-800 overflow-hidden border-t sm:border-t border-l sm:border-l-0 border-zinc-200 dark:border-zinc-700">
                          {b.cover_photo
                            ? <img src={b.cover_photo} alt="" className="w-full h-full object-cover" /> // eslint-disable-line
                            : <div className="w-full h-full flex items-center justify-center text-zinc-300 text-xs">No photo</div>}
                          <span className="absolute bottom-1 left-1 text-[10px] bg-orange-500 text-white px-1.5 py-0.5 rounded font-medium">Bayut</span>
                        </div>
                      </div>
                    )}

                    {/* Content */}
                    <div className="flex-1 flex flex-col sm:flex-row gap-4 p-4">

                      {/* DR info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-bold text-violet-600 dark:text-violet-400 uppercase tracking-widest mb-1">Your Property</p>
                        <p className="text-sm font-semibold text-zinc-900 dark:text-white truncate">{dr.location}</p>
                        <p className="text-xs font-mono text-zinc-400 dark:text-zinc-500 mt-0.5">{dr.unit_id}</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                          {dr.beds}bd · {dr.baths}ba · {dr.size_sqft?.toLocaleString()} sqft
                        </p>
                        <p className="text-sm font-bold text-zinc-900 dark:text-white mt-1">
                          AED {dr.price_aed?.toLocaleString()}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                          <span className="text-[10px] text-zinc-400 dark:text-zinc-500">{dr.community}</span>
                          {m.dr_building && (
                            <span className="text-[10px] bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 px-1.5 py-0.5 rounded">Bldg {m.dr_building}</span>
                          )}
                        </div>
                        <a href={m.dr_url} target="_blank" rel="noopener noreferrer"
                          className="mt-2 inline-block text-xs bg-violet-600 hover:bg-violet-700 text-white px-3 py-1.5 rounded-lg">
                          View on DR ↗
                        </a>
                      </div>

                      {/* Score */}
                      <div className="flex sm:flex-col items-center sm:items-center gap-3 sm:gap-2 sm:w-32 shrink-0">
                        <ScoreBadge score={m.score} />
                        <div className="flex sm:flex-col gap-2 flex-wrap">
                          <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${
                            m.building_match === true  ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800' :
                            m.building_match === false ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800' :
                                                         'bg-zinc-50 dark:bg-zinc-800 text-zinc-400 border-zinc-200 dark:border-zinc-700'
                          }`}>
                            {m.building_match === true ? '✓ Same bldg' : m.building_match === false ? '✗ Diff bldg' : '? Bldg unknown'}
                          </span>
                          {m.is_authorized && (
                            <span className="text-[10px] px-2 py-0.5 rounded border font-medium bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800">
                              ✓ Authorized
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Bayut info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-bold text-orange-500 uppercase tracking-widest mb-1">Bayut Listing</p>
                        <a href={b.url} target="_blank" rel="noopener noreferrer"
                          className="text-sm font-semibold text-zinc-900 dark:text-white hover:text-violet-600 dark:hover:text-violet-400 truncate block">
                          {b.title}
                        </a>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                          {b.beds}bd · {b.baths}ba · {b.area_sqft?.toLocaleString()} sqft
                        </p>
                        <p className="text-sm font-bold text-zinc-900 dark:text-white mt-1">
                          AED {b.price?.amount?.toLocaleString()}
                        </p>
                        {b.agent?.name && (
                          <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-1 truncate">
                            {b.agent.name} · {b.agency?.name}
                          </p>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex sm:flex-col gap-2 justify-start sm:justify-center shrink-0">
                        <Link href={`/property/${encodeURIComponent(m.dr_url)}`}
                          className="text-xs bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 px-3 py-1.5 rounded-lg text-center whitespace-nowrap">
                          All matches →
                        </Link>
                        <a href={b.url} target="_blank" rel="noopener noreferrer"
                          className="text-xs bg-orange-50 dark:bg-orange-900/20 hover:bg-orange-100 dark:hover:bg-orange-900/40 text-orange-700 dark:text-orange-400 px-3 py-1.5 rounded-lg text-center whitespace-nowrap">
                          View on Bayut ↗
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
