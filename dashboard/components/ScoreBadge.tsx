export default function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 90 ? 'bg-red-100 text-red-700 border-red-300' :
    score >= 75 ? 'bg-orange-100 text-orange-700 border-orange-300' :
    score >= 60 ? 'bg-yellow-100 text-yellow-700 border-yellow-300' :
                  'bg-gray-100 text-gray-600 border-gray-300'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-semibold ${color}`}>
      {score}%
    </span>
  )
}
