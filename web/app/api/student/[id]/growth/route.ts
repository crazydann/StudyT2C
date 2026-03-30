export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

function getISOWeek(date: Date): { week: string; label: string } {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
  const year = d.getUTCFullYear()
  // label: first day of that ISO week (Monday)
  const jan4 = new Date(Date.UTC(year, 0, 4))
  const jan4Day = jan4.getUTCDay() || 7
  const weekMonday = new Date(jan4.getTime() + (weekNo - 1) * 7 * 86400000 - (jan4Day - 1) * 86400000)
  const mo = weekMonday.getUTCMonth() + 1
  const dy = weekMonday.getUTCDate()
  return {
    week: `${year}-W${String(weekNo).padStart(2, '0')}`,
    label: `${mo}/${dy}`,
  }
}

function getLast8Weeks(): Array<{ week: string; label: string }> {
  const weeks: Array<{ week: string; label: string }> = []
  const now = new Date()
  for (let i = 7; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 7 * 24 * 60 * 60 * 1000)
    weeks.push(getISOWeek(d))
  }
  // Deduplicate (in case current week appears twice near boundary)
  const seen = new Set<string>()
  return weeks.filter((w) => {
    if (seen.has(w.week)) return false
    seen.add(w.week)
    return true
  }).slice(-8)
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = requireSessionFromRequest(request)
    const studentId = params.id

    if (session.role === 'student' && session.id !== studentId) {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }

    const now = new Date()
    const sixtyDaysAgo = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000)
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)

    // Fetch problem_items for this student (last 60 days covers 8 weeks safely)
    const { data: items } = await supabaseAdmin
      .from('problem_items')
      .select('is_correct, created_at')
      .eq('student_user_id', studentId)
      .gte('created_at', sixtyDaysAgo.toISOString())

    // Group by ISO week
    const weekMap: Record<string, { correct: number; total: number }> = {}
    ;(items || []).forEach((item) => {
      const { week } = getISOWeek(new Date(item.created_at))
      if (!weekMap[week]) weekMap[week] = { correct: 0, total: 0 }
      weekMap[week].total++
      if (item.is_correct) weekMap[week].correct++
    })

    const last8Weeks = getLast8Weeks()
    const growth = last8Weeks.map(({ week, label }) => {
      const data = weekMap[week]
      if (!data || data.total === 0) {
        return { week, label, correctRate: null, totalProblems: 0 }
      }
      return {
        week,
        label,
        correctRate: Math.round((data.correct / data.total) * 100),
        totalProblems: data.total,
      }
    })

    // Streak: consecutive days with at least 1 chat message or problem submission
    // Check last 30 days working backwards from today
    const { data: chatDays } = await supabaseAdmin
      .from('chat_messages')
      .select('created_at')
      .eq('student_user_id', studentId)
      .eq('role', 'user')
      .gte('created_at', thirtyDaysAgo.toISOString())

    const { data: submissionDays } = await supabaseAdmin
      .from('problem_submissions')
      .select('created_at')
      .eq('student_user_id', studentId)
      .gte('created_at', thirtyDaysAgo.toISOString())

    const activeDays = new Set<string>()
    ;(chatDays || []).forEach((m) => {
      activeDays.add(new Date(m.created_at).toISOString().slice(0, 10))
    })
    ;(submissionDays || []).forEach((s) => {
      activeDays.add(new Date(s.created_at).toISOString().slice(0, 10))
    })

    let streak = 0
    for (let i = 0; i < 30; i++) {
      const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
      const dateStr = d.toISOString().slice(0, 10)
      if (activeDays.has(dateStr)) {
        streak++
      } else {
        break
      }
    }

    return NextResponse.json({ ok: true, growth, streak })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Growth error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
