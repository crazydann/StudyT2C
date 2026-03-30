'use client'

interface WeekData {
  label: string
  correctRate: number | null
  totalProblems: number
}

interface Props {
  data: WeekData[]
  title?: string
}

function barColor(rate: number | null): string {
  if (rate === null) return 'bg-gray-300'
  if (rate >= 70) return 'bg-green-500'
  if (rate >= 50) return 'bg-yellow-500'
  return 'bg-red-500'
}

function trendArrow(data: WeekData[]): string | null {
  const valid = data.filter((d) => d.correctRate !== null)
  if (valid.length < 2) return null
  const last = valid[valid.length - 1].correctRate as number
  const prev = valid[valid.length - 2].correctRate as number
  return last >= prev ? '📈' : '📉'
}

export default function GrowthChart({ data, title }: Props) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-4">성장 데이터가 없습니다.</p>
  }

  const arrow = trendArrow(data)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-800">
          {title ?? '주간 성장 그래프'}
          {arrow && <span className="ml-2">{arrow}</span>}
        </h4>
      </div>
      <div className="flex items-end gap-1 h-28">
        {data.map((d, i) => {
          const height = d.correctRate !== null ? Math.max(4, d.correctRate) : 8
          const color = barColor(d.correctRate)
          const label = d.correctRate !== null ? `${d.label}: ${d.correctRate}%` : `${d.label}: 데이터 없음`
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end gap-1" style={{ height: '100%' }}>
              <div
                className={`w-full rounded-t transition-all ${color}`}
                style={{ height: `${height}%` }}
                title={label}
              />
              <span
                className="text-gray-400 text-center leading-tight block"
                style={{ fontSize: '10px', maxWidth: '100%', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}
              >
                {d.label.length > 4 ? d.label.slice(0, 4) : d.label}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex gap-3 mt-2 text-xs text-gray-500">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-green-500 inline-block" />70%↑</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-yellow-500 inline-block" />50~70%</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-red-500 inline-block" />50% 미만</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-gray-300 inline-block" />없음</span>
      </div>
    </div>
  )
}
