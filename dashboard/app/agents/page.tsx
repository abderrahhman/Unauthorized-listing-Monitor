'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Sidebar from '@/components/Sidebar'

type AgentRow = {
  agent_name: string
  agency_name: string
  match_count: number
  avg_score: number
  max_score: number
  listings: { bayut_url: string; score: number; dr_location: string }[]
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentRow[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      // Fetch all high-score matches with agent info
      const { data } = await supabase
        .from('listing_matches')
        .select(`
          dr_url, score,
          dubai_residentials_full!listing_matches_dr_url_fkey(location),
          bayut_community_rentals!listing_matches_bayut_id_fkey(url, agent, agency)
        `)
        .gte('score', 60)
        .order('score', { ascending: false })
        .limit(2000)

      if (!data) { setLoading(false); return }

      // Group by agent
      const map = new Map<string, AgentRow>()
      for (const row of data as any[]) {
        const b = row.bayut_community_rentals
        const dr = row.dubai_residentials_full
        const agentName: string = b?.agent?.name ?? 'Unknown Agent'
        const agencyName: string = b?.agency?.name ?? ''
        const key = agentName

        if (!map.has(key)) {
          map.set(key, {
            agent_name: agentName,
            agency_name: agencyName,
            match_count: 0,
            avg_score: 0,
            max_score: 0,
            listings: [],
          })
        }
        const entry = map.get(key)!
        entry.match_count++
        entry.max_score = Math.max(entry.max_score, row.score)
        entry.listings.push({
          bayut_url: b?.url ?? '',
          score: row.score,
          dr_location: dr?.location ?? '',
        })
      }

      // Compute avg score
      const rows: AgentRow[] = Array.from(map.values()).map(a => ({
        ...a,
        avg_score: Math.round(a.listings.reduce((s, l) => s + l.score, 0) / a.listings.length),
      }))

      rows.sort((a, b) => b.match_count - a.match_count)
      setAgents(rows)
      setLoading(false)
    }
    load()
  }, [])

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-4xl mx-auto">

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Agent Fingerprinting</h1>
            <p className="text-sm text-gray-500 mt-1">
              Agents ranked by number of high-similarity matches with your properties
            </p>
          </div>

          {loading ? (
            <div className="text-center py-20 text-gray-400">Loading...</div>
          ) : (
            <div className="space-y-3">
              {agents.map((a, i) => (
                <div key={a.agent_name} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                  <button
                    className="w-full flex items-center gap-4 p-5 text-left hover:bg-gray-50 transition-colors"
                    onClick={() => setExpanded(expanded === a.agent_name ? null : a.agent_name)}
                  >
                    {/* Rank */}
                    <span className="w-7 h-7 rounded-full bg-gray-100 text-gray-500 text-xs font-bold flex items-center justify-center shrink-0">
                      {i + 1}
                    </span>

                    {/* Agent info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{a.agent_name}</p>
                      <p className="text-xs text-gray-400">{a.agency_name}</p>
                    </div>

                    {/* Stats */}
                    <div className="flex items-center gap-6 shrink-0 text-right">
                      <div>
                        <p className="text-xs text-gray-400">Matches</p>
                        <p className="text-lg font-bold text-gray-900">{a.match_count}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Avg score</p>
                        <p className={`text-lg font-bold ${a.avg_score >= 80 ? 'text-red-600' : a.avg_score >= 70 ? 'text-orange-500' : 'text-gray-600'}`}>
                          {a.avg_score}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Top score</p>
                        <p className="text-lg font-bold text-gray-900">{a.max_score}%</p>
                      </div>
                      <span className="text-gray-300">{expanded === a.agent_name ? '▲' : '▼'}</span>
                    </div>
                  </button>

                  {/* Expanded listings */}
                  {expanded === a.agent_name && (
                    <div className="border-t border-gray-100 px-5 py-3 space-y-2 bg-gray-50">
                      {a.listings.slice(0, 10).map((l, j) => (
                        <div key={j} className="flex items-center justify-between text-xs">
                          <span className="text-gray-600 truncate flex-1 mr-4">{l.dr_location}</span>
                          <span className="text-gray-400 mr-4">Score: <strong>{l.score}%</strong></span>
                          <a href={l.bayut_url} target="_blank" rel="noopener noreferrer"
                            className="text-blue-500 hover:underline shrink-0">
                            View on Bayut ↗
                          </a>
                        </div>
                      ))}
                      {a.listings.length > 10 && (
                        <p className="text-xs text-gray-400 pt-1">+{a.listings.length - 10} more matches</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
