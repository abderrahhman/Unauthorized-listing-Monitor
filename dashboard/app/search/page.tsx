'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

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
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">

        <div className="mb-6">
          <h1 className="text-xl font-bold text-zinc-900 dark:text-white">Search Properties</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Search by name, ID, community, or location</p>
        </div>

        <div className="relative mb-6">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400">🔍</span>
          <input
            type="text"
            placeholder="e.g. Al Khail Gate, 2bedroom, Phase II-1, akg-1-28..."
            className="w-full pl-10 pr-4 py-3 border border-zinc-200 dark:border-zinc-700 rounded-xl text-sm bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-violet-500 placeholder:text-zinc-400 dark:placeholder:text-zinc-600"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
        </div>

        {loading && <div className="text-center py-20 text-zinc-400 dark:text-zinc-600">Searching...</div>}

        {!loading && searched && results.length === 0 && (
          <div className="text-center py-20 text-zinc-400 dark:text-zinc-600">No properties found for &ldquo;{query}&rdquo;</div>
        )}

        {!loading && !searched && (
          <div className="text-center py-20 text-zinc-300 dark:text-zinc-700 text-sm">Start typing to search</div>
        )}

        {!loading && results.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-3">
              {results.length} result{results.length !== 1 ? 's' : ''}
            </p>
            {results.map(p => (
              <Link
                key={p.url}
                href={`/property/${encodeURIComponent(p.url)}`}
                className="block bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm hover:shadow-md hover:border-violet-200 dark:hover:border-violet-800 transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/20 px-2 py-0.5 rounded">
                        {p.community}
                      </span>
                      {p.apartment_type && (
                        <span className="text-xs text-zinc-400 dark:text-zinc-500">{p.apartment_type}</span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-zinc-900 dark:text-white truncate">{p.location}</p>
                    <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
                      ID: {p.property_id} · Unit: {p.unit_id}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-white">AED {p.price_aed?.toLocaleString()}</p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                      {p.beds}bd · {p.baths}ba · {p.size_sqft?.toLocaleString()} sqft
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
