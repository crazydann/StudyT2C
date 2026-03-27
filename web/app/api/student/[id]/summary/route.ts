export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = requireSessionFromRequest(request, ['teacher', 'parent', 'student'])
    const studentId = params.id

    // Students can only view their own summary
    if (session.role === 'student' && session.id !== studentId) {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }

    // Get student info
    const { data: student } = await supabaseAdmin
      .from('users')
      .select('id, handle, role, status')
      .eq('id', studentId)
      .single()

    // Get recent problem submissions (last 30 days)
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    const { data: submissions } = await supabaseAdmin
      .from('problem_submissions')
      .select('id, created_at')
      .eq('student_user_id', studentId)
      .gte('created_at', thirtyDaysAgo.toISOString())
      .order('created_at', { ascending: false })

    // Get problem items for correct rate and weak concepts
    const submissionIds = (submissions || []).map((s) => s.id)
    let correctRate = 0
    let weakConcepts: string[] = []

    if (submissionIds.length > 0) {
      const { data: items } = await supabaseAdmin
        .from('problem_items')
        .select('is_correct, key_concepts, reason_category')
        .in('submission_id', submissionIds)

      if (items && items.length > 0) {
        const correct = items.filter((i) => i.is_correct).length
        correctRate = Math.round((correct / items.length) * 100)

        // Get weak concepts from wrong answers
        const wrongItems = items.filter((i) => !i.is_correct)
        const conceptCounts: Record<string, number> = {}
        wrongItems.forEach((item) => {
          (item.key_concepts || []).forEach((concept: string) => {
            conceptCounts[concept] = (conceptCounts[concept] || 0) + 1
          })
        })

        weakConcepts = Object.entries(conceptCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([concept]) => concept)
      }
    }

    // Get homework rate
    const { data: assignments } = await supabaseAdmin
      .from('homework_assignments')
      .select('id')
      .eq('student_user_id', studentId)

    let homeworkRate = 0
    if (assignments && assignments.length > 0) {
      const { data: hwSubmissions } = await supabaseAdmin
        .from('homework_submissions')
        .select('assignment_id')
        .eq('student_user_id', studentId)
        .in('assignment_id', assignments.map((a) => a.id))

      homeworkRate = Math.round(((hwSubmissions?.length || 0) / assignments.length) * 100)
    }

    // Get chat count (last 7 days)
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    const { count: chatCount } = await supabaseAdmin
      .from('chat_messages')
      .select('*', { count: 'exact', head: true })
      .eq('student_user_id', studentId)
      .eq('role', 'user')
      .gte('created_at', sevenDaysAgo.toISOString())

    return NextResponse.json({
      ok: true,
      summary: {
        student,
        recentSubmissions: submissions || [],
        weakConcepts,
        homeworkRate,
        chatCount: chatCount || 0,
        correctRate,
      },
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Summary error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
