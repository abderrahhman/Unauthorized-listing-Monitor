type Breakdown = {
  score_beds: number
  score_baths: number
  score_size: number
  score_price: number
}

export default function ScoreBreakdown({ b }: { b: Breakdown }) {
  const items = [
    { label: 'Beds',  matched: b.score_beds > 0,  pct: b.score_beds  > 0 ? 100 : 0,                   exact: b.score_beds  === 40 },
    { label: 'Baths', matched: b.score_baths > 0, pct: b.score_baths > 0 ? 100 : 0,                   exact: b.score_baths === 20 },
    { label: 'Size',  matched: b.score_size  > 0, pct: Math.round((b.score_size  / 20) * 100),         exact: b.score_size  === 20 },
    { label: 'Price', matched: b.score_price > 0, pct: Math.round((b.score_price / 20) * 100),         exact: b.score_price === 20 },
  ]
  return (
    <div className="space-y-1.5 w-full">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-2 text-xs">
          <span className="w-8 text-gray-500 shrink-0">{item.label}</span>
          {item.matched ? (
            <>
              <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full ${item.pct === 100 ? 'bg-green-500' : 'bg-blue-400'}`}
                  style={{ width: `${item.pct}%` }}
                />
              </div>
              <span className={`w-8 text-right shrink-0 font-medium ${item.pct === 100 ? 'text-green-600' : 'text-blue-600'}`}>
                {item.pct}%
              </span>
            </>
          ) : (
            <>
              <div className="flex-1 bg-gray-100 rounded-full h-1.5" />
              <span className="w-8 text-right shrink-0 text-red-400">✗</span>
            </>
          )}
        </div>
      ))}
    </div>
  )
}
