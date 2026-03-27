export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

const SUBJECT_LABELS: Record<string, string> = {
  KOREAN: '국어',
  ENGLISH: '영어',
  MATH: '수학',
  SCIENCE: '과학',
}

const REASON_KO: Record<string, string> = {
  concept: '개념 부족',
  calculation: '계산 실수',
  reading: '문제 해석',
  time: '시간 부족',
  guessing: '찍음/감',
}

function isoNow() {
  return new Date().toISOString()
}

function daysAgo(n: number) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString()
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = requireSessionFromRequest(request, ['teacher', 'parent', 'student'])
    const studentId = params.id

    if (session.role === 'student' && session.id !== studentId) {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }

    const since30 = daysAgo(30)
    const since14 = daysAgo(14)
    const since7 = daysAgo(7)

    // ── 1. Problem items (30d) ──────────────────────────────────────
    const { data: problemItems } = await supabaseAdmin
      .from('problem_items')
      .select('id, is_correct, key_concepts, reason_category, created_at, student_user_id')
      .eq('student_user_id', studentId)
      .gte('created_at', since30)
      .order('created_at', { ascending: false })
      .limit(500)

    const items = problemItems || []
    const totalItems = items.length
    const correctItems = items.filter((i) => i.is_correct).length
    const avgCorrectRate = totalItems > 0 ? correctItems / totalItems : 0

    // Weak concepts from wrong answers
    const conceptCounts: Record<string, number> = {}
    items.filter((i) => !i.is_correct).forEach((item) => {
      ;(item.key_concepts || []).forEach((c: string) => {
        conceptCounts[c] = (conceptCounts[c] || 0) + 1
      })
    })
    const weakConcepts = Object.entries(conceptCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({ name, count }))

    // Weekly trend for story (problem_items by week)
    const weeklyScores: Record<string, { correct: number; total: number }> = {}
    items.forEach((item) => {
      const d = new Date(item.created_at)
      const iso = d.toISOString()
      const wk = iso.slice(0, 10).slice(0, 7) // YYYY-MM
      if (!weeklyScores[wk]) weeklyScores[wk] = { correct: 0, total: 0 }
      weeklyScores[wk].total++
      if (item.is_correct) weeklyScores[wk].correct++
    })
    const timeline = Object.entries(weeklyScores)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([month, s]) => ({ month, score: s.total > 0 ? s.correct / s.total : 0 }))

    // ── 2. Problem item feedback (wrong reasons, 30d) ──────────────
    const { data: feedbackRows } = await supabaseAdmin
      .from('problem_item_feedback')
      .select('reason_category, understanding')
      .eq('student_user_id', studentId)
      .gte('created_at', since30)
      .limit(500)

    const reasonCounts: Record<string, number> = {}
    ;(feedbackRows || []).forEach((r) => {
      if (r.reason_category) {
        reasonCounts[r.reason_category] = (reasonCounts[r.reason_category] || 0) + 1
      }
    })
    const wrongReasons = Object.entries(reasonCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([code, count]) => ({
        code,
        label: REASON_KO[code] || code,
        count,
      }))

    // ── 3. Chat messages (30d) ──────────────────────────────────────
    const { data: chatRows } = await supabaseAdmin
      .from('chat_messages')
      .select('id, content, meta, role, created_at')
      .eq('student_user_id', studentId)
      .gte('created_at', since30)
      .order('created_at', { ascending: false })
      .limit(300)

    const allChats = chatRows || []
    const userChats30 = allChats.filter((c) => c.role === 'user')
    const userChats7 = allChats.filter(
      (c) => c.role === 'user' && c.created_at >= since7
    )

    // Subject question counts from meta
    const subjectQCounts: Record<string, number> = {}
    userChats30.forEach((c) => {
      const meta = typeof c.meta === 'string' ? tryParse(c.meta) : c.meta || {}
      const subj = (meta?.subject || '').toUpperCase()
      if (subj && SUBJECT_LABELS[subj]) {
        subjectQCounts[subj] = (subjectQCounts[subj] || 0) + 1
      }
    })

    // Subject achievement (based on question activity only, since no subject_code in problem_items)
    const subjectAchievement = Object.keys(SUBJECT_LABELS).map((code) => {
      const qCnt = subjectQCounts[code] || 0
      // score = correct_rate * 80 + min(q,20)*1 (no grading data per-subject, just questions)
      const score = Math.min(qCnt, 20)
      return {
        code,
        label: SUBJECT_LABELS[code],
        score,
        correctRate: avgCorrectRate,
        questionCount: qCnt,
      }
    })
    const avgScore = Math.round(
      subjectAchievement.reduce((s, x) => s + x.score, 0) / subjectAchievement.length
    )

    // Off-topic chat (7d) - messages where meta.mode=studying and meta.is_study=false
    const offTopicItems: { created_at: string; content: string; category: string }[] = []
    const offTopicCatCount: Record<string, number> = {}
    allChats
      .filter((c) => c.created_at >= since7)
      .forEach((c) => {
        const meta = typeof c.meta === 'string' ? tryParse(c.meta) : c.meta || {}
        if (!meta) return
        const isOfftopic =
          meta.is_study === false ||
          meta.is_study === 'false' ||
          String(meta.is_study).toLowerCase() === 'false'
        if (meta.mode === 'studying' && isOfftopic) {
          const cat = meta.offtopic_category || 'OTHER'
          offTopicCatCount[cat] = (offTopicCatCount[cat] || 0) + 1
          offTopicItems.push({
            created_at: c.created_at,
            content: (c.content || '').slice(0, 80),
            category: cat,
          })
        }
      })

    // Study chat history (30d) - messages where meta.is_study=true
    const studyChatItems: {
      created_at: string
      question: string
      answer: string
      subject: string
    }[] = []
    userChats30.forEach((c) => {
      const meta = typeof c.meta === 'string' ? tryParse(c.meta) : c.meta || {}
      if (!meta) return
      const isStudy =
        meta.is_study === true || meta.is_study === 'true' || String(meta.is_study).toLowerCase() === 'true'
      if (isStudy) {
        studyChatItems.push({
          created_at: c.created_at,
          question: (c.content || '').slice(0, 200),
          answer: (meta.answer || '').slice(0, 400),
          subject: meta.subject || 'OTHER',
        })
      }
    })

    // ── 4. Homework data ────────────────────────────────────────────
    const { data: allAssignments } = await supabaseAdmin
      .from('homework_assignments')
      .select('id, created_at')
      .eq('student_user_id', studentId)

    const assignIds = (allAssignments || []).map((a) => a.id)
    let submittedIds: string[] = []
    if (assignIds.length > 0) {
      const { data: hwSubs } = await supabaseAdmin
        .from('homework_submissions')
        .select('assignment_id')
        .in('assignment_id', assignIds)
      submittedIds = (hwSubs || []).map((s) => s.assignment_id)
    }
    const submissionRate =
      assignIds.length > 0 ? submittedIds.length / assignIds.length : 0

    // ── 5. Streak days ──────────────────────────────────────────────
    const streakDays = await computeStreakDays(studentId)

    // ── 6. Weekly/monthly report (4 weeks) ─────────────────────────
    const weeklyChart = await buildPeriodChart(studentId, 'week', 4)
    const monthlyChart = await buildPeriodChart(studentId, 'month', 3)

    // ── 7. Story card (rule-based) ──────────────────────────────────
    let improved = '최근 30일 성취도 변화를 분석 중입니다.'
    let stillWeak = ''
    let nextPlan = ''

    if (timeline.length >= 2) {
      const first = timeline[0].score
      const last = timeline[timeline.length - 1].score
      const diff = last - first
      if (diff > 0.05) {
        improved = `최근 한 달 동안 전체 정답률이 약 ${Math.round(diff * 100)}%p 올랐어요.`
      } else if (diff < -0.05) {
        improved = `최근 한 달 동안 정답률이 약 ${Math.round(Math.abs(diff) * 100)}%p 내려갔어요.`
      } else {
        improved = '최근 한 달 동안 전체 정답률은 비슷한 수준을 유지하고 있어요.'
      }
    }
    if (weakConcepts.length > 0) {
      stillWeak = `${weakConcepts
        .slice(0, 3)
        .map((c) => c.name)
        .join(' · ')} 개념에서 오답이 자주 나와요.`
    }
    if (weakConcepts.length > 0) {
      nextPlan = `다음 수업에서는 ${weakConcepts
        .slice(0, 2)
        .map((c) => c.name)
        .join(' · ')} 중심으로 보강할 예정입니다.`
    } else {
      nextPlan = '다음 수업에서는 최근 헷갈렸던 개념들을 정리하는 데 집중할 예정입니다.'
    }

    // ── 8. Trend sentence ───────────────────────────────────────────
    const totalQ = userChats30.length
    const crPct = Math.round(avgCorrectRate * 100)
    let trendSentence = `최근 30일간 튜터 질문 ${totalQ}건, 평균 정답률 ${crPct}%입니다.`
    if (wrongReasons.length > 0) {
      trendSentence += ` 자주 틀리는 유형은 ${wrongReasons[0].label}입니다.`
    }

    // ── 9. Recommendation ──────────────────────────────────────────
    let recommendation = '아직 오답·취약점 데이터가 부족합니다.'
    if (weakConcepts.length > 0 || wrongReasons.length > 0) {
      const parts = []
      if (weakConcepts.length > 0) {
        parts.push(`**${weakConcepts.slice(0, 3).map((c) => c.name).join(', ')}** 보강 권장`)
      }
      if (wrongReasons.length > 0) {
        parts.push(`(오답 유형: ${wrongReasons.slice(0, 2).map((r) => r.label).join(', ')})`)
      }
      recommendation = '이번 주에는 ' + parts.join(' ') + '.'
    }

    return NextResponse.json({
      ok: true,
      report: {
        // summary metrics
        avgScore,
        totalQuestions: totalQ,
        avgCorrectRate: crPct,
        chatCount7d: userChats7.length,
        submissionRate: Math.round(submissionRate * 100),
        streakDays,
        // wrong reasons
        wrongReasons,
        // subject achievement
        subjectAchievement,
        // off-topic
        offTopicTotal: offTopicItems.length,
        offTopicByCategory: offTopicCatCount,
        offTopicItems: offTopicItems.slice(0, 20),
        // study chat history
        studyChatHistory: studyChatItems.slice(0, 30),
        // weekly/monthly charts
        weeklyChart,
        monthlyChart,
        // story card
        storyCard: {
          improved,
          stillWeak,
          nextPlan,
          tips: [
            '이번 상담에서 선생님께, 집에서 아이를 어떻게 도와주면 좋을지 구체적인 예시를 물어보세요.',
            '아이에게 최근에 특히 헷갈렸던 문제를 하나 골라 왜 헷갈렸는지 이야기해 보세요.',
          ],
        },
        // trend + recommendation
        trendSentence,
        recommendation,
        // weak concepts
        weakConcepts,
      },
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Report error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}

function tryParse(s: string): Record<string, unknown> | null {
  try {
    return JSON.parse(s)
  } catch {
    return null
  }
}

async function computeStreakDays(studentId: string): Promise<number> {
  const since = daysAgo(365)
  const activeDates = new Set<string>()

  try {
    const { data: subs } = await supabaseAdmin
      .from('problem_submissions')
      .select('created_at')
      .eq('student_user_id', studentId)
      .gte('created_at', since)
      .limit(2000)
    ;(subs || []).forEach((r) => {
      if (r.created_at) activeDates.add(r.created_at.slice(0, 10))
    })
  } catch {}

  try {
    const { data: chats } = await supabaseAdmin
      .from('chat_messages')
      .select('created_at')
      .eq('student_user_id', studentId)
      .eq('role', 'user')
      .gte('created_at', since)
      .limit(2000)
    ;(chats || []).forEach((r) => {
      if (r.created_at) activeDates.add(r.created_at.slice(0, 10))
    })
  } catch {}

  const today = new Date()
  const todayStr = today.toISOString().slice(0, 10)
  if (!activeDates.has(todayStr)) return 0

  let streak = 0
  const cur = new Date(today)
  while (true) {
    const s = cur.toISOString().slice(0, 10)
    if (activeDates.has(s)) {
      streak++
      cur.setDate(cur.getDate() - 1)
    } else {
      break
    }
  }
  return streak
}

async function buildPeriodChart(
  studentId: string,
  period: 'week' | 'month',
  windows: number
): Promise<
  {
    label: string
    gradingCount: number
    chatCount: number
    wrongRate: number | null
    submissionRate: number | null
  }[]
> {
  const now = new Date()
  const deltaDays = period === 'week' ? 7 : 30
  const chart = []

  for (let i = windows - 1; i >= 0; i--) {
    const endDt = new Date(now.getTime() - i * deltaDays * 86400000)
    const startDt = new Date(endDt.getTime() - deltaDays * 86400000)
    const startIso = startDt.toISOString()
    const endIso = endDt.toISOString()
    const label =
      startDt.toISOString().slice(5, 10) + '~' + endDt.toISOString().slice(5, 10)

    let gradingCount = 0
    let chatCount = 0
    let wrongRate: number | null = null
    let submissionRate: number | null = null

    try {
      const { data: subs } = await supabaseAdmin
        .from('problem_submissions')
        .select('id')
        .eq('student_user_id', studentId)
        .gte('created_at', startIso)
        .lt('created_at', endIso)
      gradingCount = (subs || []).length
    } catch {}

    try {
      const { data: pItems } = await supabaseAdmin
        .from('problem_items')
        .select('is_correct')
        .eq('student_user_id', studentId)
        .gte('created_at', startIso)
        .lt('created_at', endIso)
      const pI = pItems || []
      if (pI.length > 0) {
        const wrong = pI.filter((x) => !x.is_correct).length
        wrongRate = wrong / pI.length
      }
    } catch {}

    try {
      const { data: chats } = await supabaseAdmin
        .from('chat_messages')
        .select('id')
        .eq('student_user_id', studentId)
        .eq('role', 'user')
        .gte('created_at', startIso)
        .lt('created_at', endIso)
      chatCount = (chats || []).length
    } catch {}

    try {
      const { data: assigns } = await supabaseAdmin
        .from('homework_assignments')
        .select('id')
        .eq('student_user_id', studentId)
        .gte('created_at', startIso)
        .lt('created_at', endIso)
      const aIds = (assigns || []).map((a) => a.id)
      if (aIds.length > 0) {
        const { data: hwSubs } = await supabaseAdmin
          .from('homework_submissions')
          .select('assignment_id')
          .in('assignment_id', aIds)
        const submitted = new Set((hwSubs || []).map((s) => s.assignment_id)).size
        submissionRate = submitted / aIds.length
      }
    } catch {}

    chart.push({ label, gradingCount, chatCount, wrongRate, submissionRate })
  }

  return chart
}
