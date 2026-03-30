'use client'

interface DataPoint {
  label: string
  correctRate: number | null
  totalProblems: number
}

interface Props {
  data: DataPoint[]
}

export default function WeeklyMiniChart({ data }: Props) {
  if (!data || data.length === 0) return null

  const maxProblems = Math.max(...data.map((d) => d.totalProblems), 1)

  function getBarColor(rate: number | null): string {
    if (rate === null) return 'bg-gray-200'
    if (rate >= 80) return 'bg-green-400'
    if (rate >= 60) return 'bg-blue-400'
    if (rate >= 40) return 'bg-yellow-400'
    return 'bg-red-400'
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-3">
      <p className="text-xs font-semibold text-gray-700 mb-2">이번 주 학습 현황</p>
      <div className="flex items-end gap-1 h-14">
        {data.map((d, i) => {
          const heightPercent = d.totalProblems > 0 ? Math.max(10, Math.round((d.totalProblems / maxProblems) * 100)) : 0
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5" title={d.totalProblems > 0 ? `${d.label}: ${d.totalProblems}문제 (${d.correctRate ?? 0}%)` : `${d.label}: 없음`}>
              <div className="w-full flex items-end justify-center" style={{ height: '44px' }}>
                <div
                  className={`w-full rounded-t transition-all duration-500 ${getBarColor(d.correctRate)}`}
                  style={{ height: d.totalProblems > 0 ? `${heightPercent}%` : '2px' }}
                />
              </div>
              <span className="text-gray-400 text-center leading-none" style={{ fontSize: '9px' }}>{d.label}</span>
            </div>
          )
        })}
      </div>
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        {[
          { color: 'bg-green-400', label: '80%+' },
          { color: 'bg-blue-400', label: '60%+' },
          { color: 'bg-yellow-400', label: '40%+' },
          { color: 'bg-red-400', label: '<40%' },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-0.5">
            <div className={`w-2 h-2 rounded-sm ${item.color}`} />
            <span className="text-gray-400" style={{ fontSize: '9px' }}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
