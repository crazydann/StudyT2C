'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { formatKoreanDate } from '@/lib/utils'

interface Student {
  id: string
  handle: string
  status: string
}

interface StudentSummary {
  student: Student
  recentSubmissions: { id: string; created_at: string }[]
  weakConcepts: string[]
  homeworkRate: number
  chatCount: number
  correctRate: number
}

interface HomeworkItem {
  id: string
  title: string
  description: string
  created_at: string
  submission: { id: string } | null
  non_submit_reason: { reason_code: string } | null
}

interface StudentData {
  summary: StudentSummary | null
  homework: HomeworkItem[]
  loadedAt: Date
}

export default function ParentPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; handle: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [students, setStudents] = useState<Student[]>([])
  const [studentData, setStudentData] = useState<Record<string, StudentData>>({})

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth/me')
        if (!res.ok) { router.push('/login'); return }
        const data = await res.json()
        if (data.user?.role !== 'parent') { router.push('/login'); return }
        setUser(data.user)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    checkAuth()
  }, [router])

  useEffect(() => {
    if (!user) return
    fetch('/api/students')
      .then((r) => r.json())
      .then((d) => { if (d.ok) setStudents(d.students) })
      .catch(() => {})
  }, [user])

  const loadStudentData = useCallback(async (studentId: string) => {
    try {
      const [summaryRes, hwRes] = await Promise.all([
        fetch(`/api/student/${studentId}/summary`),
        fetch(`/api/homework?studentId=${studentId}`),
      ])

      const [summaryData, hwData] = await Promise.all([
        summaryRes.json(),
        hwRes.json(),
      ])

      setStudentData((prev) => ({
        ...prev,
        [studentId]: {
          summary: summaryData.ok ? summaryData.summary : null,
          homework: hwData.ok ? hwData.homework : [],
          loadedAt: new Date(),
        },
      }))
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    students.forEach((s) => {
      if (!studentData[s.id]) {
        loadStudentData(s.id)
      }
    })
  }, [students, studentData, loadStudentData])

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/login')
  }

  function getHomeworkSummary(homework: HomeworkItem[]) {
    const total = homework.length
    const submitted = homework.filter((h) => h.submission).length
    const rate = total > 0 ? Math.round((submitted / total) * 100) : 0
    return { total, submitted, rate }
  }

  function getWeeklyStory(data: StudentData | undefined, student: Student): string {
    if (!data?.summary) return '데이터를 불러오는 중입니다...'

    const { correctRate, homeworkRate, chatCount, weakConcepts } = data.summary
    const parts: string[] = []

    if (chatCount > 5) {
      parts.push(`이번 주에 AI 튜터에 ${chatCount}번 질문하며 적극적으로 공부했습니다.`)
    } else if (chatCount > 0) {
      parts.push(`이번 주에 AI 튜터를 ${chatCount}번 활용했습니다.`)
    }

    if (correctRate > 0) {
      if (correctRate >= 80) {
        parts.push(`채점 결과 평균 ${correctRate}%의 높은 정답률을 보이고 있습니다.`)
      } else if (correctRate >= 60) {
        parts.push(`채점 결과 평균 ${correctRate}%의 정답률을 보이고 있습니다. 조금 더 노력이 필요합니다.`)
      } else {
        parts.push(`채점 결과 평균 ${correctRate}%의 정답률로, 추가 학습 지원이 필요합니다.`)
      }
    }

    if (homeworkRate >= 90) {
      parts.push(`숙제 제출률이 ${homeworkRate}%로 매우 성실합니다.`)
    } else if (homeworkRate >= 70) {
      parts.push(`숙제 제출률은 ${homeworkRate}%입니다.`)
    } else if (homeworkRate > 0) {
      parts.push(`숙제 제출률이 ${homeworkRate}%로 조금 더 노력이 필요합니다.`)
    }

    if (weakConcepts.length > 0) {
      parts.push(`${weakConcepts.slice(0, 2).join(', ')} 개념에서 어려움을 보이고 있습니다.`)
    }

    return parts.length > 0
      ? parts.join(' ')
      : `${student.handle} 학생의 학습 데이터가 아직 충분하지 않습니다.`
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-10 w-10 border-4 border-primary-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">T2C</span>
            </div>
            <div>
              <span className="font-semibold text-gray-900">StudyT2C</span>
              <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">학부모</span>
              <span className="ml-2 text-sm text-gray-500">{user?.handle}</span>
            </div>
          </div>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">
            로그아웃
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">우리 아이 학습 현황</h1>
          <p className="text-gray-500 text-sm mt-1">자녀의 학습 진도와 성취도를 확인하세요.</p>
        </div>

        {students.length === 0 ? (
          <div className="card text-center py-16">
            <div className="text-5xl mb-4">👨‍👧</div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">연결된 자녀가 없습니다</h3>
            <p className="text-sm text-gray-400">담당 선생님께 연결 요청을 해주세요.</p>
          </div>
        ) : (
          students.map((student) => {
            const data = studentData[student.id]
            const hw = getHomeworkSummary(data?.homework || [])

            return (
              <div key={student.id} className="space-y-4">
                {/* Student header */}
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-700 font-bold text-lg">
                    {student.handle[0].toUpperCase()}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{student.handle}</h2>
                    <p className="text-sm text-gray-400">학생</p>
                  </div>
                </div>

                {/* Weekly Story Card */}
                <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl p-6 text-white">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xl">📖</span>
                    <span className="font-semibold">이번 주 학습 이야기</span>
                  </div>
                  <p className="text-primary-100 leading-relaxed">
                    {getWeeklyStory(data, student)}
                  </p>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="card text-center">
                    {data?.summary ? (
                      <>
                        <div className={`text-3xl font-bold mb-1 ${
                          data.summary.correctRate >= 70 ? 'text-green-600' :
                          data.summary.correctRate >= 50 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {data.summary.correctRate}%
                        </div>
                        <div className="text-xs text-gray-500">평균 정답률</div>
                        <div className="mt-2">
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                data.summary.correctRate >= 70 ? 'bg-green-500' :
                                data.summary.correctRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${data.summary.correctRate}%` }}
                            />
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="animate-pulse">
                        <div className="h-8 bg-gray-200 rounded mx-auto w-16 mb-1" />
                        <div className="h-3 bg-gray-100 rounded w-20 mx-auto" />
                      </div>
                    )}
                  </div>

                  <div className="card text-center">
                    <div className={`text-3xl font-bold mb-1 ${
                      hw.rate >= 80 ? 'text-green-600' : hw.rate >= 50 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {hw.total > 0 ? `${hw.rate}%` : '-'}
                    </div>
                    <div className="text-xs text-gray-500">숙제 제출률</div>
                    {hw.total > 0 && (
                      <div className="mt-2">
                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              hw.rate >= 80 ? 'bg-green-500' : hw.rate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${hw.rate}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{hw.submitted}/{hw.total}개</p>
                      </div>
                    )}
                  </div>

                  <div className="card text-center">
                    {data?.summary ? (
                      <>
                        <div className="text-3xl font-bold text-purple-600 mb-1">
                          {data.summary.chatCount}
                        </div>
                        <div className="text-xs text-gray-500">주간 AI 질문</div>
                        <div className="mt-2 text-xs text-gray-400">
                          {data.summary.chatCount >= 5 ? '적극적 학습!' : '더 활용해보세요'}
                        </div>
                      </>
                    ) : (
                      <div className="animate-pulse">
                        <div className="h-8 bg-gray-200 rounded mx-auto w-16 mb-1" />
                        <div className="h-3 bg-gray-100 rounded w-20 mx-auto" />
                      </div>
                    )}
                  </div>
                </div>

                {/* Weak Concepts */}
                {data?.summary && data.summary.weakConcepts.length > 0 && (
                  <div className="card">
                    <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <span>⚠️</span> 취약 개념
                    </h3>
                    <p className="text-sm text-gray-500 mb-3">
                      최근 30일 오답에서 반복 등장하는 개념입니다. 추가 학습을 권장합니다.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {data.summary.weakConcepts.map((concept, i) => (
                        <div
                          key={concept}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
                            i === 0 ? 'bg-red-100 text-red-700' :
                            i === 1 ? 'bg-orange-100 text-orange-700' :
                            'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          <span className="font-bold text-xs">{i + 1}</span>
                          <span>{concept}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Homework */}
                {data?.homework && data.homework.length > 0 && (
                  <div className="card">
                    <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <span>📚</span> 최근 숙제 현황
                    </h3>
                    <div className="space-y-2">
                      {data.homework.slice(0, 5).map((hw) => (
                        <div key={hw.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                          <div>
                            <p className="text-sm font-medium text-gray-800">{hw.title}</p>
                            <p className="text-xs text-gray-400">{formatKoreanDate(hw.created_at)}</p>
                          </div>
                          <div>
                            {hw.submission ? (
                              <span className="badge-correct">제출 완료</span>
                            ) : hw.non_submit_reason ? (
                              <span className="badge-wrong">미제출 (사유 있음)</span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                                미제출
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {students.length > 1 && <hr className="border-gray-200" />}
              </div>
            )
          })
        )}
      </main>
    </div>
  )
}
