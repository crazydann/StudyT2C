'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { formatKoreanDate, formatKoreanDateTime } from '@/lib/utils'

interface Student {
  id: string
  handle: string
  status: string
}

interface ChartPoint {
  label: string
  gradingCount: number
  chatCount: number
  wrongRate: number | null
  submissionRate: number | null
}

interface Report {
  avgScore: number
  totalQuestions: number
  avgCorrectRate: number
  chatCount7d: number
  submissionRate: number
  streakDays: number
  wrongReasons: { code: string; label: string; count: number }[]
  subjectAchievement: { code: string; label: string; score: number; correctRate: number; questionCount: number }[]
  offTopicTotal: number
  offTopicByCategory: Record<string, number>
  offTopicItems: { created_at: string; content: string; category: string }[]
  studyChatHistory: { created_at: string; question: string; answer: string; subject: string }[]
  weeklyChart: ChartPoint[]
  monthlyChart: ChartPoint[]
  storyCard: { improved: string; stillWeak: string; nextPlan: string; tips: string[] }
  trendSentence: string
  recommendation: string
  weakConcepts: { name: string; count: number }[]
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
  report: Report | null
  homework: HomeworkItem[]
  loadedAt: Date
}

export default function ParentPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; handle: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [students, setStudents] = useState<Student[]>([])
  const [studentData, setStudentData] = useState<Record<string, StudentData>>({})
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, Record<string, boolean>>>({})
  const [reportPeriod, setReportPeriod] = useState<Record<string, 'week' | 'month'>>({})

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
      const [reportRes, hwRes] = await Promise.all([
        fetch(`/api/student/${studentId}/report`),
        fetch(`/api/homework?studentId=${studentId}`),
      ])
      const [reportData, hwData] = await Promise.all([reportRes.json(), hwRes.json()])
      setStudentData((prev) => ({
        ...prev,
        [studentId]: {
          report: reportData.ok ? reportData.report : null,
          homework: hwData.ok ? hwData.homework : [],
          loadedAt: new Date(),
        },
      }))
    } catch {}
  }, [])

  useEffect(() => {
    students.forEach((s) => {
      if (!studentData[s.id]) loadStudentData(s.id)
    })
  }, [students, studentData, loadStudentData])

  function toggleSection(studentId: string, section: string) {
    setExpandedSections((prev) => ({
      ...prev,
      [studentId]: { ...(prev[studentId] || {}), [section]: !prev[studentId]?.[section] },
    }))
  }

  function getPeriod(studentId: string): 'week' | 'month' {
    return reportPeriod[studentId] || 'week'
  }

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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-10 w-10 border-4 border-primary-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">로그아웃</button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">우리 아이 학습 현황</h1>
          <p className="text-gray-500 text-sm mt-1">자녀의 학습 성향·평가·시간에 따른 성취도 추이를 확인하세요.</p>
        </div>

        {students.length === 0 ? (
          <div className="card text-center py-16">
            <div className="text-5xl mb-4">👨‍👧</div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">연결된 자녀가 없습니다</h3>
            <p className="text-sm text-gray-400">담당 선생님께 연결 요청을 해주세요.</p>
          </div>
        ) : (
          <>
            {/* Mobile: child tab selector (shown only on mobile when multiple children) */}
            {students.length > 1 && (
              <div className="md:hidden flex gap-2">
                {students.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setSelectedStudentId(s.id)}
                    className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                      (selectedStudentId ?? students[0]?.id) === s.id
                        ? 'bg-primary-600 text-white shadow-sm'
                        : 'bg-white border border-gray-200 text-gray-600'
                    }`}
                  >
                    <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold">
                      {s.handle[0].toUpperCase()}
                    </span>
                    {s.handle}
                  </button>
                ))}
              </div>
            )}

          {students.map((student) => {
            const data = studentData[student.id]
            const report = data?.report
            const hw = getHomeworkSummary(data?.homework || [])
            const period = getPeriod(student.id)
            const chartData = period === 'week' ? report?.weeklyChart : report?.monthlyChart
            const sections = expandedSections[student.id] || {}
            // On mobile with multiple children: hide non-selected children
            const isSelected = (selectedStudentId ?? students[0]?.id) === student.id
            const mobileVisibility = students.length > 1 ? (isSelected ? 'block' : 'hidden md:block') : ''

            return (
              <div key={student.id} className={`space-y-4 ${mobileVisibility}`}>
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

                {/* Story card */}
                {report ? (
                  <div className="rounded-2xl p-5 text-white" style={{ background: 'linear-gradient(135deg, #16a34a, #15803d)' }}>
                    <p className="text-xs font-bold uppercase tracking-wide mb-3 text-green-200">
                      이번 주 {student.handle} 학습 요약
                    </p>
                    {report.storyCard.improved && (
                      <p className="text-sm mb-1">📈 {report.storyCard.improved}</p>
                    )}
                    {report.storyCard.stillWeak && (
                      <p className="text-sm mb-1 text-yellow-200">⚠️ {report.storyCard.stillWeak}</p>
                    )}
                    {report.storyCard.nextPlan && (
                      <p className="text-sm text-blue-200">📌 {report.storyCard.nextPlan}</p>
                    )}
                  </div>
                ) : (
                  <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl p-5 text-white">
                    <div className="animate-pulse">
                      <div className="h-4 bg-white/30 rounded w-3/4 mb-2" />
                      <div className="h-3 bg-white/20 rounded w-full mb-1" />
                      <div className="h-3 bg-white/20 rounded w-5/6" />
                    </div>
                  </div>
                )}

                {/* Trend sentence */}
                {report?.trendSentence && (
                  <div className="card bg-gray-50">
                    <p className="text-sm text-gray-700">💡 {report.trendSentence}</p>
                  </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="card text-center">
                    {report ? (
                      <>
                        <div className={`text-3xl font-bold mb-1 ${report.avgCorrectRate >= 70 ? 'text-green-600' : report.avgCorrectRate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {report.avgCorrectRate}%
                        </div>
                        <div className="text-xs text-gray-500">평균 정답률</div>
                        <div className="mt-2">
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${report.avgCorrectRate >= 70 ? 'bg-green-500' : report.avgCorrectRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                              style={{ width: `${report.avgCorrectRate}%` }}
                            />
                          </div>
                        </div>
                      </>
                    ) : <LoadingSkeleton />}
                  </div>

                  <div className="card text-center">
                    <div className={`text-3xl font-bold mb-1 ${hw.rate >= 80 ? 'text-green-600' : hw.rate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {hw.total > 0 ? `${hw.rate}%` : '-'}
                    </div>
                    <div className="text-xs text-gray-500">숙제 제출률</div>
                    {hw.total > 0 && (
                      <div className="mt-2">
                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${hw.rate >= 80 ? 'bg-green-500' : hw.rate >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${hw.rate}%` }} />
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{hw.submitted}/{hw.total}개</p>
                      </div>
                    )}
                  </div>

                  <div className="card text-center">
                    {report ? (
                      <>
                        <div className="text-3xl font-bold text-purple-600 mb-1">{report.totalQuestions}</div>
                        <div className="text-xs text-gray-500">30일 AI 질문</div>
                        <div className="mt-2 text-xs text-gray-400">
                          {report.totalQuestions >= 20 ? '적극적 학습!' : '더 활용해보세요'}
                        </div>
                      </>
                    ) : <LoadingSkeleton />}
                  </div>
                </div>

                {/* Wrong reason breakdown */}
                {report && report.wrongReasons.length > 0 && (
                  <div className="card">
                    <h3 className="font-semibold text-gray-800 mb-3">오답 유형 분석 (최근 30일)</h3>
                    <div className="flex flex-wrap gap-2">
                      {report.wrongReasons.map((r) => (
                        <span key={r.code} className="bg-orange-50 text-orange-700 border border-orange-200 px-3 py-1 rounded-full text-sm">
                          {r.label} <span className="font-semibold">{r.count}건</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Weekly/monthly report */}
                {report && (
                  <div className="card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-800">주간/월간 리포트</h3>
                      <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                        {(['week', 'month'] as const).map((p) => (
                          <button
                            key={p}
                            onClick={() => setReportPeriod((prev) => ({ ...prev, [student.id]: p }))}
                            className={`px-3 py-1 text-sm rounded-md transition-colors ${
                              period === p ? 'bg-white shadow text-gray-900 font-medium' : 'text-gray-500'
                            }`}
                          >
                            {p === 'week' ? '주간' : '월간'}
                          </button>
                        ))}
                      </div>
                    </div>
                    {chartData && chartData.length > 0 && (
                      <>
                        <div className="grid grid-cols-4 gap-2 mb-4">
                          {[
                            { label: '채점 횟수', value: chartData[chartData.length - 1]?.gradingCount ?? 0, unit: '회' },
                            { label: '튜터 질문', value: chartData[chartData.length - 1]?.chatCount ?? 0, unit: '건' },
                            {
                              label: '오답률',
                              value: chartData[chartData.length - 1]?.wrongRate != null
                                ? Math.round((chartData[chartData.length - 1].wrongRate as number) * 100) : null,
                              unit: '%',
                            },
                            { label: '연속 학습', value: report.streakDays, unit: '일' },
                          ].map((m) => (
                            <div key={m.label} className="text-center bg-gray-50 rounded-lg p-3">
                              <div className="text-xl font-bold text-gray-800">
                                {m.value != null ? `${m.value}${m.unit}` : 'N/A'}
                              </div>
                              <div className="text-xs text-gray-500 mt-0.5">{m.label}</div>
                            </div>
                          ))}
                        </div>
                        <SimpleBarChart data={chartData} />
                      </>
                    )}
                  </div>
                )}

                {/* Subject achievement */}
                {report && (
                  <div className="card">
                    <h3 className="font-semibold text-gray-800 mb-4">과목별 성취도</h3>
                    <div className="space-y-3">
                      {report.subjectAchievement.map((s) => (
                        <div key={s.code}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-gray-700">{s.label}</span>
                            <span className="text-sm text-gray-500">질문 {s.questionCount}건 · {s.score}점</span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary-500 rounded-full"
                              style={{ width: `${Math.min(100, s.score * 5)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Weak concepts */}
                {report && report.weakConcepts.length > 0 && (
                  <div className="card">
                    <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <span>⚠️</span> 취약 개념
                    </h3>
                    <p className="text-sm text-gray-500 mb-3">최근 30일 오답에서 반복 등장하는 개념입니다.</p>
                    <div className="flex flex-wrap gap-2">
                      {report.weakConcepts.map((concept, i) => (
                        <div key={concept.name} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
                          i === 0 ? 'bg-red-100 text-red-700' : i === 1 ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          <span className="font-bold text-xs">{i + 1}</span>
                          <span>{concept.name}</span>
                          <span className="text-xs opacity-70">({concept.count}회)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tips */}
                {report && report.storyCard.tips && report.storyCard.tips.length > 0 && (
                  <div className="card border border-green-200 bg-green-50">
                    <button
                      onClick={() => toggleSection(student.id, 'tips')}
                      className="w-full flex items-center justify-between"
                    >
                      <span className="font-semibold text-green-800 text-sm">💬 상담 때 이렇게 물어보세요</span>
                      <span className="text-green-600 text-sm">{sections.tips ? '▲' : '▼'}</span>
                    </button>
                    {sections.tips && (
                      <div className="mt-3 space-y-2">
                        {report.storyCard.tips.map((tip, i) => (
                          <p key={i} className="text-sm text-green-700">• {tip}</p>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Study chat history */}
                {report && (
                  <div className="card">
                    <button
                      onClick={() => toggleSection(student.id, 'studyChat')}
                      className="w-full flex items-center justify-between"
                    >
                      <span className="font-semibold text-gray-800">
                        질문 이력 (최근 30일) — {report.studyChatHistory.length}건
                      </span>
                      <span className="text-gray-400 text-sm">{sections.studyChat ? '▲ 닫기' : '▼ 열기'}</span>
                    </button>
                    {sections.studyChat && (
                      <div className="mt-4 max-h-72 overflow-y-auto space-y-3">
                        {report.studyChatHistory.length === 0 ? (
                          <p className="text-sm text-gray-400">공부 관련 질문 이력이 없습니다.</p>
                        ) : (
                          report.studyChatHistory.map((item, idx) => (
                            <div key={idx} className="border-b border-gray-100 pb-3 last:border-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs text-gray-400">{formatKoreanDateTime(item.created_at)}</span>
                                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{item.subject}</span>
                              </div>
                              <p className="text-sm text-gray-700"><span className="font-medium">Q: </span>{item.question}</p>
                              {item.answer && (
                                <p className="text-sm text-gray-500 mt-0.5"><span className="font-medium">A: </span>{item.answer.slice(0, 150)}{item.answer.length > 150 ? '...' : ''}</p>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Off-topic chat */}
                {report && (
                  <div className="card">
                    <button
                      onClick={() => toggleSection(student.id, 'offTopic')}
                      className="w-full flex items-center justify-between"
                    >
                      <span className="font-semibold text-gray-800">
                        공부 외 질문 (최근 7일)
                        {report.offTopicTotal >= 10 ? ' 🔴' : report.offTopicTotal >= 5 ? ' 🟠' : ''} — {report.offTopicTotal}건
                      </span>
                      <span className="text-gray-400 text-sm">{sections.offTopic ? '▲ 닫기' : '▼ 열기'}</span>
                    </button>
                    {sections.offTopic && (
                      <div className="mt-4">
                        {report.offTopicTotal === 0 ? (
                          <p className="text-sm text-gray-400">공부 시간 중 공부 외 질문 없이 잘 활용하고 있어요.</p>
                        ) : (
                          <>
                            {Object.entries(report.offTopicByCategory).length > 0 && (
                              <p className="text-xs text-gray-500 mb-3">
                                유형: {Object.entries(report.offTopicByCategory).map(([k, v]) => `${k} ${v}건`).join(', ')}
                              </p>
                            )}
                            <div className="max-h-60 overflow-y-auto space-y-2">
                              {report.offTopicItems.map((item, idx) => (
                                <div key={idx} className="border-b border-gray-100 pb-2 last:border-0">
                                  <div className="flex items-center gap-2 mb-0.5">
                                    <span className="text-xs text-gray-400">{formatKoreanDateTime(item.created_at)}</span>
                                    <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">{item.category}</span>
                                  </div>
                                  <p className="text-sm text-gray-700">{item.content}</p>
                                </div>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Recent homework */}
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
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">미제출</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {students.length > 1 && <hr className="border-gray-200 hidden md:block" />}
              </div>
            )
          })}
          </>
        )}
      </main>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded mx-auto w-16 mb-1" />
      <div className="h-3 bg-gray-100 rounded w-20 mx-auto" />
    </div>
  )
}

function SimpleBarChart({ data }: { data: ChartPoint[] }) {
  const maxVal = Math.max(...data.map((d) => Math.max(d.gradingCount, d.chatCount)), 1)
  return (
    <div className="mt-2">
      <div className="flex gap-4 text-xs text-gray-500 mb-2">
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-primary-500 rounded inline-block" />채점 수</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-purple-400 rounded inline-block" />질문 수</span>
      </div>
      <div className="flex items-end gap-2 h-24">
        {data.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
            <div className="flex items-end gap-0.5 h-16 w-full justify-center">
              <div
                className="bg-primary-500 rounded-t w-2/5"
                style={{ height: `${(d.gradingCount / maxVal) * 100}%`, minHeight: d.gradingCount > 0 ? '2px' : '0' }}
              />
              <div
                className="bg-purple-400 rounded-t w-2/5"
                style={{ height: `${(d.chatCount / maxVal) * 100}%`, minHeight: d.chatCount > 0 ? '2px' : '0' }}
              />
            </div>
            <span className="text-xs text-gray-400 text-center" style={{ fontSize: '10px' }}>
              {d.label.slice(0, 5)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
