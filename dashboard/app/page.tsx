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
      total_dr:    drRes.count ?? 0,
      total_bayut: bayutRes.count ?? 0,
      high_risk:   highRes.count ?? 0,
      conflicts:   conflictsRes.count ?? 0,
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
    <div className="min-h-screen bg-zinc-50 dark:bg-[#0a0a0a]">

      {/* Alert banner */}
      {newAlert && (
        <div className="bg-red-600 text-white text-sm font-medium px-4 py-2.5 flex items-center gap-3">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping shrink-0" />
          New high-score match — Score: {newAlert.score}%
          <button onClick={() => setNewAlert(null)} className="ml-auto opacity-70 hover:opacity-100 text-xs">✕</button>
        </div>
      )}

      <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-6">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">Dashboard</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-500 mt-1">Live feed of similar listings found on Bayut</p>
        </div>

        {/* Stats — no colored backgrounds, left accent border */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: 'DR Properties',     value: stats.total_dr,    sub: 'managed units',    accent: 'dark:border-l-indigo-600 border-l-indigo-500',     num: 'text-zinc-900 dark:text-white' },
            { label: 'Bayut Monitored',   value: stats.total_bayut, sub: 'scraped listings', accent: 'dark:border-l-zinc-600 border-l-zinc-400',          num: 'text-zinc-900 dark:text-white' },
            { label: 'High-Risk Matches', value: stats.high_risk,   sub: 'score ≥ 95%',      accent: 'dark:border-l-amber-500 border-l-amber-500',        num: 'text-amber-600 dark:text-amber-400' },
            { label: 'Confirmed Stolen',  value: stats.conflicts,   sub: 'permit conflicts', accent: 'dark:border-l-red-600 border-l-red-500',            num: 'text-red-600 dark:text-red-400', href: '/conflicts' },
          ].map(s => {
            const inner = (
              <>
                <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-widest mb-2">{s.label}</p>
                <p className={`text-3xl font-bold tabular-nums tracking-tight ${s.num}`}>{s.value.toLocaleString()}</p>
                <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-1">{s.sub}</p>
              </>
            )
            const cls = `bg-white dark:bg-[#111] border border-zinc-200 dark:border-[#1e1e1e] border-l-4 ${s.accent} rounded-lg p-4`
            return s.href
              ? <Link key={s.label} href={s.href} className={`${cls} hover:border-zinc-300 dark:hover:border-[#2a2a2a] transition-colors`}>{inner}</Link>
              : <div key={s.label} className={cls}>{inner}</div>
          })}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-600 uppercase tracking-widest">Min score</span>
          <select
            className="border border-zinc-200 dark:border-[#222] rounded-md px-2.5 py-1.5 text-sm bg-white dark:bg-[#111] text-zinc-700 dark:text-zinc-300"
            value={threshold} onChange={e => setThreshold(Number(e.target.value))}>
            {[60, 70, 75, 80, 85, 90, 95].map(v => <option key={v} value={v}>{v}%</option>)}
          </select>

          <div className="w-px h-4 bg-zinc-200 dark:bg-[#222]" />

          <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-600 uppercase tracking-widest">Community</span>
          <select
            className="border border-zinc-200 dark:border-[#222] rounded-md px-2.5 py-1.5 text-sm bg-white dark:bg-[#111] text-zinc-700 dark:text-zinc-300"
            value={community} onChange={e => setCommunity(e.target.value)}>
            {COMMUNITIES.map(c => <option key={c}>{c}</option>)}
          </select>

          <div className="w-px h-4 bg-zinc-200 dark:bg-[#222]" />

          <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-600 uppercase tracking-widest">DR listings</span>
          <select
            className="border border-zinc-200 dark:border-[#222] rounded-md px-2.5 py-1.5 text-sm bg-white dark:bg-[#111] text-zinc-700 dark:text-zinc-300"
            value={authFilter} onChange={e => setAuthFilter(e.target.value as AuthFilter)}>
            <option value="hide">Hide authorized</option>
            <option value="show">Show all</option>
          </select>

          <span className="text-sm text-zinc-400 dark:text-zinc-600 ml-auto tabular-nums">
            {loading ? '—' : `${dedupedMatches.length} properties`}
          </span>
        </div>

        {/* Cards */}
        {loading ? (
          <div className="flex items-center justify-center py-32 text-zinc-400 dark:text-zinc-700">
            <svg className="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <span className="text-sm">Loading matches…</span>
          </div>
        ) : dedupedMatches.length === 0 ? (
          <div className="text-center py-32 text-sm text-zinc-400 dark:text-zinc-700">No matches found for this filter</div>
        ) : (
          <div className="space-y-2">
            {dedupedMatches.map(m => {
              const dr = m.dubai_residentials_full
              const b  = m.bayut_community_rentals
              if (!dr || !b) return null

              const riskBorder =
                m.score >= 95 ? 'border-l-red-500'
                : m.score >= 75 ? 'border-l-amber-500'
                : 'border-l-yellow-500'

              return (
                <div key={m.id}
                  className={`bg-white dark:bg-[#111] border border-zinc-200 dark:border-[#1e1e1e] border-l-4 ${riskBorder} rounded-lg overflow-hidden hover:border-zinc-300 dark:hover:border-[#2a2a2a] transition-colors`}>

                  <div className="flex flex-col sm:flex-row">
                    {/* Photos */}
                    {(dr.photos?.[0] || b.cover_photo) && (
                      <div className="flex sm:flex-col w-full sm:w-24 h-20 sm:h-auto shrink-0">
                        <div className="flex-1 relative bg-zinc-100 dark:bg-[#1a1a1a] overflow-hidden">
                          {dr.photos?.[0]
                            ? <img src={dr.photos[0]} alt="" className="w-full h-full object-cover" /> // eslint-disable-line
                            : <div className="w-full h-full flex items-center justify-center text-zinc-400 text-[10px]">No photo</div>}
                          <span className="absolute bottom-1 left-1 text-[9px] bg-indigo-600 text-white px-1 py-0.5 rounded font-bold">DR</span>
                        </div>
                        <div className="flex-1 relative bg-zinc-100 dark:bg-[#1a1a1a] overflow-hidden border-t sm:border-t border-l sm:border-l-0 border-zinc-200 dark:border-[#1e1e1e]">
                          {b.cover_photo
                            ? <img src={b.cover_photo} alt="" className="w-full h-full object-cover" /> // eslint-disable-line
                            : <div className="w-full h-full flex items-center justify-center text-zinc-400 text-[10px]">No photo</div>}
                          <span className="absolute bottom-1 left-1 text-[9px] bg-amber-500 text-white px-1 py-0.5 rounded font-bold">Bayut</span>
                        </div>
                      </div>
                    )}

                    <div className="flex-1 flex flex-col sm:flex-row gap-4 p-4 min-w-0">

                      {/* DR info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1.5">Your Property</p>
                        <p className="text-sm font-semibold text-zinc-900 dark:text-white truncate">{dr.location}</p>
                        <p className="text-[11px] font-mono text-zinc-400 dark:text-zinc-600 mt-0.5">{dr.unit_id}</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-500 mt-1.5">
                          {dr.beds}bd · {dr.baths}ba · {dr.size_sqft?.toLocaleString()} sqft
                        </p>
                        <p className="text-sm font-bold text-zinc-900 dark:text-white mt-1 tabular-nums">
                          AED {dr.price_aed?.toLocaleString()}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                          <span className="text-[10px] text-zinc-400 dark:text-zinc-600">{dr.community}</span>
                          {m.dr_building && <span className="text-[10px] text-indigo-400 dark:text-indigo-600">· Bldg {m.dr_building}</span>}
                        </div>
                        <a href={m.dr_url} target="_blank" rel="noopener noreferrer"
                          className="mt-2.5 inline-block text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-md font-medium transition-colors">
                          View on DR ↗
                        </a>
                      </div>

                      {/* Score */}
                      <div className="flex sm:flex-col items-center gap-3 sm:w-28 shrink-0">
                        <ScoreBadge score={m.score} />
                        <div className="flex sm:flex-col gap-1.5 flex-wrap">
                          <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${
                            m.building_match === true  ? 'text-emerald-400 border-emerald-900/50 dark:border-emerald-900' :
                            m.building_match === false ? 'text-red-400 border-red-900/50 dark:border-red-900' :
                                                         'text-zinc-500 border-zinc-200 dark:border-[#222]'
                          }`}>
                            {m.building_match === true ? '✓ Same bldg' : m.building_match === false ? '✗ Diff bldg' : '? Bldg'}
                          </span>
                          {m.is_authorized && (
                            <span className="text-[10px] px-2 py-0.5 rounded border font-medium text-emerald-400 border-emerald-900/50 dark:border-emerald-900">
                              ✓ Authorized
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Bayut info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-semibold text-amber-500 uppercase tracking-widest mb-1.5">Bayut Listing</p>
                        <a href={b.url} target="_blank" rel="noopener noreferrer"
                          className="text-sm font-semibold text-zinc-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 truncate block">
                          {b.title}
                        </a>
                        <p className="text-xs text-zinc-500 dark:text-zinc-500 mt-1.5">
                          {b.beds}bd · {b.baths}ba · {b.area_sqft?.toLocaleString()} sqft
                        </p>
                        <p className="text-sm font-bold text-zinc-900 dark:text-white mt-1 tabular-nums">
                          AED {b.price?.amount?.toLocaleString()}
                        </p>
                        {b.agent?.name && (
                          <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-1 truncate">
                            {b.agent.name}
                            {b.agency?.name && <> · {b.agency.name}</>}
                          </p>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex sm:flex-col gap-2 justify-start sm:justify-center shrink-0">
                        <Link href={`/property/${encodeURIComponent(m.dr_url)}`}
                          className="text-xs border border-zinc-200 dark:border-[#222] hover:border-zinc-300 dark:hover:border-[#333] text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 px-3 py-1.5 rounded-md text-center whitespace-nowrap transition-colors">
                          All matches →
                        </Link>
                        <a href={b.url} target="_blank" rel="noopener noreferrer"
                          className="text-xs border border-amber-200 dark:border-amber-900/50 hover:border-amber-300 dark:hover:border-amber-800 text-amber-700 dark:text-amber-500 hover:text-amber-800 dark:hover:text-amber-400 px-3 py-1.5 rounded-md text-center whitespace-nowrap transition-colors">
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
