'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { formatKoreanDate, formatKoreanDateTime } from '@/lib/utils'

interface Student {
  id: string
  handle: string
  status: string
}

interface ProblemItem {
  id: string
  item_no: number
  is_correct: boolean
  key_concepts: string[]
  explanation_summary: string
  reason_category: string
}

interface Submission {
  id: string
  created_at: string
  items: ProblemItem[]
  stats: { total: number; correct: number; wrong: number; rate: number }
}

interface HomeworkItem {
  id: string
  title: string
  description: string
  created_at: string
  submission: { id: string; created_at: string } | null
  non_submit_reason: { reason_code: string } | null
}

interface Summary {
  student: Student
  recentSubmissions: { id: string; created_at: string }[]
  weakConcepts: string[]
  homeworkRate: number
  chatCount: number
  correctRate: number
  focusStats?: { leftTabCount: number; firstUse: string | null; lastUse: string | null; todayEventCount: number }
  currentMode?: string
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

type Panel = 'briefing' | 'report' | 'notes' | 'grading' | 'homework'

export default function TeacherPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; handle: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [students, setStudents] = useState<Student[]>([])
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null)
  const [activePanel, setActivePanel] = useState<Panel>('briefing')

  // Per-student data
  const [summary, setSummary] = useState<Summary | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [report, setReport] = useState<Report | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportPeriod, setReportPeriod] = useState<'week' | 'month'>('week')
  const [showStudyChat, setShowStudyChat] = useState(false)
  const [showOffTopic, setShowOffTopic] = useState(false)
  const [note, setNote] = useState('')
  const [noteSaved, setNoteSaved] = useState(false)
  const [noteSaving, setNoteSaving] = useState(false)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [gradingLoading, setGradingLoading] = useState(false)
  const [homework, setHomework] = useState<HomeworkItem[]>([])
  const [hwLoading, setHwLoading] = useState(false)

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth/me')
        if (!res.ok) { router.push('/login'); return }
        const data = await res.json()
        if (data.user?.role !== 'teacher') { router.push('/login'); return }
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

  const loadSummary = useCallback(async (studentId: string) => {
    setSummaryLoading(true)
    try {
      const res = await fetch(`/api/student/${studentId}/summary`)
      const data = await res.json()
      if (data.ok) setSummary(data.summary)
    } catch {}
    finally { setSummaryLoading(false) }
  }, [])

  const loadReport = useCallback(async (studentId: string) => {
    setReportLoading(true)
    try {
      const res = await fetch(`/api/student/${studentId}/report`)
      const data = await res.json()
      if (data.ok) setReport(data.report)
    } catch {}
    finally { setReportLoading(false) }
  }, [])

  const loadNote = useCallback(async (studentId: string) => {
    try {
      const res = await fetch(`/api/student/${studentId}/notes`)
      const data = await res.json()
      if (data.ok) setNote(data.note?.note || '')
    } catch {}
  }, [])

  const loadGrading = useCallback(async (studentId: string) => {
    setGradingLoading(true)
    try {
      const res = await fetch(`/api/student/${studentId}/grading`)
      const data = await res.json()
      if (data.ok) setSubmissions(data.submissions)
    } catch {}
    finally { setGradingLoading(false) }
  }, [])

  const loadHomework = useCallback(async (studentId: string) => {
    setHwLoading(true)
    try {
      const res = await fetch(`/api/homework?studentId=${studentId}`)
      const data = await res.json()
      if (data.ok) setHomework(data.homework)
    } catch {}
    finally { setHwLoading(false) }
  }, [])

  useEffect(() => {
    if (!selectedStudent) return
    setSummary(null)
    setReport(null)
    setNote('')
    setSubmissions([])
    setHomework([])
    setActivePanel('briefing')
    setShowStudyChat(false)
    setShowOffTopic(false)
    loadSummary(selectedStudent.id)
    loadNote(selectedStudent.id)
  }, [selectedStudent, loadSummary, loadNote])

  useEffect(() => {
    if (!selectedStudent) return
    if (activePanel === 'grading') loadGrading(selectedStudent.id)
    if (activePanel === 'homework') loadHomework(selectedStudent.id)
    if (activePanel === 'report' && !report) loadReport(selectedStudent.id)
  }, [activePanel, selectedStudent, loadGrading, loadHomework, loadReport, report])

  async function saveNote() {
    if (!selectedStudent) return
    setNoteSaving(true)
    try {
      await fetch(`/api/student/${selectedStudent.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      })
      setNoteSaved(true)
      setTimeout(() => setNoteSaved(false), 2000)
    } catch {}
    finally { setNoteSaving(false) }
  }

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin h-10 w-10 border-4 border-primary-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  const panels: { key: Panel; label: string }[] = [
    { key: 'briefing', label: '수업 전 브리핑' },
    { key: 'report', label: 'AI 리포트' },
    { key: 'notes', label: '상담 노트' },
    { key: 'grading', label: '채점 이력' },
    { key: 'homework', label: '숙제 현황' },
  ]

  const chartData = reportPeriod === 'week' ? report?.weeklyChart : report?.monthlyChart

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">T2C</span>
            </div>
            <div>
              <span className="font-semibold text-gray-900">StudyT2C</span>
              <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">선생님</span>
              <span className="ml-2 text-sm text-gray-500">{user?.handle}</span>
            </div>
          </div>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">로그아웃</button>
        </div>
      </header>

      <div className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 flex gap-6">
        {/* Sidebar */}
        <aside className="w-56 flex-shrink-0">
          <div className="card p-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              담당 학생 ({students.length}명)
            </h2>
            {students.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">연결된 학생이 없습니다.</p>
            ) : (
              <div className="space-y-1">
                {students.map((student) => (
                  <button
                    key={student.id}
                    onClick={() => setSelectedStudent(student)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                      selectedStudent?.id === student.id
                        ? 'bg-primary-50 text-primary-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-xs font-semibold text-gray-600">
                        {student.handle[0].toUpperCase()}
                      </div>
                      <span className="text-sm">{student.handle}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 min-w-0">
          {!selectedStudent ? (
            <div className="card text-center py-16">
              <div className="text-5xl mb-4">👈</div>
              <h3 className="text-lg font-semibold text-gray-700 mb-2">학생을 선택해주세요</h3>
              <p className="text-sm text-gray-400">왼쪽 목록에서 학생을 선택하면 상세 정보를 볼 수 있습니다.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Student header */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-bold text-lg">
                  {selectedStudent.handle[0].toUpperCase()}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{selectedStudent.handle}</h2>
                  <p className="text-sm text-gray-500">학생 상세 정보</p>
                </div>
              </div>

              {/* Panel tabs */}
              <div className="flex gap-1 bg-white border border-gray-200 rounded-xl p-1 flex-wrap">
                {panels.map((p) => (
                  <button
                    key={p.key}
                    onClick={() => setActivePanel(p.key)}
                    className={`flex-1 py-2 text-sm rounded-lg transition-colors font-medium min-w-[80px] ${
                      activePanel === p.key
                        ? 'bg-primary-600 text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* ── Briefing Panel ── */}
              {activePanel === 'briefing' && (
                <div className="space-y-4">
                  {summaryLoading ? (
                    <div className="card text-center py-8">
                      <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
                    </div>
                  ) : summary ? (
                    <>
                      <div className="grid grid-cols-3 gap-4">
                        <div className="card text-center">
                          <div className="text-3xl font-bold text-primary-600 mb-1">{summary.correctRate}%</div>
                          <div className="text-xs text-gray-500">평균 정답률</div>
                        </div>
                        <div className="card text-center">
                          <div className="text-3xl font-bold text-green-600 mb-1">{summary.homeworkRate}%</div>
                          <div className="text-xs text-gray-500">숙제 제출률</div>
                        </div>
                        <div className="card text-center">
                          <div className="text-3xl font-bold text-purple-600 mb-1">{summary.chatCount}</div>
                          <div className="text-xs text-gray-500">주간 질문 수</div>
                        </div>
                      </div>

                      {/* Focus stats */}
                      <div className="card">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="font-semibold text-gray-800">오늘 집중 현황</h3>
                          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${summary.currentMode === 'studying' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                            {summary.currentMode === 'studying' ? '공부 모드' : '휴식 모드'}
                          </span>
                        </div>
                        {summary.focusStats ? (
                          <div className="grid grid-cols-3 gap-3">
                            <div className="text-center">
                              <div className={`text-2xl font-bold ${summary.focusStats.leftTabCount >= 5 ? 'text-red-500' : summary.focusStats.leftTabCount >= 2 ? 'text-orange-500' : 'text-gray-700'}`}>
                                {summary.focusStats.leftTabCount}
                              </div>
                              <div className="text-xs text-gray-500 mt-0.5">탭 이탈 횟수</div>
                            </div>
                            <div className="text-center">
                              <div className="text-sm font-semibold text-gray-700">
                                {summary.focusStats.firstUse
                                  ? new Date(summary.focusStats.firstUse).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
                                  : '-'}
                              </div>
                              <div className="text-xs text-gray-500 mt-0.5">첫 접속</div>
                            </div>
                            <div className="text-center">
                              <div className="text-sm font-semibold text-gray-700">
                                {summary.focusStats.lastUse
                                  ? new Date(summary.focusStats.lastUse).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
                                  : '-'}
                              </div>
                              <div className="text-xs text-gray-500 mt-0.5">마지막 활동</div>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">오늘 접속 기록이 없습니다.</p>
                        )}
                      </div>
                      <div className="card">
                        <h3 className="font-semibold text-gray-800 mb-3">취약 개념 (최근 30일)</h3>
                        {summary.weakConcepts.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {summary.weakConcepts.map((concept, i) => (
                              <span key={concept} className={`px-3 py-1 rounded-full text-sm font-medium ${
                                i === 0 ? 'bg-red-100 text-red-700' : i === 1 ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'
                              }`}>{concept}</span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">취약 개념 데이터가 없습니다.</p>
                        )}
                      </div>
                      <div className="card">
                        <h3 className="font-semibold text-gray-800 mb-3">최근 채점 (30일 내)</h3>
                        {summary.recentSubmissions.length > 0 ? (
                          <div className="space-y-2">
                            {summary.recentSubmissions.slice(0, 5).map((sub) => (
                              <div key={sub.id} className="flex items-center justify-between text-sm">
                                <span className="text-gray-600">채점 세션</span>
                                <span className="text-gray-400">{formatKoreanDate(sub.created_at)}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">최근 채점 기록이 없습니다.</p>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="card text-center py-8">
                      <p className="text-gray-400">데이터를 불러오지 못했습니다.</p>
                    </div>
                  )}
                </div>
              )}

              {/* ── AI Report Panel ── */}
              {activePanel === 'report' && (
                <div className="space-y-4">
                  {reportLoading ? (
                    <div className="card text-center py-12">
                      <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-3" />
                      <p className="text-sm text-gray-500">AI 리포트 분석 중...</p>
                    </div>
                  ) : report ? (
                    <>
                      {/* Recommendation */}
                      <div className="card border-l-4 border-l-blue-500 bg-blue-50">
                        <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">다음 수업 맞춤 보강 포인트</p>
                        <p className="text-sm text-gray-800">{report.recommendation}</p>
                      </div>

                      {/* Key metrics */}
                      <div className="grid grid-cols-4 gap-3">
                        <div className="card text-center py-3">
                          <div className="text-2xl font-bold text-primary-600">{report.avgCorrectRate}%</div>
                          <div className="text-xs text-gray-500 mt-0.5">평균 정답률</div>
                        </div>
                        <div className="card text-center py-3">
                          <div className="text-2xl font-bold text-blue-600">{report.totalQuestions}</div>
                          <div className="text-xs text-gray-500 mt-0.5">30일 질문 수</div>
                        </div>
                        <div className="card text-center py-3">
                          <div className={`text-2xl font-bold ${report.offTopicTotal >= 10 ? 'text-red-600' : report.offTopicTotal >= 5 ? 'text-orange-500' : 'text-gray-700'}`}>
                            {report.offTopicTotal}
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            공부 외 질문(7일)
                            {report.offTopicTotal >= 10 ? ' 🔴' : report.offTopicTotal >= 5 ? ' 🟠' : ''}
                          </div>
                        </div>
                        <div className="card text-center py-3">
                          <div className="text-2xl font-bold text-green-600">{report.streakDays}일</div>
                          <div className="text-xs text-gray-500 mt-0.5">연속 학습</div>
                        </div>
                      </div>

                      {/* Wrong reason breakdown */}
                      {report.wrongReasons.length > 0 && (
                        <div className="card">
                          <h3 className="font-semibold text-gray-800 mb-3">오답 유형별 집계 (최근 30일)</h3>
                          <div className="flex flex-wrap gap-2">
                            {report.wrongReasons.map((r) => (
                              <span key={r.code} className="bg-orange-50 text-orange-700 border border-orange-200 px-3 py-1 rounded-full text-sm">
                                {r.label} <span className="font-semibold">{r.count}건</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Trend sentence */}
                      {report.trendSentence && (
                        <div className="card bg-gray-50">
                          <p className="text-sm text-gray-700"><span className="font-medium">학습 추이: </span>{report.trendSentence}</p>
                        </div>
                      )}

                      {/* Weekly/Monthly report */}
                      <div className="card">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="font-semibold text-gray-800">주간/월간 리포트</h3>
                          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                            {(['week', 'month'] as const).map((p) => (
                              <button
                                key={p}
                                onClick={() => setReportPeriod(p)}
                                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                                  reportPeriod === p ? 'bg-white shadow text-gray-900 font-medium' : 'text-gray-500 hover:text-gray-700'
                                }`}
                              >
                                {p === 'week' ? '주간' : '월간'}
                              </button>
                            ))}
                          </div>
                        </div>
                        {chartData && chartData.length > 0 && (
                          <>
                            <div className="grid grid-cols-4 gap-3 mb-4">
                              {[
                                { label: '채점 횟수', value: chartData[chartData.length - 1]?.gradingCount ?? 0, unit: '회' },
                                { label: '튜터 질문', value: chartData[chartData.length - 1]?.chatCount ?? 0, unit: '건' },
                                {
                                  label: '오답률',
                                  value: chartData[chartData.length - 1]?.wrongRate != null
                                    ? Math.round((chartData[chartData.length - 1].wrongRate as number) * 100)
                                    : null,
                                  unit: '%',
                                },
                                {
                                  label: '숙제 제출률',
                                  value: chartData[chartData.length - 1]?.submissionRate != null
                                    ? Math.round((chartData[chartData.length - 1].submissionRate as number) * 100)
                                    : null,
                                  unit: '%',
                                },
                              ].map((m) => (
                                <div key={m.label} className="text-center bg-gray-50 rounded-lg p-3">
                                  <div className="text-xl font-bold text-gray-800">
                                    {m.value != null ? `${m.value}${m.unit}` : 'N/A'}
                                  </div>
                                  <div className="text-xs text-gray-500 mt-0.5">{m.label}</div>
                                </div>
                              ))}
                            </div>
                            <p className="text-xs text-gray-500 mb-3">연속 학습 일수: {report.streakDays}일</p>
                            {/* Simple bar chart */}
                            <SimpleBarChart data={chartData} />
                          </>
                        )}
                      </div>

                      {/* Subject achievement */}
                      <div className="card">
                        <h3 className="font-semibold text-gray-800 mb-4">과목별 성취도 (질문 활동 기반)</h3>
                        <div className="space-y-3">
                          {report.subjectAchievement.map((s) => (
                            <div key={s.code}>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-gray-700">{s.label}</span>
                                <span className="text-sm text-gray-500">질문 {s.questionCount}건 · 성취도 {s.score}점</span>
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

                      {/* Study chat history */}
                      <div className="card">
                        <button
                          onClick={() => setShowStudyChat(!showStudyChat)}
                          className="w-full flex items-center justify-between text-left"
                        >
                          <span className="font-semibold text-gray-800">
                            질문 이력 (최근 30일) — {report.studyChatHistory.length}건
                          </span>
                          <span className="text-gray-400 text-sm">{showStudyChat ? '▲ 닫기' : '▼ 열기'}</span>
                        </button>
                        {showStudyChat && (
                          <div className="mt-4 max-h-80 overflow-y-auto space-y-3">
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
                                    <p className="text-sm text-gray-500 mt-1"><span className="font-medium">A: </span>{item.answer}</p>
                                  )}
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>

                      {/* Off-topic chat */}
                      <div className="card">
                        <button
                          onClick={() => setShowOffTopic(!showOffTopic)}
                          className="w-full flex items-center justify-between text-left"
                        >
                          <span className="font-semibold text-gray-800">
                            공부 외 질문 (최근 7일)
                            {report.offTopicTotal >= 10 ? ' 🔴' : report.offTopicTotal >= 5 ? ' 🟠' : ''} — {report.offTopicTotal}건
                          </span>
                          <span className="text-gray-400 text-sm">{showOffTopic ? '▲ 닫기' : '▼ 열기'}</span>
                        </button>
                        {showOffTopic && (
                          <div className="mt-4">
                            {report.offTopicTotal === 0 ? (
                              <p className="text-sm text-gray-400">공부 시간 중 공부 외 질문이 없었어요.</p>
                            ) : (
                              <>
                                {Object.entries(report.offTopicByCategory).length > 0 && (
                                  <p className="text-xs text-gray-500 mb-3">
                                    유형: {Object.entries(report.offTopicByCategory).map(([k, v]) => `${k} ${v}건`).join(', ')}
                                  </p>
                                )}
                                <div className="max-h-64 overflow-y-auto space-y-2">
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
                    </>
                  ) : (
                    <div className="card text-center py-8">
                      <p className="text-gray-400">리포트 데이터를 불러오지 못했습니다.</p>
                    </div>
                  )}
                </div>
              )}

              {/* ── Notes Panel ── */}
              {activePanel === 'notes' && (
                <div className="card">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-800">상담 노트</h3>
                    {noteSaved && <span className="text-xs text-green-600 font-medium">저장되었습니다!</span>}
                  </div>
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder={`${selectedStudent.handle} 학생에 대한 상담 노트를 작성하세요.`}
                    className="input-field h-64 resize-none mb-4"
                  />
                  <button onClick={saveNote} disabled={noteSaving} className="btn-primary">
                    {noteSaving ? '저장 중...' : '저장'}
                  </button>
                </div>
              )}

              {/* ── Grading History Panel ── */}
              {activePanel === 'grading' && (
                <div className="space-y-4">
                  {gradingLoading ? (
                    <div className="card text-center py-8">
                      <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
                    </div>
                  ) : submissions.length === 0 ? (
                    <div className="card text-center py-8">
                      <p className="text-gray-400">채점 기록이 없습니다.</p>
                    </div>
                  ) : (
                    submissions.map((sub) => (
                      <div key={sub.id} className="card">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <p className="font-medium text-gray-800">{formatKoreanDateTime(sub.created_at)}</p>
                            <p className="text-sm text-gray-500 mt-0.5">총 {sub.stats.total}문제 중 {sub.stats.correct}개 정답</p>
                          </div>
                          <div className="text-right">
                            <div className={`text-2xl font-bold ${sub.stats.rate >= 70 ? 'text-green-600' : sub.stats.rate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                              {sub.stats.rate}%
                            </div>
                            <div className="flex gap-2 text-xs mt-1">
                              <span className="badge-correct">{sub.stats.correct}정</span>
                              <span className="badge-wrong">{sub.stats.wrong}오</span>
                            </div>
                          </div>
                        </div>
                        {sub.items.filter((i) => !i.is_correct).length > 0 && (
                          <div className="border-t border-gray-100 pt-3 mt-3">
                            <p className="text-xs font-medium text-gray-500 mb-2">오답 문항</p>
                            <div className="space-y-2">
                              {sub.items.filter((i) => !i.is_correct).map((item) => (
                                <div key={item.id} className="text-sm bg-red-50 rounded-lg p-2">
                                  <div className="flex items-center gap-2 mb-0.5">
                                    <span className="font-medium text-red-700">{item.item_no}번</span>
                                    {item.reason_category && <span className="badge-blue text-xs">{item.reason_category}</span>}
                                  </div>
                                  <p className="text-gray-600 text-xs">{item.explanation_summary}</p>
                                  {item.key_concepts.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-1">
                                      {item.key_concepts.map((c) => (
                                        <span key={c} className="text-xs text-gray-500">#{c}</span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ── Homework Panel ── */}
              {activePanel === 'homework' && (
                <div className="space-y-3">
                  {hwLoading ? (
                    <div className="card text-center py-8">
                      <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
                    </div>
                  ) : homework.length === 0 ? (
                    <div className="card text-center py-8">
                      <p className="text-gray-400">숙제 기록이 없습니다.</p>
                    </div>
                  ) : (
                    <>
                      <div className="card">
                        <div className="flex gap-4 text-center">
                          <div className="flex-1">
                            <div className="text-2xl font-bold text-primary-600">{homework.length}</div>
                            <div className="text-xs text-gray-500">전체 과제</div>
                          </div>
                          <div className="flex-1">
                            <div className="text-2xl font-bold text-green-600">{homework.filter((h) => h.submission).length}</div>
                            <div className="text-xs text-gray-500">제출 완료</div>
                          </div>
                          <div className="flex-1">
                            <div className="text-2xl font-bold text-red-600">{homework.filter((h) => !h.submission).length}</div>
                            <div className="text-xs text-gray-500">미제출</div>
                          </div>
                        </div>
                      </div>
                      {homework.map((hw) => (
                        <div key={hw.id} className="card">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium text-gray-800">{hw.title}</span>
                                {hw.submission ? (
                                  <span className="badge-correct">제출</span>
                                ) : (
                                  <span className="badge-wrong">미제출</span>
                                )}
                              </div>
                              <p className="text-sm text-gray-500">{hw.description}</p>
                              <p className="text-xs text-gray-400 mt-1">{formatKoreanDate(hw.created_at)}</p>
                            </div>
                          </div>
                          {!hw.submission && hw.non_submit_reason && (
                            <div className="mt-2 text-xs text-orange-600 bg-orange-50 px-3 py-1.5 rounded-lg inline-block">
                              사유:{' '}
                              {hw.non_submit_reason.reason_code === 'forgot'
                                ? '깜빡했음'
                                : hw.non_submit_reason.reason_code === 'time'
                                ? '시간 부족'
                                : '난이도 높음'}
                            </div>
                          )}
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

function SimpleBarChart({ data }: { data: ChartPoint[] }) {
  const maxGrading = Math.max(...data.map((d) => d.gradingCount), 1)
  const maxChat = Math.max(...data.map((d) => d.chatCount), 1)
  const maxVal = Math.max(maxGrading, maxChat)

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
                title={`채점 ${d.gradingCount}회`}
              />
              <div
                className="bg-purple-400 rounded-t w-2/5"
                style={{ height: `${(d.chatCount / maxVal) * 100}%`, minHeight: d.chatCount > 0 ? '2px' : '0' }}
                title={`질문 ${d.chatCount}건`}
              />
            </div>
            <span className="text-xs text-gray-400 text-center leading-tight" style={{ fontSize: '10px' }}>
              {d.label.slice(0, 5)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
