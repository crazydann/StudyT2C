'use client'

interface Props {
  streak: number
  correctRate: number
  totalProblems: number
}

interface LevelInfo {
  emoji: string
  name: string
  min: number
  max: number | null
}

const LEVELS: LevelInfo[] = [
  { emoji: '🌱', name: '새싹', min: 0, max: 9 },
  { emoji: '📚', name: '학습자', min: 10, max: 49 },
  { emoji: '⭐', name: '우등생', min: 50, max: 99 },
  { emoji: '🏆', name: '우수자', min: 100, max: 199 },
  { emoji: '👑', name: '최우수자', min: 200, max: null },
]

function getLevel(totalProblems: number): LevelInfo & { progress: number; nextLevelProblems: number | null } {
  const level = LEVELS.find((l) => totalProblems >= l.min && (l.max === null || totalProblems <= l.max)) ?? LEVELS[0]
  const nextLevel = LEVELS[LEVELS.indexOf(level) + 1] ?? null
  const progress = nextLevel
    ? Math.min(100, Math.round(((totalProblems - level.min) / (nextLevel.min - level.min)) * 100))
    : 100
  return { ...level, progress, nextLevelProblems: nextLevel ? nextLevel.min : null }
}

function getMotivationalMessage(correctRate: number): string {
  if (correctRate >= 80) return '훌륭해요! 최상위권이에요 🎉'
  if (correctRate >= 60) return '잘 하고 있어요! 조금만 더 💪'
  if (correctRate >= 40) return '꾸준히 하면 돼요! 화이팅 😊'
  return '걱정 마세요, 함께 해봐요 🤗'
}

export default function StreakBadge({ streak, correctRate, totalProblems }: Props) {
  const level = getLevel(totalProblems)
  const motivationalMessage = getMotivationalMessage(correctRate)

  return (
    <div className="space-y-2">
      {/* Streak Card */}
      <div className={`rounded-2xl shadow-md p-3 text-white relative overflow-hidden ${streak > 0 ? 'bg-gradient-to-r from-orange-400 to-red-500' : 'bg-gradient-to-r from-gray-400 to-gray-500'}`}>
        <div className="relative z-10">
          {streak > 0 ? (
            <div className="flex items-center gap-2">
              <span className="text-2xl">🔥</span>
              <div>
                <p className="text-xs font-medium text-orange-100">연속 학습</p>
                <p className="text-lg font-bold leading-tight">{streak}일 연속 학습 중!</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xl">✨</span>
              <p className="text-sm font-semibold">오늘 학습을 시작해보세요!</p>
            </div>
          )}
        </div>
        {/* Shimmer overlay */}
        <div className="absolute inset-0 animate-shimmer pointer-events-none" />
      </div>

      {/* Level Badge */}
      <div className="bg-white rounded-2xl shadow-md border border-gray-100 p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xl">{level.emoji}</span>
            <div>
              <p className="text-xs text-gray-500 leading-none">레벨</p>
              <p className="text-sm font-bold text-gray-800">{level.name}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">총 문제</p>
            <p className="text-sm font-bold text-indigo-600 animate-count-up">{totalProblems}개</p>
          </div>
        </div>

        {/* Progress bar to next level */}
        {level.nextLevelProblems !== null ? (
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>{totalProblems}문제</span>
              <span>다음 레벨: {level.nextLevelProblems}문제</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700"
                style={{ width: `${level.progress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="h-1.5 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full" />
        )}

        {/* Motivational message */}
        {totalProblems > 0 && (
          <p className="text-xs text-gray-500 mt-2 text-center font-medium">{motivationalMessage}</p>
        )}
      </div>
    </div>
  )
}
