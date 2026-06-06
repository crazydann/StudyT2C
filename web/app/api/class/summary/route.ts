export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

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

    const studentMetrics = await Promise.all(
      (students || []).map(async (student) => {
        // Correct rate (30 days)
        const { data: submissions } = await supabaseAdmin
          .from('problem_submissions')
          .select('id')
          .eq('student_user_id', student.id)
          .gte('created_at', thirtyDaysAgo.toISOString())

        let correctRate = 0
        if (submissions && submissions.length > 0) {
          const { data: items } = await supabaseAdmin
            .from('problem_items')
            .select('is_correct')
            .in('submission_id', submissions.map((s) => s.id))
          if (items && items.length > 0) {
            correctRate = Math.round((items.filter((i) => i.is_correct).length / items.length) * 100)
          }
        }

        // Homework submission rate (14 days)
        const { data: assignments } = await supabaseAdmin
          .from('homework_assignments')
          .select('id')
          .eq('student_user_id', student.id)
          .gte('created_at', fourteenDaysAgo.toISOString())

        let submissionRate = 0
        if (assignments && assignments.length > 0) {
          const { data: hwSubs } = await supabaseAdmin
            .from('homework_submissions')
            .select('assignment_id')
            .eq('student_user_id', student.id)
            .in('assignment_id', assignments.map((a) => a.id))
          submissionRate = Math.round(((hwSubs?.length || 0) / assignments.length) * 100)
        }

        // Off-topic count (7 days)
        const { count: offTopicCount } = await supabaseAdmin
          .from('chat_messages')
          .select('*', { count: 'exact', head: true })
          .eq('student_user_id', student.id)
          .eq('role', 'assistant')
          .gte('created_at', sevenDaysAgo.toISOString())
          .filter('meta->>is_study', 'eq', 'false')

        const wrongRate = 100 - correctRate
        const riskScore = Math.round(wrongRate * 0.6 + (100 - submissionRate) * 0.4)

        return {
          id: student.id,
          handle: student.handle,
          status: student.status,
          correctRate,
          submissionRate,
          offTopicCount: offTopicCount || 0,
          riskScore,
          atRisk: riskScore >= 50,
        }
      })
    )

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
