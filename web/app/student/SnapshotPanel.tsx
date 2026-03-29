'use client'

interface Snapshot {
  strongConcepts: string[]
  weakConcepts: string[]
  totalProblems: number
  correctRate: number
}

interface Props {
  snapshot: Snapshot | null
  loading: boolean
  onConceptClick?: (concept: string) => void
}

export default function SnapshotPanel({ snapshot, loading, onConceptClick }: Props) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-100 rounded w-1/2" />
          <div className="h-3 bg-gray-100 rounded w-full" />
          <div className="h-3 bg-gray-100 rounded w-3/4" />
        </div>
      </div>
    )
  }

  if (!snapshot || snapshot.totalProblems === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
        <div className="text-2xl mb-2">📊</div>
        <p className="text-xs text-gray-500">채점을 해보면<br />학습 현황을 분석해드려요</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">학습 스냅샷</h3>
        <span className={`text-xs font-bold ${snapshot.correctRate >= 70 ? 'text-green-600' : snapshot.correctRate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
          {snapshot.correctRate}%
        </span>
      </div>
      <p className="text-xs text-gray-400">최근 {snapshot.totalProblems}문제 기준</p>

      {snapshot.strongConcepts.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1.5 font-medium">💪 강점</p>
          <div className="flex flex-wrap gap-1">
            {snapshot.strongConcepts.map((c) => (
              <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">{c}</span>
            ))}
          </div>
        </div>
      )}

      {snapshot.weakConcepts.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1.5 font-medium">🔥 보완 필요</p>
          <div className="flex flex-wrap gap-1">
            {snapshot.weakConcepts.map((c) => (
              <button
                key={c}
                onClick={() => onConceptClick?.(c)}
                className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors"
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
