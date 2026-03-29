'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { formatRelativeTime, formatKoreanDate } from '@/lib/utils'
import SnapshotPanel from './SnapshotPanel'
import QuizPanel from './QuizPanel'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  meta?: { mode?: string; is_study?: boolean; offtopic_category?: string }
}

interface GradedItem {
  item_no: number
  is_correct: boolean
  key_concepts: string[]
  explanation_summary: string
  reason_category: string
}

interface HomeworkItem {
  id: string
  title: string
  description: string
  created_at: string
  submission: { id: string; created_at: string } | null
  non_submit_reason: { reason_code: string } | null
}

interface Snapshot {
  strongConcepts: string[]
  weakConcepts: string[]
  totalProblems: number
  correctRate: number
}

interface Quiz {
  id: string
  concept: string
  question: string
  choices: string[]
  correct_index: number
  explanation: string
  created_at: string
  lastAttempt: { is_correct: boolean } | null
}

type Tab = 'chat' | 'grade' | 'homework'

export default function StudentPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; handle: string; status?: string } | null>(null)
  const [studentMode, setStudentMode] = useState<'studying' | 'break'>('break')
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [loading, setLoading] = useState(true)
  const [showFocusWarning, setShowFocusWarning] = useState(false)

  // Snapshot & Quiz
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [snapshotLoading, setSnapshotLoading] = useState(false)
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [generatingQuiz, setGeneratingQuiz] = useState(false)

  // Chat state
  const [messages, setMessages] = useState<Message[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Grade state
  const [gradeMode, setGradeMode] = useState<'image' | 'text'>('image')
  const [gradeText, setGradeText] = useState('')
  const [gradeFile, setGradeFile] = useState<File | null>(null)
  const [gradePreviewUrl, setGradePreviewUrl] = useState<string | null>(null)
  const [imageRotation, setImageRotation] = useState(0)
  const [gradeLoading, setGradeLoading] = useState(false)
  const [gradedItems, setGradedItems] = useState<GradedItem[] | null>(null)
  const [gradeError, setGradeError] = useState('')
  const [gradingHistory, setGradingHistory] = useState<{ id: string; created_at: string; stats: { total: number; correct: number; rate: number } }[]>([])

  // Homework state
  const [homework, setHomework] = useState<HomeworkItem[]>([])
  const [hwLoading, setHwLoading] = useState(false)
  const [selectedReason, setSelectedReason] = useState<Record<string, string>>({})
  const [submittingReason, setSubmittingReason] = useState<string | null>(null)
  const [pendingHwCount, setPendingHwCount] = useState<number | null>(null)

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth/me')
        if (!res.ok) { router.push('/login'); return }
        const data = await res.json()
        if (data.user?.role !== 'student') { router.push('/login'); return }
        setUser(data.user)
        setStudentMode(data.user?.status === 'studying' ? 'studying' : 'break')
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    checkAuth()
  }, [router])

  // Focus tracker
  useEffect(() => {
    if (!user) return
    const handleVisibilityChange = () => {
      const eventType = document.hidden ? 'left_tab' : 'returned_tab'
      fetch('/api/focus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: eventType }),
      }).catch(() => {})
      if (!document.hidden && studentMode === 'studying') {
        setShowFocusWarning(true)
        setTimeout(() => setShowFocusWarning(false), 4000)
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [user, studentMode])

  const loadMessages = useCallback(async () => {
    try {
      const res = await fetch('/api/chat')
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      }
    } catch {}
  }, [])

  const loadHomework = useCallback(async () => {
    setHwLoading(true)
    try {
      const res = await fetch('/api/homework')
      if (res.ok) {
        const data = await res.json()
        setHomework(data.homework || [])
      }
    } catch {}
    finally { setHwLoading(false) }
  }, [])

  const loadGradingHistory = useCallback(async (userId: string) => {
    try {
      const res = await fetch(`/api/student/${userId}/grading`)
      if (res.ok) {
        const data = await res.json()
        setGradingHistory((data.submissions || []).slice(0, 5))
      }
    } catch {}
  }, [])

  const loadSnapshot = useCallback(async () => {
    setSnapshotLoading(true)
    try {
      const res = await fetch('/api/student/snapshot')
      if (res.ok) {
        const data = await res.json()
        if (data.ok) setSnapshot(data.snapshot)
      }
    } catch {}
    finally { setSnapshotLoading(false) }
  }, [])

  const loadQuizzes = useCallback(async () => {
    try {
      const res = await fetch('/api/quiz/list')
      if (res.ok) {
        const data = await res.json()
        if (data.ok) setQuizzes(data.quizzes || [])
      }
    } catch {}
  }, [])

  useEffect(() => {
    if (user) {
      loadMessages()
      loadGradingHistory(user.id)
      loadSnapshot()
      loadQuizzes()
      fetch('/api/homework')
        .then((r) => r.json())
        .then((d) => {
          if (d.homework) {
            const pending = (d.homework as HomeworkItem[]).filter(
              (h) => !h.submission && !h.non_submit_reason
            ).length
            setPendingHwCount(pending)
          }
        })
        .catch(() => {})
    }
  }, [user, loadMessages, loadGradingHistory, loadSnapshot, loadQuizzes])

  useEffect(() => {
    if (activeTab === 'homework' && user) loadHomework()
  }, [activeTab, user, loadHomework])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function generateQuiz() {
    setGeneratingQuiz(true)
    try {
      const res = await fetch('/api/quiz/generate', { method: 'POST' })
      const data = await res.json()
      if (data.ok) {
        await loadQuizzes()
      } else {
        alert(data.error || '퀴즈 생성에 실패했습니다.')
      }
    } catch {}
    finally { setGeneratingQuiz(false) }
  }

  function handleConceptClick(concept: string) {
    setChatInput(`${concept} 개념을 쉽게 설명해줘`)
    setActiveTab('chat')
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault()
    if (!chatInput.trim() || chatLoading) return
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: chatInput.trim(),
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setChatInput('')
    setChatLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content }),
      })
      const data = await res.json()
      if (data.ok) {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.reply,
          created_at: new Date().toISOString(),
        }])
      }
    } catch {}
    finally { setChatLoading(false) }
  }

  async function handleGrade(e: React.FormEvent) {
    e.preventDefault()
    setGradeLoading(true)
    setGradeError('')
    setGradedItems(null)
    try {
      let res: Response
      if (gradeMode === 'image' && gradeFile) {
        const formData = new FormData()
        formData.append('file', gradeFile)
        res = await fetch('/api/grade', { method: 'POST', body: formData })
      } else if (gradeMode === 'text' && gradeText.trim()) {
        res = await fetch('/api/grade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: gradeText }),
        })
      } else {
        setGradeError('파일 또는 텍스트를 입력해주세요.')
        setGradeLoading(false)
        return
      }
      const data = await res.json()
      if (data.ok) {
        setGradedItems(data.items)
        loadSnapshot() // refresh snapshot after grading
      } else {
        setGradeError(data.error || '채점에 실패했습니다.')
      }
    } catch {
      setGradeError('서버 오류가 발생했습니다.')
    } finally {
      setGradeLoading(false)
    }
  }

  async function submitNonReason(assignmentId: string) {
    const reason = selectedReason[assignmentId]
    if (!reason) return
    setSubmittingReason(assignmentId)
    try {
      await fetch('/api/homework', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignment_id: assignmentId, reason_code: reason }),
      })
      loadHomework()
    } catch {}
    finally { setSubmittingReason(null) }
  }

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-10 w-10 border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">로딩 중...</p>
        </div>
      </div>
    )
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'chat', label: 'AI 튜터' },
    { key: 'grade', label: '채점' },
    { key: 'homework', label: '숙제' },
  ]

  // ── Grading Panel (shared between desktop right panel and mobile tab) ──
  const GradingContent = (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <h2 className="text-sm font-semibold text-gray-800 mb-3">AI 채점</h2>
        <div className="flex gap-2 mb-4">
          {(['image', 'text'] as const).map((m) => (
            <button key={m} onClick={() => setGradeMode(m)}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${gradeMode === m ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {m === 'image' ? '이미지 업로드' : '텍스트 입력'}
            </button>
          ))}
        </div>
        <form onSubmit={handleGrade} className="space-y-3">
          {gradeMode === 'image' ? (
            <div>
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-5 text-center cursor-pointer hover:border-primary-400 transition-colors"
                onClick={() => document.getElementById('file-input')?.click()}>
                {gradeFile && gradePreviewUrl ? (
                  <div onClick={(e) => e.stopPropagation()}>
                    <img src={gradePreviewUrl} alt="preview"
                      className="max-h-36 mx-auto rounded-lg object-contain transition-transform"
                      style={{ transform: `rotate(${imageRotation}deg)` }} />
                    <div className="flex justify-center gap-1 mt-2">
                      {[['↺', -90], ['↻', 90], ['180°', 180]].map(([label, deg]) => (
                        <button key={label} type="button"
                          onClick={() => setImageRotation((r) => r + (deg as number))}
                          className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-0.5 rounded">{label}</button>
                      ))}
                      <button type="button" onClick={() => setImageRotation(0)}
                        className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-0.5 rounded">초기화</button>
                    </div>
                    <button type="button" onClick={() => { setGradeFile(null); setGradePreviewUrl(null); setImageRotation(0) }}
                      className="text-xs text-red-500 mt-1 hover:underline">파일 제거</button>
                  </div>
                ) : (
                  <>
                    <div className="text-3xl mb-1">📷</div>
                    <p className="text-xs text-gray-600">클릭하여 이미지 선택</p>
                    <p className="text-xs text-gray-400">JPG, PNG, GIF</p>
                  </>
                )}
              </div>
              <input id="file-input" type="file" accept="image/*" className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0] || null
                  setGradeFile(f); setImageRotation(0)
                  if (f?.type.startsWith('image/')) setGradePreviewUrl(URL.createObjectURL(f))
                  else setGradePreviewUrl(null)
                }} />
            </div>
          ) : (
            <textarea value={gradeText} onChange={(e) => setGradeText(e.target.value)}
              placeholder="문제와 답안을 붙여넣어 주세요." className="input-field h-32 resize-none text-sm" />
          )}
          {gradeError && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{gradeError}</p>}
          <button type="submit" disabled={gradeLoading || (gradeMode === 'image' ? !gradeFile : !gradeText.trim())}
            className="btn-primary w-full py-2 text-sm">
            {gradeLoading ? 'AI 채점 중...' : 'AI 채점 시작'}
          </button>
        </form>
      </div>

      {gradedItems && gradedItems.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-800">채점 결과</h3>
            <span className="text-sm font-bold text-primary-600">
              {Math.round((gradedItems.filter((i) => i.is_correct).length / gradedItems.length) * 100)}%
            </span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full mb-3 overflow-hidden">
            <div className="h-full bg-primary-600 rounded-full transition-all"
              style={{ width: `${Math.round((gradedItems.filter((i) => i.is_correct).length / gradedItems.length) * 100)}%` }} />
          </div>
          <div className="space-y-2">
            {gradedItems.map((item) => (
              <div key={item.item_no} className={`p-3 rounded-lg border text-xs ${item.is_correct ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ${item.is_correct ? 'bg-green-500' : 'bg-red-500'}`}>{item.item_no}</span>
                  <span className={item.is_correct ? 'badge-correct' : 'badge-wrong'}>{item.is_correct ? '정답' : '오답'}</span>
                  {!item.is_correct && item.reason_category && <span className="badge-blue">{item.reason_category}</span>}
                </div>
                <p className="text-gray-700 leading-relaxed">{item.explanation_summary}</p>
                {item.key_concepts.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {item.key_concepts.map((c) => (
                      <span key={c} className="text-xs bg-white px-1.5 py-0.5 rounded-full text-gray-600 border border-gray-200">{c}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {gradingHistory.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-2">최근 채점 이력</h3>
          <div className="space-y-1.5">
            {gradingHistory.map((h) => (
              <div key={h.id} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-xs text-gray-500">{new Date(h.created_at).toLocaleDateString('ko-KR')}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{h.stats.total}문제</span>
                  <span className={`text-xs font-semibold ${h.stats.rate >= 70 ? 'text-green-600' : h.stats.rate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>{h.stats.rate}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  // ── Chat content ──
  const ChatContent = (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 pb-4">
        {/* 보완 개념 추천 배너 */}
        {snapshot && snapshot.weakConcepts.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-xl px-3 py-2 flex flex-wrap items-center gap-2">
            <span className="text-xs text-orange-700 font-medium">복습 추천</span>
            {snapshot.weakConcepts.map((c) => (
              <button key={c} onClick={() => handleConceptClick(c)}
                className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors">
                {c}
              </button>
            ))}
          </div>
        )}

        {/* 오늘 할 일 */}
        {pendingHwCount !== null && pendingHwCount > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-amber-100 transition-colors"
            onClick={() => setActiveTab('homework')}>
            <div className="flex items-center gap-2">
              <span>📋</span>
              <p className="text-xs text-amber-800 font-medium">미제출 숙제 {pendingHwCount}건</p>
            </div>
            <span className="text-amber-600 text-xs">›</span>
          </div>
        )}

        {/* Studying mode notice */}
        {studentMode === 'studying' && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-3 py-2 flex items-center gap-2 text-xs text-green-700">
            <span>📚</span>
            <span>공부 모드 활성화 — 학습 관련 질문만 답변해요</span>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-14 h-14 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">🤖</span>
            </div>
            <h3 className="text-base font-semibold text-gray-800 mb-1">AI 튜터</h3>
            <p className="text-gray-500 text-xs max-w-xs mx-auto">
              {studentMode === 'studying' ? '공부 모드예요. 학습 질문을 해보세요!' : '수학, 국어, 영어, 과학 등 질문해보세요.'}
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-1">
                  <span className="text-white text-xs">AI</span>
                </div>
              )}
              <div className={`max-w-[85%] rounded-2xl px-3 py-2.5 text-sm whitespace-pre-wrap ${
                msg.role === 'user' ? 'bg-primary-600 text-white rounded-br-sm' : 'bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100'
              }`}>
                {msg.content}
                <div className={`text-xs mt-1 ${msg.role === 'user' ? 'text-primary-200' : 'text-gray-400'}`}>
                  {formatRelativeTime(msg.created_at)}
                </div>
              </div>
            </div>
          ))
        )}
        {chatLoading && (
          <div className="flex justify-start">
            <div className="w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center mr-2 flex-shrink-0">
              <span className="text-white text-xs">AI</span>
            </div>
            <div className="bg-white rounded-2xl rounded-bl-sm shadow-sm border border-gray-100 px-4 py-3">
              <div className="flex gap-1">
                {[0, 150, 300].map((d) => (
                  <span key={d} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <form onSubmit={sendMessage} className="flex gap-2 pt-3 border-t border-gray-200">
        <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)}
          placeholder="학습 관련 질문을 입력하세요..."
          className="input-field flex-1 text-sm" disabled={chatLoading} />
        <button type="submit" disabled={!chatInput.trim() || chatLoading} className="btn-primary px-4 text-sm">전송</button>
      </form>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {showFocusWarning && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-amber-500 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium animate-bounce">
          공부 시간이에요! 집중해 주세요 📚
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">T2C</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">StudyT2C</span>
              <span className="text-sm text-gray-500">{user?.handle}</span>
              {studentMode === 'studying' ? (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">공부 중 🟢</span>
              ) : (
                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">휴식 중 🟡</span>
              )}
            </div>
          </div>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">로그아웃</button>
        </div>

        {/* Mobile tabs only */}
        <div className="lg:hidden max-w-7xl mx-auto px-4">
          <div className="flex gap-6 border-b border-gray-100">
            {tabs.map((tab) => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`py-3 text-sm transition-colors ${activeTab === tab.key ? 'tab-active' : 'tab-inactive'}`}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ── Desktop 3-column layout ── */}
      <div className="hidden lg:flex max-w-7xl mx-auto px-4 py-4 gap-4 h-[calc(100vh-64px)]">
        {/* Left panel */}
        <div className="w-60 xl:w-64 flex-shrink-0 flex flex-col gap-3 overflow-y-auto">
          <SnapshotPanel snapshot={snapshot} loading={snapshotLoading} onConceptClick={handleConceptClick} />
          <QuizPanel quizzes={quizzes} generating={generatingQuiz} onGenerate={generateQuiz} />
        </div>

        {/* Center: Chat */}
        <div className="flex-1 bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-col min-h-0">
          {ChatContent}
        </div>

        {/* Right panel: Grading */}
        <div className="w-72 xl:w-80 flex-shrink-0 overflow-y-auto">
          {GradingContent}
        </div>
      </div>

      {/* ── Mobile tab layout ── */}
      <main className="lg:hidden max-w-4xl mx-auto px-4 py-4">
        {activeTab === 'chat' && (
          <div className="flex flex-col gap-3">
            {/* Compact snapshot on mobile */}
            {snapshot && snapshot.totalProblems > 0 && (
              <SnapshotPanel snapshot={snapshot} loading={snapshotLoading} onConceptClick={handleConceptClick} />
            )}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4" style={{ height: 'calc(100vh - 220px)' }}>
              {ChatContent}
            </div>
          </div>
        )}

        {activeTab === 'grade' && GradingContent}

        {activeTab === 'homework' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">숙제 현황</h2>
              <button onClick={loadHomework} className="btn-secondary text-sm py-1.5">새로고침</button>
            </div>
            {hwLoading ? (
              <div className="text-center py-12">
                <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
              </div>
            ) : homework.length === 0 ? (
              <div className="card text-center py-12">
                <div className="text-4xl mb-3">📚</div>
                <p className="text-gray-500">아직 숙제가 없습니다.</p>
              </div>
            ) : (
              homework.map((hw) => (
                <div key={hw.id} className="card">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-800">{hw.title}</h3>
                        {hw.submission ? (
                          <span className="badge-correct">제출 완료</span>
                        ) : hw.non_submit_reason ? (
                          <span className="badge-wrong">미제출</span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">미제출</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{hw.description}</p>
                      <p className="text-xs text-gray-400 mt-1">{formatKoreanDate(hw.created_at)}</p>
                    </div>
                  </div>
                  {hw.submission && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs text-green-600">제출일: {formatKoreanDate(hw.submission.created_at)}</p>
                    </div>
                  )}
                  {!hw.submission && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      {hw.non_submit_reason ? (
                        <p className="text-xs text-gray-500">미제출 사유: {
                          hw.non_submit_reason.reason_code === 'forgot' ? '깜빡했어요' :
                          hw.non_submit_reason.reason_code === 'time' ? '시간이 없었어요' : '너무 어려웠어요'
                        }</p>
                      ) : (
                        <div className="flex items-center gap-2">
                          <select value={selectedReason[hw.id] || ''}
                            onChange={(e) => setSelectedReason((prev) => ({ ...prev, [hw.id]: e.target.value }))}
                            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 flex-1">
                            <option value="">미제출 사유 선택</option>
                            <option value="forgot">깜빡했어요</option>
                            <option value="time">시간이 없었어요</option>
                            <option value="hard">너무 어려웠어요</option>
                          </select>
                          <button onClick={() => submitNonReason(hw.id)}
                            disabled={!selectedReason[hw.id] || submittingReason === hw.id}
                            className="btn-secondary text-sm py-1.5">
                            {submittingReason === hw.id ? '저장 중...' : '저장'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  )
}
