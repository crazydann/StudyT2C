'use client'

interface StudentCard {
  id: string
  handle: string
  correctRate: number | null
  riskLevel: 'low' | 'medium' | 'high'
  lastSeen: string | null
  todayActive: boolean
}

interface Props {
  students: StudentCard[]
  onSelect: (id: string) => void
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return '기록 없음'
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  return `${days}일 전`
}

const riskColors = {
  high:   { avatar: 'bg-red-400 text-white',    card: 'border-red-200 bg-red-50' },
  medium: { avatar: 'bg-yellow-400 text-white',  card: 'border-yellow-200 bg-yellow-50' },
  low:    { avatar: 'bg-green-400 text-white',   card: 'border-green-200 bg-green-50' },
}

export default function StudentGrid({ students, onSelect }: Props) {
  if (students.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-8">학생 데이터가 없습니다.</p>
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {students.map((s) => {
        const colors = riskColors[s.riskLevel]
        return (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`rounded-xl border p-3 text-left transition-shadow hover:shadow-md ${colors.card}`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${colors.avatar}`}>
                {s.handle[0]?.toUpperCase() ?? '?'}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">{s.handle}</p>
                {s.todayActive && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-medium">오늘 활동</span>
                )}
              </div>
            </div>
            <div className="text-xs text-gray-600 space-y-0.5">
              <p>
                정답률:{' '}
                <span className="font-medium">
                  {s.correctRate !== null ? `${s.correctRate}%` : '데이터 없음'}
                </span>
              </p>
              <p className="text-gray-400">{relativeTime(s.lastSeen)}</p>
            </div>
          </button>
        )
      })}
    </div>
  )
}
