'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import Sidebar from '@/components/Sidebar'

type DRProperty = {
  url: string
  community: string
  property_id: string
  unit_id: string
  apartment_type: string
  location: string
  price_aed: number
  beds: number
  baths: number
  size_sqft: number
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DRProperty[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setSearched(false); return }
    setLoading(true)
    setSearched(true)

    const term = q.trim().toLowerCase()
    const { data } = await supabase
      .from('dubai_residentials_full')
      .select('url, community, property_id, unit_id, apartment_type, location, price_aed, beds, baths, size_sqft')
      .or(`location.ilike.%${term}%,community.ilike.%${term}%,property_id.ilike.%${term}%,unit_id.ilike.%${term}%,apartment_type.ilike.%${term}%`)
      .order('community')
      .limit(50)

    setResults((data ?? []) as DRProperty[])
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => search(query), 300)
    return () => clearTimeout(t)
  }, [query, search])

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-4xl mx-auto">

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Search Properties</h1>
            <p className="text-sm text-gray-500 mt-1">Search by name, ID, community, or location</p>
          </div>

          <div className="relative mb-6">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
            <input
              type="text"
              placeholder="e.g. Al Khail Gate, 2bedroom, Phase II-1, akg-1-28..."
              className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={query}
              onChange={e => setQuery(e.target.value)}
              autoFocus
            />
          </div>

          {loading && <div className="text-center py-20 text-gray-400">Searching...</div>}

          {!loading && searched && results.length === 0 && (
            <div className="text-center py-20 text-gray-400">No properties found for &ldquo;{query}&rdquo;</div>
          )}

          {!loading && !searched && (
            <div className="text-center py-20 text-gray-300 text-sm">Start typing to search</div>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs text-gray-400 mb-3">{results.length} result{results.length !== 1 ? 's' : ''}</p>
              {results.map(p => (
                <Link
                  key={p.url}
                  href={`/property/${encodeURIComponent(p.url)}`}
                  className="block bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-blue-200 transition-all"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                          {p.community}
                        </span>
                        {p.apartment_type && (
                          <span className="text-xs text-gray-400">{p.apartment_type}</span>
                        )}
                      </div>
                      <p className="text-sm font-medium text-gray-900 truncate">{p.location}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        ID: {p.property_id} · Unit: {p.unit_id}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold text-gray-900">AED {p.price_aed?.toLocaleString()}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {p.beds}bd · {p.baths}ba · {p.size_sqft?.toLocaleString()} sqft
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
