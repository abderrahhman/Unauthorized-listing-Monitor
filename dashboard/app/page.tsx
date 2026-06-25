'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import Sidebar from '@/components/Sidebar'
import ScoreBadge from '@/components/ScoreBadge'
import ScoreBreakdown from '@/components/ScoreBreakdown'

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

type Stats = { total_dr: number; total_bayut: number; high_risk: number }
type AuthFilter = 'hide' | 'show'

const COMMUNITIES = [
  'All', 'Al Khail Gate', 'Bluewaters', 'Citywalk', 'Discovery Gardens',
  'Dubai Wharf', 'Garden View Apartments', 'Garden View Villas', 'Gardens Apartments',
  'International City', 'Manazel Al Khor', 'Meydan Residence 1', 'The Gardens',
]

export default function Dashboard() {
  const [matches, setMatches] = useState<Match[]>([])
  const [stats, setStats] = useState<Stats>({ total_dr: 0, total_bayut: 0, high_risk: 0 })
  const [threshold, setThreshold] = useState(95)
  const [community, setCommunity] = useState('All')
  const [authFilter, setAuthFilter] = useState<AuthFilter>('hide')
  const [loading, setLoading] = useState(true)
  const [newAlert, setNewAlert] = useState<Match | null>(null)
  const [lastScrape] = useState<string>('Not yet run')

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

    if (authFilter === 'hide') {
      q = q.eq('is_authorized', false)
    }

    // Fetch enough to cover all DR units after dedup
    q = q.limit(2000)

    const { data } = await q
    if (data) setMatches(data as unknown as Match[])
    setLoading(false)
  }, [threshold, authFilter])

  const fetchStats = useCallback(async () => {
    const [drRes, bayutRes, highRes] = await Promise.all([
      supabase.from('dubai_residentials_full').select('url', { count: 'exact', head: true }),
      supabase.from('bayut_community_rentals').select('id', { count: 'exact', head: true }),
      supabase.from('listing_matches').select('id', { count: 'exact', head: true }).gte('score', 95).eq('is_authorized', false),
    ])
    setStats({
      total_dr: drRes.count ?? 0,
      total_bayut: bayutRes.count ?? 0,
      high_risk: highRes.count ?? 0,
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

  // One best match per DR unit (matches already sorted score DESC)
  const dedupedMatches = (() => {
    const seen = new Set<string>()
    const out: Match[] = []
    const filtered = community === 'All'
      ? matches
      : matches.filter(m => m.dubai_residentials_full?.community === community)
    for (const m of filtered) {
      if (!seen.has(m.dr_url)) {
        seen.add(m.dr_url)
        out.push(m)
      }
    }
    return out
  })()

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-6xl mx-auto">

          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-sm text-gray-500 mt-1">Live feed of similar listings found on Bayut</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs text-gray-400">Last scrape</p>
                <p className="text-xs font-medium text-gray-600">{lastScrape}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs text-gray-500">Live</span>
              </div>
            </div>
          </div>

          {newAlert && (
            <div className="mb-6 bg-red-50 border border-red-300 rounded-xl p-4 flex items-center gap-3">
              <span className="text-2xl">🚨</span>
              <div>
                <p className="font-semibold text-red-700 text-sm">New high-score match detected!</p>
                <p className="text-red-600 text-xs mt-0.5">Score: {newAlert.score}%</p>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { label: 'DR Properties', value: stats.total_dr, color: 'text-blue-600' },
              { label: 'Bayut Listings Monitored', value: stats.total_bayut, color: 'text-purple-600' },
              { label: 'High-Risk Matches (≥95%)', value: stats.high_risk, color: 'text-red-600' },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <p className="text-xs text-gray-500 mb-2">{s.label}</p>
                <p className={`text-3xl font-bold ${s.color}`}>{s.value.toLocaleString()}</p>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-5">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Min score</label>
              <select className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm"
                value={threshold} onChange={e => setThreshold(Number(e.target.value))}>
                {[60, 70, 75, 80, 85, 90, 95].map(v => <option key={v} value={v}>{v}%</option>)}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Community</label>
              <select className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm"
                value={community} onChange={e => setCommunity(e.target.value)}>
                {COMMUNITIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Show DR authorized</label>
              <select className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white shadow-sm"
                value={authFilter} onChange={e => setAuthFilter(e.target.value as AuthFilter)}>
                <option value="hide">No</option>
                <option value="show">Yes</option>
              </select>
            </div>

            <span className="text-sm text-gray-400 ml-auto">{dedupedMatches.length} properties</span>
          </div>

          {/* Matches */}
          {loading ? (
            <div className="text-center py-20 text-gray-400">Loading...</div>
          ) : dedupedMatches.length === 0 ? (
            <div className="text-center py-20 text-gray-400">No matches found</div>
          ) : (
            <div className="space-y-4">
              {dedupedMatches.map(m => {
                const dr = m.dubai_residentials_full
                const b = m.bayut_community_rentals
                if (!dr || !b) return null
                const drPhoto = dr.photos?.[0]
                return (
                  <div key={m.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">

                    {/* Status bar */}
                    <div className={`h-1 w-full ${m.is_authorized ? 'bg-green-400' : m.building_match === true ? 'bg-orange-400' : m.building_match === false ? 'bg-red-400' : 'bg-gray-200'}`} />

                    {/* Photos */}
                    {(drPhoto || b.cover_photo) && (
                      <div className="flex h-36 border-b border-gray-100">
                        <div className="flex-1 relative bg-gray-100 overflow-hidden">
                          {drPhoto
                            ? <img src={drPhoto} alt="DR property" className="w-full h-full object-cover" /> // eslint-disable-line
                            : <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">No photo</div>}
                          <span className="absolute top-2 left-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded font-medium">Your Property</span>
                        </div>
                        <div className="flex-1 relative bg-gray-100 overflow-hidden">
                          {b.cover_photo
                            ? <img src={b.cover_photo} alt="Bayut listing" className="w-full h-full object-cover" /> // eslint-disable-line
                            : <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">No photo</div>}
                          <span className="absolute top-2 left-2 text-xs bg-orange-500 text-white px-2 py-0.5 rounded font-medium">Bayut Listing</span>
                        </div>
                      </div>
                    )}

                    <div className="flex gap-6 p-5">
                      {/* DR info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">Your Property</p>
                        <p className="text-sm font-medium text-gray-900 truncate">{dr.location}</p>
                        <p className="text-xs text-gray-400 mt-0.5 font-mono">{dr.unit_id}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {dr.beds}bd · {dr.baths}ba · {dr.size_sqft?.toLocaleString()} sqft
                        </p>
                        <p className="text-sm font-bold text-gray-900 mt-1">AED {dr.price_aed?.toLocaleString()}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-400">{dr.community}</span>
                          {m.dr_building && (
                            <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">Bldg {m.dr_building}</span>
                          )}
                        </div>
                        <a href={m.dr_url} target="_blank" rel="noopener noreferrer"
                          className="mt-3 inline-block text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg whitespace-nowrap">
                          View on DR ↗
                        </a>
                      </div>

                      {/* Score + building status */}
                      <div className="flex flex-col items-center gap-2 w-44 shrink-0">
                        <ScoreBadge score={m.score} />
                        <ScoreBreakdown b={m} />
                        {/* Building match badge */}
                        <div className={`text-xs px-2 py-0.5 rounded border font-medium ${
                          m.building_match === true  ? 'bg-green-50 text-green-700 border-green-200' :
                          m.building_match === false ? 'bg-red-50 text-red-600 border-red-200' :
                                                       'bg-gray-50 text-gray-400 border-gray-200'
                        }`}>
                          {m.building_match === true  ? '✓ Same building' :
                           m.building_match === false ? '✗ Diff building' :
                                                        '? Building unknown'}
                        </div>
                        {/* Authorization badge */}
                        <div className={`text-xs px-2 py-0.5 rounded border font-medium ${
                          m.is_authorized
                            ? 'bg-green-50 text-green-700 border-green-200'
                            : 'bg-orange-50 text-orange-600 border-orange-200'
                        }`}>
                          {m.is_authorized ? '✓ Authorized (DR)' : '⚠ Unverified listing'}
                        </div>
                      </div>

                      {/* Bayut info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-orange-500 uppercase tracking-wide mb-1">Bayut Listing</p>
                        <a href={b.url} target="_blank" rel="noopener noreferrer"
                          className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate block">
                          {b.title}
                        </a>
                        <p className="text-xs text-gray-500 mt-1">
                          {b.beds}bd · {b.baths}ba · {b.area_sqft?.toLocaleString()} sqft
                        </p>
                        <p className="text-sm font-bold text-gray-900 mt-1">AED {b.price?.amount?.toLocaleString()}</p>
                        <div className="flex items-center gap-2 mt-1">
                          {b.agent?.name && <p className="text-xs text-gray-400 truncate">{b.agent.name} · {b.agency?.name}</p>}
                          {m.bayut_building && (
                            <span className="text-xs bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded shrink-0">Bldg {m.bayut_building}</span>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex flex-col gap-2 justify-center shrink-0">
                        <Link href={`/property/${encodeURIComponent(m.dr_url)}`}
                          className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 px-3 py-1.5 rounded-lg text-center whitespace-nowrap">
                          All matches →
                        </Link>
                        <a href={b.url} target="_blank" rel="noopener noreferrer"
                          className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-center whitespace-nowrap">
                          View on Bayut ↗
                        </a>
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
