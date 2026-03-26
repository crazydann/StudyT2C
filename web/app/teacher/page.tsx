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
}

type Panel = 'briefing' | 'notes' | 'grading' | 'homework'

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
    } catch {
      // ignore
    } finally {
      setSummaryLoading(false)
    }
  }, [])

  const loadNote = useCallback(async (studentId: string) => {
    try {
      const res = await fetch(`/api/student/${studentId}/notes`)
      const data = await res.json()
      if (data.ok) setNote(data.note?.note || '')
    } catch {
      // ignore
    }
  }, [])

  const loadGrading = useCallback(async (studentId: string) => {
    setGradingLoading(true)
    try {
      const res = await fetch(`/api/student/${studentId}/grading`)
      const data = await res.json()
      if (data.ok) setSubmissions(data.submissions)
    } catch {
      // ignore
    } finally {
      setGradingLoading(false)
    }
  }, [])

  const loadHomework = useCallback(async (studentId: string) => {
    setHwLoading(true)
    try {
      const res = await fetch(`/api/homework?studentId=${studentId}`)
      const data = await res.json()
      if (data.ok) setHomework(data.homework)
    } catch {
      // ignore
    } finally {
      setHwLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!selectedStudent) return
    setSummary(null)
    setNote('')
    setSubmissions([])
    setHomework([])
    setActivePanel('briefing')
    loadSummary(selectedStudent.id)
    loadNote(selectedStudent.id)
  }, [selectedStudent, loadSummary, loadNote])

  useEffect(() => {
    if (!selectedStudent) return
    if (activePanel === 'grading') loadGrading(selectedStudent.id)
    if (activePanel === 'homework') loadHomework(selectedStudent.id)
  }, [activePanel, selectedStudent, loadGrading, loadHomework])

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
    } catch {
      // ignore
    } finally {
      setNoteSaving(false)
    }
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
    { key: 'notes', label: '상담 노트' },
    { key: 'grading', label: '채점 이력' },
    { key: 'homework', label: '숙제 현황' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
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
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">
            로그아웃
          </button>
        </div>
      </header>

      <div className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 flex gap-6">
        {/* Left Sidebar - Student List */}
        <aside className="w-64 flex-shrink-0">
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

        {/* Main Panel */}
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
              <div className="flex gap-1 bg-white border border-gray-200 rounded-xl p-1">
                {panels.map((p) => (
                  <button
                    key={p.key}
                    onClick={() => setActivePanel(p.key)}
                    className={`flex-1 py-2 text-sm rounded-lg transition-colors font-medium ${
                      activePanel === p.key
                        ? 'bg-primary-600 text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Briefing Panel */}
              {activePanel === 'briefing' && (
                <div className="space-y-4">
                  {summaryLoading ? (
                    <div className="card text-center py-8">
                      <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
                    </div>
                  ) : summary ? (
                    <>
                      {/* Stats row */}
                      <div className="grid grid-cols-3 gap-4">
                        <div className="card text-center">
                          <div className="text-3xl font-bold text-primary-600 mb-1">
                            {summary.correctRate}%
                          </div>
                          <div className="text-xs text-gray-500">평균 정답률</div>
                        </div>
                        <div className="card text-center">
                          <div className="text-3xl font-bold text-green-600 mb-1">
                            {summary.homeworkRate}%
                          </div>
                          <div className="text-xs text-gray-500">숙제 제출률</div>
                        </div>
                        <div className="card text-center">
                          <div className="text-3xl font-bold text-purple-600 mb-1">
                            {summary.chatCount}
                          </div>
                          <div className="text-xs text-gray-500">주간 질문 수</div>
                        </div>
                      </div>

                      {/* Weak concepts */}
                      <div className="card">
                        <h3 className="font-semibold text-gray-800 mb-3">취약 개념 (최근 30일)</h3>
                        {summary.weakConcepts.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {summary.weakConcepts.map((concept, i) => (
                              <span
                                key={concept}
                                className={`px-3 py-1 rounded-full text-sm font-medium ${
                                  i === 0
                                    ? 'bg-red-100 text-red-700'
                                    : i === 1
                                    ? 'bg-orange-100 text-orange-700'
                                    : 'bg-yellow-100 text-yellow-700'
                                }`}
                              >
                                {concept}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">취약 개념 데이터가 없습니다.</p>
                        )}
                      </div>

                      {/* Recent submissions */}
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

              {/* Notes Panel */}
              {activePanel === 'notes' && (
                <div className="card">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-800">상담 노트</h3>
                    {noteSaved && (
                      <span className="text-xs text-green-600 font-medium">저장되었습니다!</span>
                    )}
                  </div>
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder={`${selectedStudent.handle} 학생에 대한 상담 노트를 작성하세요.\n\n예) 수학 이차방정식 개념 취약, 영어 독해 속도 개선 필요...`}
                    className="input-field h-64 resize-none mb-4"
                  />
                  <button
                    onClick={saveNote}
                    disabled={noteSaving}
                    className="btn-primary"
                  >
                    {noteSaving ? '저장 중...' : '저장'}
                  </button>
                </div>
              )}

              {/* Grading History Panel */}
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
                            <p className="font-medium text-gray-800">
                              {formatKoreanDateTime(sub.created_at)}
                            </p>
                            <p className="text-sm text-gray-500 mt-0.5">
                              총 {sub.stats.total}문제 중 {sub.stats.correct}개 정답
                            </p>
                          </div>
                          <div className="text-right">
                            <div
                              className={`text-2xl font-bold ${
                                sub.stats.rate >= 70 ? 'text-green-600' : sub.stats.rate >= 50 ? 'text-yellow-600' : 'text-red-600'
                              }`}
                            >
                              {sub.stats.rate}%
                            </div>
                            <div className="flex gap-2 text-xs mt-1">
                              <span className="badge-correct">{sub.stats.correct}정</span>
                              <span className="badge-wrong">{sub.stats.wrong}오</span>
                            </div>
                          </div>
                        </div>

                        {/* Wrong items */}
                        {sub.items.filter((i) => !i.is_correct).length > 0 && (
                          <div className="border-t border-gray-100 pt-3 mt-3">
                            <p className="text-xs font-medium text-gray-500 mb-2">오답 문항</p>
                            <div className="space-y-2">
                              {sub.items
                                .filter((i) => !i.is_correct)
                                .map((item) => (
                                  <div key={item.id} className="text-sm bg-red-50 rounded-lg p-2">
                                    <div className="flex items-center gap-2 mb-0.5">
                                      <span className="font-medium text-red-700">{item.item_no}번</span>
                                      {item.reason_category && (
                                        <span className="badge-blue text-xs">{item.reason_category}</span>
                                      )}
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

              {/* Homework Panel */}
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
                            <div className="text-2xl font-bold text-primary-600">
                              {homework.length}
                            </div>
                            <div className="text-xs text-gray-500">전체 과제</div>
                          </div>
                          <div className="flex-1">
                            <div className="text-2xl font-bold text-green-600">
                              {homework.filter((h) => h.submission).length}
                            </div>
                            <div className="text-xs text-gray-500">제출 완료</div>
                          </div>
                          <div className="flex-1">
                            <div className="text-2xl font-bold text-red-600">
                              {homework.filter((h) => !h.submission).length}
                            </div>
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
