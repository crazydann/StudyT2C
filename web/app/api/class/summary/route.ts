export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { correctRate } from '@/lib/stats'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['teacher'])

    const { data: links } = await supabaseAdmin
      .from('teacher_student_links')
      .select('student_user_id')
      .eq('teacher_user_id', session.id)

    const studentIds = (links || []).map((l) => l.student_user_id)
    if (studentIds.length === 0) {
      return NextResponse.json({ ok: true, classData: { totalCount: 0, atRiskCount: 0, avgCorrectRate: 0, avgSubmissionRate: 0, students: [] } })
    }

    const { data: students } = await supabaseAdmin
      .from('users')
      .select('id, handle, status')
      .in('id', studentIds)
      .eq('role', 'student')

    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
    const fourteenDaysAgo = new Date()
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14)
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    const { data: submissions } = await supabaseAdmin
      .from('problem_submissions')
      .select('id, student_user_id')
      .in('student_user_id', studentIds)
      .gte('created_at', thirtyDaysAgo.toISOString())

    const submissionToStudent: Record<string, string> = {}
    const submissionIds: string[] = []
    ;(submissions || []).forEach((s) => {
      submissionToStudent[s.id] = s.student_user_id
      submissionIds.push(s.id)
    })

    const itemsByStudent: Record<string, { is_correct: boolean }[]> = {}
    if (submissionIds.length > 0) {
      const { data: items } = await supabaseAdmin
        .from('problem_items')
        .select('is_correct, submission_id')
        .in('submission_id', submissionIds)
      ;(items || []).forEach((item) => {
        const studentId = submissionToStudent[item.submission_id]
        if (!studentId) return
        if (!itemsByStudent[studentId]) itemsByStudent[studentId] = []
        itemsByStudent[studentId].push({ is_correct: item.is_correct })
      })
    }

    const { data: assignments } = await supabaseAdmin
      .from('homework_assignments')
      .select('id, student_user_id')
      .in('student_user_id', studentIds)
      .gte('created_at', fourteenDaysAgo.toISOString())

    const assignmentToStudent: Record<string, string> = {}
    const assignmentCountByStudent: Record<string, number> = {}
    const assignmentIds: string[] = []
    ;(assignments || []).forEach((a) => {
      assignmentToStudent[a.id] = a.student_user_id
      assignmentCountByStudent[a.student_user_id] = (assignmentCountByStudent[a.student_user_id] || 0) + 1
      assignmentIds.push(a.id)
    })

    const submissionCountByStudent: Record<string, number> = {}
    if (assignmentIds.length > 0) {
      const { data: hwSubs } = await supabaseAdmin
        .from('homework_submissions')
        .select('assignment_id, student_user_id')
        .in('student_user_id', studentIds)
        .in('assignment_id', assignmentIds)
      ;(hwSubs || []).forEach((sub) => {
        const studentId = assignmentToStudent[sub.assignment_id]
        if (!studentId) return
        submissionCountByStudent[studentId] = (submissionCountByStudent[studentId] || 0) + 1
      })
    }

    const { data: offTopicMsgs } = await supabaseAdmin
      .from('chat_messages')
      .select('student_user_id, meta')
      .in('student_user_id', studentIds)
      .eq('role', 'assistant')
      .gte('created_at', sevenDaysAgo.toISOString())
      .filter('meta->>is_study', 'eq', 'false')

    const offTopicCountByStudent: Record<string, number> = {}
    ;(offTopicMsgs || []).forEach((m) => {
      offTopicCountByStudent[m.student_user_id] = (offTopicCountByStudent[m.student_user_id] || 0) + 1
    })

    const studentMetrics = (students || []).map((student) => {
      const correctRateValue = correctRate(itemsByStudent[student.id])

      const assignmentCount = assignmentCountByStudent[student.id] || 0
      const submissionRate = assignmentCount > 0
        ? Math.round(((submissionCountByStudent[student.id] || 0) / assignmentCount) * 100)
        : 0

      const offTopicCount = offTopicCountByStudent[student.id] || 0

      const wrongRate = 100 - correctRateValue
      const riskScore = Math.round(wrongRate * 0.6 + (100 - submissionRate) * 0.4)

      return {
        id: student.id,
        handle: student.handle,
        status: student.status,
        correctRate: correctRateValue,
        submissionRate,
        offTopicCount,
        riskScore,
        atRisk: riskScore >= 50,
      }
    })

    const atRiskCount = studentMetrics.filter((s) => s.atRisk).length
    const avgCorrectRate =
      studentMetrics.length > 0
        ? Math.round(studentMetrics.reduce((sum, s) => sum + s.correctRate, 0) / studentMetrics.length)
        : 0
    const avgSubmissionRate =
      studentMetrics.length > 0
        ? Math.round(studentMetrics.reduce((sum, s) => sum + s.submissionRate, 0) / studentMetrics.length)
        : 0

    return NextResponse.json({
      ok: true,
      classData: { totalCount: studentMetrics.length, atRiskCount, avgCorrectRate, avgSubmissionRate, students: studentMetrics },
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Class summary error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
