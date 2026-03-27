'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { formatRelativeTime, formatKoreanDate } from '@/lib/utils'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
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

type Tab = 'chat' | 'grade' | 'homework'

export default function StudentPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; handle: string } | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [loading, setLoading] = useState(true)

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

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth/me')
        if (!res.ok) {
          router.push('/login')
          return
        }
        const data = await res.json()
        if (data.user?.role !== 'student') {
          router.push('/login')
          return
        }
        setUser(data.user)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    checkAuth()
  }, [router])

  const loadMessages = useCallback(async () => {
    try {
      const res = await fetch('/api/chat')
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      }
    } catch {
      // ignore
    }
  }, [])

  const loadHomework = useCallback(async () => {
    setHwLoading(true)
    try {
      const res = await fetch('/api/homework')
      if (res.ok) {
        const data = await res.json()
        setHomework(data.homework || [])
      }
    } catch {
      // ignore
    } finally {
      setHwLoading(false)
    }
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

  useEffect(() => {
    if (user) {
      loadMessages()
      loadGradingHistory(user.id)
    }
  }, [user, loadMessages, loadGradingHistory])

  useEffect(() => {
    if (activeTab === 'homework' && user) {
      loadHomework()
    }
  }, [activeTab, user, loadHomework])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.reply,
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      }
    } catch {
      // ignore
    } finally {
      setChatLoading(false)
    }
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
    } catch {
      // ignore
    } finally {
      setSubmittingReason(null)
    }
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">T2C</span>
            </div>
            <div>
              <span className="font-semibold text-gray-900">StudyT2C</span>
              <span className="ml-2 text-sm text-gray-500">{user?.handle}</span>
            </div>
          </div>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">
            로그아웃
          </button>
        </div>

        {/* Tabs */}
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex gap-6 border-b border-gray-100">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`py-3 text-sm transition-colors ${
                  activeTab === tab.key ? 'tab-active' : 'tab-inactive'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* AI 튜터 Tab */}
        {activeTab === 'chat' && (
          <div className="flex flex-col h-[calc(100vh-160px)]">
            <div className="flex-1 overflow-y-auto space-y-4 pb-4">
              {messages.length === 0 ? (
                <div className="text-center py-16">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-3xl">🤖</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">AI 튜터에 오신 것을 환영합니다!</h3>
                  <p className="text-gray-500 text-sm max-w-sm mx-auto">
                    수학, 국어, 영어, 과학, 사회 등 학습 관련 질문을 자유롭게 해보세요.
                  </p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-1">
                        <span className="text-white text-xs">AI</span>
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                        msg.role === 'user'
                          ? 'bg-primary-600 text-white rounded-br-sm'
                          : 'bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100'
                      }`}
                    >
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
                  <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center mr-2 flex-shrink-0">
                    <span className="text-white text-xs">AI</span>
                  </div>
                  <div className="bg-white rounded-2xl rounded-bl-sm shadow-sm border border-gray-100 px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={sendMessage} className="flex gap-2 pt-4 border-t border-gray-200">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="학습 관련 질문을 입력하세요..."
                className="input-field flex-1"
                disabled={chatLoading}
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || chatLoading}
                className="btn-primary px-5"
              >
                전송
              </button>
            </form>
          </div>
        )}

        {/* 채점 Tab */}
        {activeTab === 'grade' && (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">AI 채점</h2>

              {/* Mode toggle */}
              <div className="flex gap-2 mb-6">
                <button
                  onClick={() => setGradeMode('image')}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gradeMode === 'image'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  이미지 업로드
                </button>
                <button
                  onClick={() => setGradeMode('text')}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gradeMode === 'text'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  텍스트 입력
                </button>
              </div>

              <form onSubmit={handleGrade} className="space-y-4">
                {gradeMode === 'image' ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      시험지 이미지 업로드
                    </label>
                    <div
                      className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-primary-400 transition-colors"
                      onClick={() => document.getElementById('file-input')?.click()}
                    >
                      {gradeFile && gradePreviewUrl ? (
                        <div onClick={(e) => e.stopPropagation()}>
                          <img
                            src={gradePreviewUrl}
                            alt="preview"
                            className="max-h-48 mx-auto rounded-lg object-contain transition-transform"
                            style={{ transform: `rotate(${imageRotation}deg)` }}
                          />
                          <div className="flex items-center justify-center gap-2 mt-3">
                            <button type="button" onClick={() => setImageRotation((r) => r - 90)} className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded">↺ -90°</button>
                            <button type="button" onClick={() => setImageRotation((r) => r + 90)} className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded">↻ +90°</button>
                            <button type="button" onClick={() => setImageRotation((r) => r + 180)} className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded">180°</button>
                            <button type="button" onClick={() => setImageRotation(0)} className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded">초기화</button>
                          </div>
                          <p className="text-xs text-gray-500 mt-2">{gradeFile.name} · {(gradeFile.size / 1024 / 1024).toFixed(2)} MB</p>
                          <button
                            type="button"
                            onClick={() => { setGradeFile(null); setGradePreviewUrl(null); setImageRotation(0) }}
                            className="text-xs text-red-500 mt-1 hover:underline"
                          >
                            파일 제거
                          </button>
                        </div>
                      ) : gradeFile ? (
                        <div>
                          <p className="text-sm font-medium text-gray-800">{gradeFile.name}</p>
                          <p className="text-xs text-gray-500 mt-1">{(gradeFile.size / 1024 / 1024).toFixed(2)} MB</p>
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setGradeFile(null); setGradePreviewUrl(null); setImageRotation(0) }}
                            className="text-xs text-red-500 mt-2 hover:underline"
                          >
                            파일 제거
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="text-4xl mb-2">📷</div>
                          <p className="text-sm text-gray-600">클릭하여 이미지 선택</p>
                          <p className="text-xs text-gray-400 mt-1">JPG, PNG, GIF 지원</p>
                        </>
                      )}
                    </div>
                    <input
                      id="file-input"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0] || null
                        setGradeFile(f)
                        setImageRotation(0)
                        if (f && f.type.startsWith('image/')) {
                          const url = URL.createObjectURL(f)
                          setGradePreviewUrl(url)
                        } else {
                          setGradePreviewUrl(null)
                        }
                      }}
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      문제 및 답안 텍스트
                    </label>
                    <textarea
                      value={gradeText}
                      onChange={(e) => setGradeText(e.target.value)}
                      placeholder="문제와 학생의 답안을 붙여넣어 주세요.&#10;예) 1번: 문제... 답: 3번&#10;2번: 문제... 답: 2번"
                      className="input-field h-48 resize-none"
                    />
                  </div>
                )}

                {gradeError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                    {gradeError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={gradeLoading || (gradeMode === 'image' ? !gradeFile : !gradeText.trim())}
                  className="btn-primary w-full py-3"
                >
                  {gradeLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      AI가 채점 중입니다...
                    </span>
                  ) : 'AI 채점 시작'}
                </button>
              </form>
            </div>

            {/* Grading Results */}
            {gradedItems && gradedItems.length > 0 && (
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-800">채점 결과</h3>
                  <div className="flex gap-3 text-sm">
                    <span className="badge-correct">
                      정답 {gradedItems.filter((i) => i.is_correct).length}개
                    </span>
                    <span className="badge-wrong">
                      오답 {gradedItems.filter((i) => !i.is_correct).length}개
                    </span>
                  </div>
                </div>

                {/* Score bar */}
                <div className="mb-6">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>정답률</span>
                    <span className="font-semibold">
                      {Math.round((gradedItems.filter((i) => i.is_correct).length / gradedItems.length) * 100)}%
                    </span>
                  </div>
                  <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 rounded-full transition-all"
                      style={{
                        width: `${Math.round((gradedItems.filter((i) => i.is_correct).length / gradedItems.length) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-3">
                  {gradedItems.map((item) => (
                    <div
                      key={item.item_no}
                      className={`p-4 rounded-xl border ${
                        item.is_correct
                          ? 'bg-green-50 border-green-200'
                          : 'bg-red-50 border-red-200'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0 ${
                            item.is_correct ? 'bg-green-500' : 'bg-red-500'
                          }`}
                        >
                          {item.item_no}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={item.is_correct ? 'badge-correct' : 'badge-wrong'}>
                              {item.is_correct ? '정답' : '오답'}
                            </span>
                            {!item.is_correct && item.reason_category && (
                              <span className="badge-blue">{item.reason_category}</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-700 mt-1">{item.explanation_summary}</p>
                          {item.key_concepts.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {item.key_concepts.map((concept) => (
                                <span
                                  key={concept}
                                  className="text-xs bg-white px-2 py-0.5 rounded-full text-gray-600 border border-gray-200"
                                >
                                  {concept}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Grading History */}
            {gradingHistory.length > 0 && (
              <div className="card">
                <h3 className="text-base font-semibold text-gray-800 mb-3">최근 채점 이력</h3>
                <div className="space-y-2">
                  {gradingHistory.map((h) => (
                    <div key={h.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                      <span className="text-sm text-gray-600">{new Date(h.created_at).toLocaleDateString('ko-KR')}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-400">{h.stats.total}문제</span>
                        <span className={`text-sm font-semibold ${h.stats.rate >= 70 ? 'text-green-600' : h.stats.rate >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {h.stats.rate}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 숙제 Tab */}
        {activeTab === 'homework' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">숙제 현황</h2>
              <button onClick={loadHomework} className="btn-secondary text-sm py-1.5">
                새로고침
              </button>
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
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            미제출
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{hw.description}</p>
                      <p className="text-xs text-gray-400 mt-1">{formatKoreanDate(hw.created_at)}</p>
                    </div>
                  </div>

                  {/* Submission info */}
                  {hw.submission && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs text-green-600">
                        제출일: {formatKoreanDate(hw.submission.created_at)}
                      </p>
                    </div>
                  )}

                  {/* Non-submit reason */}
                  {!hw.submission && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      {hw.non_submit_reason ? (
                        <p className="text-xs text-gray-500">
                          미제출 사유:{' '}
                          {hw.non_submit_reason.reason_code === 'forgot'
                            ? '깜빡했어요'
                            : hw.non_submit_reason.reason_code === 'time'
                            ? '시간이 없었어요'
                            : '너무 어려웠어요'}
                        </p>
                      ) : (
                        <div className="flex items-center gap-2">
                          <select
                            value={selectedReason[hw.id] || ''}
                            onChange={(e) =>
                              setSelectedReason((prev) => ({ ...prev, [hw.id]: e.target.value }))
                            }
                            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 flex-1"
                          >
                            <option value="">미제출 사유 선택</option>
                            <option value="forgot">깜빡했어요</option>
                            <option value="time">시간이 없었어요</option>
                            <option value="hard">너무 어려웠어요</option>
                          </select>
                          <button
                            onClick={() => submitNonReason(hw.id)}
                            disabled={!selectedReason[hw.id] || submittingReason === hw.id}
                            className="btn-secondary text-sm py-1.5"
                          >
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
