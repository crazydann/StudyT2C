'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { formatKoreanDate, formatKoreanDateTime } from '@/lib/utils'
import KpiCard from './KpiCard'
import StudentGrid from './StudentGrid'
import GrowthChart from './GrowthChart'

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

interface ClassStudent {
  id: string; handle: string; status: string
  correctRate: number; submissionRate: number; offTopicCount: number; riskScore: number; atRisk: boolean
}
interface ClassData {
  totalCount: number; atRiskCount: number; avgCorrectRate: number; avgSubmissionRate: number; students: ClassStudent[]
}

interface KpiData {
  totalStudents: number
  todayActive: number
  avgCorrectRate: number
  submissionRate: number
  focusScore: number
  atRiskCount: number
}

interface WeekData {
  label: string
  correctRate: number | null
  totalProblems: number
}

type Panel = 'briefing' | 'report' | 'notes' | 'grading' | 'homework'

export default function TeacherPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; handle: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [students, setStudents] = useState<Student[]>([])
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null)
  const [classView, setClassView] = useState(false)
  const [classData, setClassData] = useState<ClassData | null>(null)
  const [classLoading, setClassLoading] = useState(false)
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
  const [noteOneliner, setNoteOneliner] = useState('')
  const [noteCompletion, setNoteCompletion] = useState<'충분히' | '일부' | '미흡'>('충분히')
  const [noteSaved, setNoteSaved] = useState(false)
  const [noteSaving, setNoteSaving] = useState(false)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [gradingLoading, setGradingLoading] = useState(false)
  const [homework, setHomework] = useState<HomeworkItem[]>([])
  const [hwLoading, setHwLoading] = useState(false)

  // Dashboard / KPI
  const [kpi, setKpi] = useState<KpiData | null>(null)
  const [kpiLoading, setKpiLoading] = useState(false)
  const [gridView, setGridView] = useState(false)
  const [selectedStudentGrowth, setSelectedStudentGrowth] = useState<WeekData[] | null>(null)

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

  const loadClassData = useCallback(async () => {
    setClassLoading(true)
    try {
      const res = await fetch('/api/class/summary')
      const data = await res.json()
      if (data.ok) setClassData(data.classData)
    } catch {}
    finally { setClassLoading(false) }
  }, [])

  const loadKpi = useCallback(async () => {
    setKpiLoading(true)
    try {
      const res = await fetch('/api/teacher/dashboard')
      const data = await res.json()
      if (data.ok) setKpi(data.kpi)
    } catch {}
    finally { setKpiLoading(false) }
  }, [])

  const loadStudentGrowth = useCallback(async (studentId: string) => {
    try {
      const res = await fetch(`/api/student/${studentId}/growth`)
      const data = await res.json()
      if (data.ok) setSelectedStudentGrowth(data.growth)
    } catch {}
  }, [])

  const loadNote = useCallback(async (studentId: string) => {
    try {
      const res = await fetch(`/api/student/${studentId}/notes`)
      const data = await res.json()
      const raw = data.note?.note || ''
      // Parse structured format
      const onelinerMatch = raw.match(/^ONELINER:(.+)$/m)
      const completionMatch = raw.match(/^COMPLETION:(.+)$/m)
      const notesMatch = raw.match(/^---\n([\s\S]*)$/)
      setNoteOneliner(onelinerMatch ? onelinerMatch[1].trim() : '')
      setNoteCompletion((completionMatch ? completionMatch[1].trim() : '충분히') as '충분히' | '일부' | '미흡')
      setNote(notesMatch ? notesMatch[1].trim() : raw.replace(/^(ONELINER|COMPLETION):.+\n?/gm, '').replace(/^---\n?/, '').trim())
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
    if (user) {
      loadClassData()
      loadKpi()
    }
  }, [user, loadClassData, loadKpi])

  useEffect(() => {
    if (!selectedStudent) return
    setSummary(null)
    setReport(null)
    setNote('')
    setNoteOneliner('')
    setNoteCompletion('충분히')
    setSubmissions([])
    setHomework([])
    setActivePanel('briefing')
    setShowStudyChat(false)
    setShowOffTopic(false)
    setSelectedStudentGrowth(null)
    loadSummary(selectedStudent.id)
    loadNote(selectedStudent.id)
    loadStudentGrowth(selectedStudent.id)
  }, [selectedStudent, loadSummary, loadNote, loadStudentGrowth])

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
      const structured = `ONELINER:${noteOneliner}\nCOMPLETION:${noteCompletion}\n---\n${note}`
      await fetch(`/api/student/${selectedStudent.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: structured }),
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

      <div className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 md:flex md:gap-6">

        {/* Desktop sidebar (always visible on md+) */}
        <aside className="hidden md:block w-56 flex-shrink-0">
          <div className="card p-4">
            {/* 원장 대시보드 button */}
            <button
              onClick={() => { setClassView(false); setSelectedStudent(null); setGridView(false) }}
              className={`w-full text-left px-3 py-2.5 rounded-lg mb-2 transition-colors text-sm font-medium flex items-center gap-2 ${
                !classView && !selectedStudent ? 'bg-purple-50 text-purple-700' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span>🏠</span> 원장 대시보드
            </button>
            {/* 반 요약 button */}
            <button
              onClick={() => { setClassView(true); setSelectedStudent(null) }}
              className={`w-full text-left px-3 py-2.5 rounded-lg mb-3 transition-colors text-sm font-medium flex items-center gap-2 ${
                classView ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span>📊</span> 반 요약
            </button>
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
                    onClick={() => { setSelectedStudent(student); setClassView(false) }}
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

        {/* Mobile: student picker (shown only when no student selected) */}
        {!selectedStudent && (
          <div className="md:hidden">
            <div className="card p-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                담당 학생 선택
              </h2>
              {students.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">연결된 학생이 없습니다.</p>
              ) : (
                <div className="space-y-2">
                  {students.map((student) => (
                    <button
                      key={student.id}
                      onClick={() => { setSelectedStudent(student); setClassView(false) }}
                      className="w-full text-left px-4 py-3 rounded-xl bg-gray-50 hover:bg-primary-50 hover:text-primary-700 transition-colors flex items-center gap-3"
                    >
                      <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-bold text-base">
                        {student.handle[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{student.handle}</p>
                        <p className="text-xs text-gray-400">탭하여 상세 보기</p>
                      </div>
                      <span className="ml-auto text-gray-400">›</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Main */}
        <main className={`flex-1 min-w-0 ${!selectedStudent && !classView ? 'hidden md:block' : ''}`}>
          {/* ── 반 요약 ── */}
          {classView && !selectedStudent && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-2xl">📊</span>
                <h2 className="text-xl font-bold text-gray-900">반 전체 요약</h2>
              </div>
              {classLoading ? (
                <div className="card text-center py-10">
                  <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
                </div>
              ) : classData ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="card text-center">
                      <div className="text-3xl font-bold text-gray-800 mb-1">{classData.totalCount}명</div>
                      <div className="text-xs text-gray-500">전체 학생</div>
                    </div>
                    <div className="card text-center">
                      <div className={`text-3xl font-bold mb-1 ${classData.atRiskCount > 0 ? 'text-red-600' : 'text-green-600'}`}>{classData.atRiskCount}명</div>
                      <div className="text-xs text-gray-500">주의 학생</div>
                    </div>
                    <div className="card text-center">
                      <div className="text-3xl font-bold text-primary-600 mb-1">{classData.avgCorrectRate}%</div>
                      <div className="text-xs text-gray-500">평균 정답률</div>
                    </div>
                    <div className="card text-center">
                      <div className="text-3xl font-bold text-green-600 mb-1">{classData.avgSubmissionRate}%</div>
                      <div className="text-xs text-gray-500">평균 숙제 제출률</div>
                    </div>
                  </div>
                  {classData.atRiskCount > 0 && (
                    <div className="card border-l-4 border-l-red-500 bg-red-50">
                      <p className="text-sm font-semibold text-red-700 mb-2">⚠️ 주의 필요 학생</p>
                      <div className="space-y-2">
                        {classData.students.filter(s => s.atRisk).map(s => (
                          <div key={s.id} className="flex items-center justify-between">
                            <button
                              onClick={() => { setSelectedStudent(students.find(st => st.id === s.id) || null); setClassView(false) }}
                              className="text-sm font-medium text-red-700 hover:underline"
                            >
                              {s.handle}
                            </button>
                            <div className="flex gap-3 text-xs text-gray-600">
                              <span>정답률 {s.correctRate}%</span>
                              <span>제출률 {s.submissionRate}%</span>
                              <span className="font-semibold text-red-600">위험도 {s.riskScore}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="card overflow-x-auto">
                    <h3 className="font-semibold text-gray-800 mb-4">학생별 현황</h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                          <th className="pb-2 pr-4">이름</th>
                          <th className="pb-2 pr-4">모드</th>
                          <th className="pb-2 pr-4 text-right">정답률</th>
                          <th className="pb-2 pr-4 text-right">제출률</th>
                          <th className="pb-2 pr-4 text-right">이탈질문</th>
                          <th className="pb-2 text-right">위험도</th>
                        </tr>
                      </thead>
                      <tbody>
                        {classData.students.map(s => (
                          <tr key={s.id} className={`border-b border-gray-50 last:border-0 ${s.atRisk ? 'bg-red-50' : ''}`}>
                            <td className="py-2 pr-4">
                              <button
                                onClick={() => { setSelectedStudent(students.find(st => st.id === s.id) || null); setClassView(false) }}
                                className="font-medium text-primary-600 hover:underline"
                              >
                                {s.handle}
                              </button>
                            </td>
                            <td className="py-2 pr-4">
                              <span className={`text-xs px-2 py-0.5 rounded-full ${s.status === 'studying' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                {s.status === 'studying' ? '공부' : '휴식'}
                              </span>
                            </td>
                            <td className={`py-2 pr-4 text-right font-medium ${s.correctRate >= 70 ? 'text-green-600' : s.correctRate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>{s.correctRate}%</td>
                            <td className={`py-2 pr-4 text-right ${s.submissionRate >= 70 ? 'text-green-600' : 'text-orange-500'}`}>{s.submissionRate}%</td>
                            <td className="py-2 pr-4 text-right text-gray-600">{s.offTopicCount}건</td>
                            <td className={`py-2 text-right font-semibold ${s.riskScore >= 70 ? 'text-red-600' : s.riskScore >= 50 ? 'text-orange-500' : 'text-green-600'}`}>{s.riskScore}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className="card text-center py-8"><p className="text-gray-400">데이터를 불러오지 못했습니다.</p></div>
              )}
            </div>
          )}

          {!selectedStudent && !classView ? (
            <div className="space-y-6">
              {/* KPI Cards Row */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-bold text-gray-900">🏠 원장 대시보드</h2>
                  {kpiLoading && (
                    <div className="animate-spin h-4 w-4 border-2 border-purple-600 border-t-transparent rounded-full" />
                  )}
                </div>
                {kpi ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    <KpiCard icon="👥" label="전체 학생" value={kpi.totalStudents} sub="명" color="purple" />
                    <KpiCard icon="🟢" label="오늘 접속" value={kpi.todayActive} sub="명" color="blue" />
                    <KpiCard icon="✅" label="평균 정답률" value={`${kpi.avgCorrectRate}%`} color="green" />
                    <KpiCard icon="📚" label="숙제 제출률" value={`${kpi.submissionRate}%`} color="yellow" />
                    <KpiCard icon="🎯" label="집중도" value={`${kpi.focusScore}점`} color="blue" />
                    <KpiCard icon="⚠️" label="주의 학생" value={kpi.atRiskCount} sub="명" color="red" />
                  </div>
                ) : !kpiLoading ? (
                  <div className="card text-center py-6">
                    <p className="text-gray-400 text-sm">대시보드 데이터를 불러오지 못했습니다.</p>
                  </div>
                ) : null}
              </div>

              {/* Student Grid Toggle */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-base font-semibold text-gray-800">학생 현황 그리드</h3>
                  <button
                    onClick={() => setGridView((v) => !v)}
                    className="text-sm px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium transition-colors"
                  >
                    {gridView ? '▲ 접기' : '▼ 펼치기'}
                  </button>
                </div>
                {gridView && classData && (
                  <StudentGrid
                    students={classData.students.map((s) => ({
                      id: s.id,
                      handle: s.handle,
                      correctRate: s.correctRate,
                      riskLevel: s.riskScore >= 70 ? 'high' : s.riskScore >= 40 ? 'medium' : 'low',
                      lastSeen: null,
                      todayActive: s.status === 'studying',
                    }))}
                    onSelect={(id) => {
                      const found = students.find((st) => st.id === id)
                      if (found) { setSelectedStudent(found); setClassView(false) }
                    }}
                  />
                )}
                {gridView && !classData && (
                  <p className="text-sm text-gray-400">반 데이터가 없습니다.</p>
                )}
              </div>
            </div>
          ) : selectedStudent ? (
            <div className="space-y-4">
              {/* Mobile back button */}
              <button
                onClick={() => setSelectedStudent(null)}
                className="md:hidden flex items-center gap-1 text-sm text-primary-600 font-medium mb-1"
              >
                ‹ 학생 변경
              </button>
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

              {/* ── Growth Chart (always shown when data available) ── */}
              {selectedStudentGrowth && selectedStudentGrowth.length > 0 && (
                <div className="card">
                  <GrowthChart data={selectedStudentGrowth} title={`${selectedStudent.handle} 주간 성장 그래프`} />
                </div>
              )}

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
                <div className="space-y-4">
                  <div className="card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-800">상담 로그</h3>
                      {noteSaved && <span className="text-xs text-green-600 font-medium">저장되었습니다!</span>}
                    </div>
                    {/* One-liner */}
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">한 줄 요약</label>
                      <input
                        type="text"
                        value={noteOneliner}
                        onChange={(e) => setNoteOneliner(e.target.value)}
                        placeholder="예) 이차방정식 개념 보강 필요, 숙제 습관 개선 중"
                        className="input-field"
                      />
                    </div>
                    {/* Completion level */}
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">상담 완료도</label>
                      <div className="flex gap-2">
                        {(['충분히', '일부', '미흡'] as const).map((level) => (
                          <button
                            key={level}
                            onClick={() => setNoteCompletion(level)}
                            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                              noteCompletion === level
                                ? level === '충분히' ? 'bg-green-600 text-white' : level === '일부' ? 'bg-yellow-500 text-white' : 'bg-red-500 text-white'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            {level === '충분히' ? '충분히 다룸' : level === '일부' ? '일부만 다룸' : '거의 못 다룸'}
                          </button>
                        ))}
                      </div>
                    </div>
                    {/* Notes textarea */}
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">상세 노트</label>
                      <textarea
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder={`${selectedStudent.handle} 학생 상담 내용, 특이사항 등을 기록하세요.`}
                        className="input-field h-48 resize-none"
                      />
                    </div>
                    <button onClick={saveNote} disabled={noteSaving} className="btn-primary">
                      {noteSaving ? '저장 중...' : '저장'}
                    </button>
                  </div>
                  {/* Preview */}
                  {(noteOneliner || note) && (
                    <div className="card bg-gray-50 border border-gray-200">
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">저장된 내용 미리보기</p>
                      {noteOneliner && <p className="text-sm font-medium text-gray-800 mb-1">📌 {noteOneliner}</p>}
                      <p className="text-xs text-gray-500 mb-2">완료도: <span className={`font-medium ${noteCompletion === '충분히' ? 'text-green-600' : noteCompletion === '일부' ? 'text-yellow-600' : 'text-red-600'}`}>{noteCompletion === '충분히' ? '충분히 다룸' : noteCompletion === '일부' ? '일부만 다룸' : '거의 못 다룸'}</span></p>
                      {note && <p className="text-sm text-gray-600 whitespace-pre-wrap">{note}</p>}
                    </div>
                  )}
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
          ) : null}
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
