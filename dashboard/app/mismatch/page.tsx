'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Sidebar from '@/components/Sidebar'

type Row = {
  id: number
  status: 'matched' | 'missing_from_bayut' | 'extra_on_bayut'
  dr_url: string | null
  bayut_url: string | null
  dr_beds: number | null
  dr_baths: number | null
  dr_size_sqft: number | null
  dr_price_aed: number | null
  dr_location: string | null
  dr_community: string | null
  dr_unit_id: string | null
  bayut_beds: number | null
  bayut_baths: number | null
  bayut_sqft: number | null
  bayut_price: number | null
  bayut_location: string | null
  bayut_reference: string | null
  bayut_permit: string | null
  price_diff_pct: number | null
  size_diff_pct: number | null
  building_match: boolean | null
  dr_building: string | null
  bayut_building: string | null
}

type Tab = 'all' | 'matched' | 'missing_from_bayut' | 'extra_on_bayut'

export default function MismatchPage() {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('all')
  const [priceOnly, setPriceOnly] = useState(false)

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from('dr_bayut_comparison')
        .select('*')
        .order('status')
        .limit(500)
      setRows((data ?? []) as Row[])
      setLoading(false)
    }
    load()
  }, [])

  const filtered = rows.filter(r => {
    if (tab !== 'all' && r.status !== tab) return false
    if (priceOnly && r.status === 'matched') return (r.price_diff_pct ?? 0) > 5
    return true
  })

  const counts = {
    matched:            rows.filter(r => r.status === 'matched').length,
    missing_from_bayut: rows.filter(r => r.status === 'missing_from_bayut').length,
    extra_on_bayut:     rows.filter(r => r.status === 'extra_on_bayut').length,
    price_mismatch:     rows.filter(r => r.status === 'matched' && (r.price_diff_pct ?? 0) > 5).length,
  }

  const tabs: { key: Tab; label: string; count: number; color: string }[] = [
    { key: 'all',               label: 'All',               count: rows.length,              color: 'bg-gray-100 text-gray-700' },
    { key: 'matched',           label: 'Matched',           count: counts.matched,           color: 'bg-green-100 text-green-700' },
    { key: 'missing_from_bayut', label: 'Missing from Bayut', count: counts.missing_from_bayut, color: 'bg-red-100 text-red-700' },
    { key: 'extra_on_bayut',    label: 'Extra on Bayut',    count: counts.extra_on_bayut,    color: 'bg-orange-100 text-orange-700' },
  ]

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-6xl mx-auto">

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">DR Website vs Bayut</h1>
            <p className="text-sm text-gray-500 mt-1">
              Comparing your 118 website units against your 146 official Bayut listings
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Matched', value: counts.matched, color: 'text-green-600', sub: 'found on both' },
              { label: 'Missing from Bayut', value: counts.missing_from_bayut, color: 'text-red-600', sub: 'on website, not on Bayut' },
              { label: 'Extra on Bayut', value: counts.extra_on_bayut, color: 'text-orange-600', sub: 'on Bayut, not on website' },
              { label: 'Price Mismatch', value: counts.price_mismatch, color: 'text-purple-600', sub: 'price differs >5%' },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <p className="text-xs text-gray-500 mb-1">{s.label}</p>
                <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-gray-400 mt-1">{s.sub}</p>
              </div>
            ))}
          </div>

          {/* Tabs + filters */}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex gap-2 flex-wrap">
              {tabs.map(t => (
                <button
                  key={t.key}
                  onClick={() => { setTab(t.key); setPriceOnly(false) }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    tab === t.key ? t.color + ' ring-1 ring-inset ring-current' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {t.label} <span className="ml-1 opacity-70">{t.count}</span>
                </button>
              ))}
            </div>
            {(tab === 'matched' || tab === 'all') && (
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input type="checkbox" checked={priceOnly} onChange={e => setPriceOnly(e.target.checked)}
                  className="rounded" />
                Price mismatch only (&gt;5%)
              </label>
            )}
            <span className="text-sm text-gray-400">{filtered.length} rows</span>
          </div>

          {/* Table */}
          {loading ? (
            <div className="text-center py-20 text-gray-400">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20 text-gray-400">No results</div>
          ) : (
            <div className="space-y-3">
              {filtered.map(r => (
                <div key={r.id} className={`bg-white rounded-xl border shadow-sm p-5 ${
                  r.status === 'missing_from_bayut' ? 'border-red-200' :
                  r.status === 'extra_on_bayut'    ? 'border-orange-200' :
                  (r.price_diff_pct ?? 0) > 5      ? 'border-purple-200' :
                                                      'border-gray-200'
                }`}>
                  <div className="flex items-start gap-6">

                    {/* Status badge */}
                    <div className="shrink-0 w-36">
                      <span className={`inline-block text-xs font-semibold px-2 py-1 rounded-lg ${
                        r.status === 'matched'            ? 'bg-green-100 text-green-700' :
                        r.status === 'missing_from_bayut' ? 'bg-red-100 text-red-700' :
                                                             'bg-orange-100 text-orange-700'
                      }`}>
                        {r.status === 'matched'            ? '✓ Matched' :
                         r.status === 'missing_from_bayut' ? '✗ Missing from Bayut' :
                                                              '+ Extra on Bayut'}
                      </span>
                      {r.building_match === true && (
                        <p className="text-xs text-green-600 mt-1">✓ Same building</p>
                      )}
                      {r.building_match === false && (
                        <p className="text-xs text-red-500 mt-1">✗ Diff building</p>
                      )}
                    </div>

                    {/* DR side */}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">DR Website</p>
                      {r.dr_url ? (
                        <>
                          <a href={r.dr_url} target="_blank" rel="noopener noreferrer"
                            className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate block">
                            {r.dr_location}
                          </a>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {r.dr_unit_id} · {r.dr_beds}bd · {r.dr_baths}ba · {r.dr_size_sqft?.toLocaleString()} sqft
                          </p>
                          <p className="text-sm font-bold text-gray-900 mt-1">
                            AED {r.dr_price_aed?.toLocaleString()}
                          </p>
                          {r.dr_building && <p className="text-xs text-gray-400 mt-0.5">Building {r.dr_building}</p>}
                        </>
                      ) : (
                        <p className="text-sm text-gray-400 italic">Not on DR website</p>
                      )}
                    </div>

                    {/* Diff column */}
                    {r.status === 'matched' && (
                      <div className="shrink-0 w-32 text-center">
                        {(r.price_diff_pct ?? 0) > 0 ? (
                          <div className={`rounded-lg px-2 py-1 text-xs font-semibold ${
                            (r.price_diff_pct ?? 0) > 10 ? 'bg-red-100 text-red-700' :
                            (r.price_diff_pct ?? 0) > 5  ? 'bg-orange-100 text-orange-700' :
                                                            'bg-yellow-100 text-yellow-700'
                          }`}>
                            Price diff<br />{r.price_diff_pct}%
                          </div>
                        ) : (
                          <div className="rounded-lg px-2 py-1 text-xs bg-green-100 text-green-700 font-semibold">
                            Price match
                          </div>
                        )}
                        {(r.size_diff_pct ?? 0) > 0 && (
                          <div className="mt-1 text-xs text-gray-400">
                            Size diff: {r.size_diff_pct}%
                          </div>
                        )}
                      </div>
                    )}

                    {/* Bayut side */}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-orange-500 uppercase tracking-wide mb-1">Bayut (DR Official)</p>
                      {r.bayut_url ? (
                        <>
                          <a href={r.bayut_url} target="_blank" rel="noopener noreferrer"
                            className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate block">
                            {r.bayut_location}
                          </a>
                          <p className="text-xs text-gray-500 mt-0.5">
                            Ref: {r.bayut_reference} · {r.bayut_beds}bd · {r.bayut_baths}ba · {r.bayut_sqft?.toLocaleString()} sqft
                          </p>
                          <p className="text-sm font-bold text-gray-900 mt-1">
                            AED {r.bayut_price?.toLocaleString()}
                          </p>
                          {r.bayut_building && <p className="text-xs text-gray-400 mt-0.5">Building {r.bayut_building}</p>}
                          {r.bayut_permit && <p className="text-xs text-gray-400">Permit: {r.bayut_permit}</p>}
                        </>
                      ) : (
                        <p className="text-sm text-gray-400 italic">Not on Bayut</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
