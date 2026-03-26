'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const router = useRouter()
  const [handle, setHandle] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handle, password }),
      })

      const data = await res.json()

      if (!res.ok || !data.ok) {
        setError(data.error || '로그인에 실패했습니다.')
        return
      }

      if (data.role === 'student') router.push('/student')
      else if (data.role === 'teacher') router.push('/teacher')
      else if (data.role === 'parent') router.push('/parent')
      else router.push('/')
    } catch {
      setError('서버 오류가 발생했습니다. 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4 shadow-lg">
            <span className="text-white text-2xl font-bold">T2C</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">StudyT2C</h1>
          <p className="text-gray-500 mt-2">스마트 학습 도우미</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-6">로그인</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                아이디 (핸들)
              </label>
              <input
                type="text"
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                placeholder="아이디를 입력하세요"
                className="input-field"
                required
                autoComplete="username"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                비밀번호
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                className="input-field"
                required
                autoComplete="current-password"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !handle || !password}
              className="btn-primary w-full py-3 text-base mt-2"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  로그인 중...
                </span>
              ) : '로그인'}
            </button>
          </form>

          {/* Hint */}
          <div className="mt-6 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-400 text-center mb-3">테스트 계정</p>
            <div className="grid grid-cols-3 gap-2 text-xs text-center">
              <div className="bg-blue-50 rounded-lg p-2">
                <div className="font-semibold text-blue-700">학생</div>
                <div className="text-gray-500 mt-0.5">david, joshua</div>
              </div>
              <div className="bg-green-50 rounded-lg p-2">
                <div className="font-semibold text-green-700">선생님</div>
                <div className="text-gray-500 mt-0.5">teacher 계정</div>
              </div>
              <div className="bg-purple-50 rounded-lg p-2">
                <div className="font-semibold text-purple-700">학부모</div>
                <div className="text-gray-500 mt-0.5">parent 계정</div>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          © 2025 StudyT2C. All rights reserved.
        </p>
      </div>
    </div>
  )
}
