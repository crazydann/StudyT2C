export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { correctRate, rateByKey } from '@/lib/stats'

export async function GET(request: NextRequest) {
  try {
    requireSessionFromRequest(request, ['teacher'])

    // Korea time offset: UTC+9 — compute today's start in UTC
    const now = new Date()
    const koreaOffset = 9 * 60 * 60 * 1000
    const koreaToday = new Date(now.getTime() + koreaOffset)
    koreaToday.setUTCHours(0, 0, 0, 0)
    const todayStartUTC = new Date(koreaToday.getTime() - koreaOffset)

    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

    // 1. All students
    const { data: students, error: studentsError } = await supabaseAdmin
      .from('users')
      .select('id, handle')
      .eq('role', 'student')

    if (studentsError) throw studentsError
    const totalStudents = (students || []).length
    const studentIds = (students || []).map((s) => s.id)

    if (totalStudents === 0) {
      return NextResponse.json({
        ok: true,
        kpi: {
          totalStudents: 0,
          todayActive: 0,
          avgCorrectRate: 0,
          submissionRate: 0,
          focusScore: 100,
          atRiskCount: 0,
        },
        recentActivity: [],
      })
    }

    // 2. Today's active students (distinct student_user_id in focus_events)
    const { data: todayFocusRaw } = await supabaseAdmin
      .from('focus_events')
      .select('student_user_id')
      .gte('created_at', todayStartUTC.toISOString())

    const todayActiveSet = new Set((todayFocusRaw || []).map((e) => e.student_user_id))
    const todayActive = todayActiveSet.size

    // 3. Avg correct rate (last 30 days) via problem_items
    const { data: recentItems } = await supabaseAdmin
      .from('problem_items')
      .select('is_correct, student_user_id')
      .in('student_user_id', studentIds)
      .gte('created_at', thirtyDaysAgo.toISOString())

    const avgCorrectRate = correctRate(recentItems)

    // 4. Homework submission rate
    const { data: allAssignments } = await supabaseAdmin
      .from('homework_assignments')
      .select('id')
      .in('student_user_id', studentIds)

    let submissionRate = 0
    const totalAssignmentSlots = (allAssignments?.length || 0)
    if (totalAssignmentSlots > 0) {
      const assignmentIds = (allAssignments || []).map((a) => a.id)
      const { data: hwSubs } = await supabaseAdmin
        .from('homework_submissions')
        .select('id')
        .in('assignment_id', assignmentIds)

      submissionRate = Math.round(((hwSubs?.length || 0) / totalAssignmentSlots) * 100)
    }

    // 5. Focus score: avg tab leave count per student today → invert to 0-100
    const { data: todayLeftTab } = await supabaseAdmin
      .from('focus_events')
      .select('student_user_id')
      .eq('event_type', 'left_tab')
      .gte('created_at', todayStartUTC.toISOString())

    const leaveCountMap: Record<string, number> = {}
    ;(todayLeftTab || []).forEach((e) => {
      leaveCountMap[e.student_user_id] = (leaveCountMap[e.student_user_id] || 0) + 1
    })

    const avgLeaves = totalStudents > 0
      ? Object.values(leaveCountMap).reduce((a, b) => a + b, 0) / totalStudents
      : 0
    const focusScore = Math.round(Math.max(0, 100 - avgLeaves * 10))

    // 6. At-risk students: riskScore > 60
    // Per student: offTopicCount from chat_messages.meta where is_study=false last 7 days
    const { data: offTopicMsgs } = await supabaseAdmin
      .from('chat_messages')
      .select('student_user_id, meta')
      .in('student_user_id', studentIds)
      .eq('role', 'assistant') // is_study 메타는 assistant 응답에 저장됨
      .gte('created_at', sevenDaysAgo.toISOString())

    const offTopicCountMap: Record<string, number> = {}
    ;(offTopicMsgs || []).forEach((m) => {
      if (m.meta?.is_study === false) {
        offTopicCountMap[m.student_user_id] = (offTopicCountMap[m.student_user_id] || 0) + 1
      }
    })

    // Per student correct rate
    const studentCorrectMap = rateByKey(recentItems, (item) => item.student_user_id)

    // Recent focus events for lastSeen
    const { data: recentFocus } = await supabaseAdmin
      .from('focus_events')
      .select('student_user_id, created_at')
      .in('student_user_id', studentIds)
      .order('created_at', { ascending: false })

    const lastSeenMap: Record<string, string> = {}
    ;(recentFocus || []).forEach((e) => {
      if (!lastSeenMap[e.student_user_id]) {
        lastSeenMap[e.student_user_id] = e.created_at
      }
    })

    let atRiskCount = 0
    const recentActivity = (students || []).map((student) => {
      const sc = studentCorrectMap[student.id]
      const studentCorrectRate = sc && sc.total > 0 ? sc.rate : null
      const offTopicCount = offTopicCountMap[student.id] || 0

      // riskScore: weight correctRate + offTopicCount
      let riskScore = 0
      if (studentCorrectRate !== null && studentCorrectRate < 40) riskScore += 50
      else if (studentCorrectRate !== null && studentCorrectRate < 60) riskScore += 25
      if (offTopicCount > 5) riskScore += 40
      else if (offTopicCount > 2) riskScore += 20

      if (riskScore > 60) atRiskCount++

      let riskLevel: 'low' | 'medium' | 'high'
      if (studentCorrectRate !== null && (studentCorrectRate < 40 || offTopicCount > 5)) {
        riskLevel = 'high'
      } else if (studentCorrectRate !== null && studentCorrectRate < 60) {
        riskLevel = 'medium'
      } else {
        riskLevel = 'low'
      }

      return {
        studentId: student.id,
        handle: student.handle,
        lastSeen: lastSeenMap[student.id] || null,
        correctRate: studentCorrectRate,
        riskLevel,
      }
    })

    // Sort by lastSeen desc
    recentActivity.sort((a, b) => {
      if (!a.lastSeen) return 1
      if (!b.lastSeen) return -1
      return new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime()
    })

    return NextResponse.json({
      ok: true,
      kpi: {
        totalStudents,
        todayActive,
        avgCorrectRate,
        submissionRate,
        focusScore,
        atRiskCount,
      },
      recentActivity,
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Teacher dashboard error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
