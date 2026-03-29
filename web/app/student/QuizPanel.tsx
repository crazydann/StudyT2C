'use client'

import { useState } from 'react'

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

interface QuizResult {
  isCorrect: boolean
  correctIndex: number
  explanation: string
}

interface Props {
  quizzes: Quiz[]
  generating: boolean
  onGenerate: () => void
}

export default function QuizPanel({ quizzes, generating, onGenerate }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedChoice, setSelectedChoice] = useState<Record<string, number>>({})
  const [results, setResults] = useState<Record<string, QuizResult>>({})
  const [submitting, setSubmitting] = useState<string | null>(null)

  async function submitAttempt(quizId: string) {
    const choice = selectedChoice[quizId]
    if (choice === undefined) return
    setSubmitting(quizId)
    try {
      const res = await fetch('/api/quiz/attempt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quizId, selectedChoice: choice }),
      })
      const data = await res.json()
      if (data.ok) {
        setResults((prev) => ({ ...prev, [quizId]: { isCorrect: data.isCorrect, correctIndex: data.correctIndex, explanation: data.explanation } }))
      }
    } catch {}
    setSubmitting(null)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800">개념 복습 퀴즈</h3>
      </div>

      <button
        onClick={onGenerate}
        disabled={generating}
        className="w-full py-2 text-xs font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
      >
        {generating ? '퀴즈 생성 중...' : '+ 퀴즈 만들기'}
      </button>

      {quizzes.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-2">AI 튜터와 대화 후<br />퀴즈를 만들어 보세요</p>
      )}

      <div className="space-y-2">
        {quizzes.map((quiz) => {
          const isExpanded = expandedId === quiz.id
          const result = results[quiz.id]
          return (
            <div key={quiz.id} className="border border-gray-100 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedId(isExpanded ? null : quiz.id)}
                className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 transition-colors"
              >
                <span className="text-xs text-gray-700 font-medium truncate">{quiz.concept}</span>
                <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                  {quiz.lastAttempt && (
                    <span className={`text-xs ${quiz.lastAttempt.is_correct ? 'text-green-600' : 'text-red-500'}`}>
                      {quiz.lastAttempt.is_correct ? '✓' : '✗'}
                    </span>
                  )}
                  <span className="text-gray-400 text-xs">{isExpanded ? '▲' : '▼'}</span>
                </div>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 space-y-2 border-t border-gray-50">
                  <p className="text-xs text-gray-700 mt-2 leading-relaxed">{quiz.question}</p>
                  <div className="space-y-1">
                    {quiz.choices.map((choice, idx) => {
                      const isSelected = selectedChoice[quiz.id] === idx
                      const answered = !!result
                      const isCorrectChoice = answered && idx === result.correctIndex
                      const isWrongSelected = answered && isSelected && !result.isCorrect
                      return (
                        <label
                          key={idx}
                          className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer text-xs transition-colors ${
                            isCorrectChoice ? 'bg-green-50 text-green-700' :
                            isWrongSelected ? 'bg-red-50 text-red-700' :
                            isSelected ? 'bg-primary-50 text-primary-700' : 'hover:bg-gray-50 text-gray-700'
                          }`}
                        >
                          <input
                            type="radio"
                            name={`quiz-${quiz.id}`}
                            disabled={answered}
                            checked={isSelected}
                            onChange={() => setSelectedChoice((prev) => ({ ...prev, [quiz.id]: idx }))}
                            className="mt-0.5 flex-shrink-0"
                          />
                          <span>{idx + 1}. {choice}</span>
                        </label>
                      )
                    })}
                  </div>

                  {result ? (
                    <div className={`text-xs p-2 rounded-lg ${result.isCorrect ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                      <p className="font-semibold mb-1">{result.isCorrect ? '정답!' : '오답'}</p>
                      <p className="leading-relaxed">{result.explanation}</p>
                    </div>
                  ) : (
                    <button
                      onClick={() => submitAttempt(quiz.id)}
                      disabled={selectedChoice[quiz.id] === undefined || submitting === quiz.id}
                      className="w-full py-1.5 text-xs font-medium bg-primary-600 text-white rounded-lg disabled:opacity-50"
                    >
                      {submitting === quiz.id ? '채점 중...' : '제출'}
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
