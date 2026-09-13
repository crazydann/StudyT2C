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

    if (session.role === 'student' && session.id !== studentId) {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }

    if (session.role === 'parent' || session.role === 'teacher') {
      const linkTable = session.role === 'teacher' ? 'teacher_student_links' : 'parent_student_links'
      const ownerCol = session.role === 'teacher' ? 'teacher_user_id' : 'parent_user_id'
      const { data: link } = await supabaseAdmin
        .from(linkTable)
        .select('student_user_id')
        .eq(ownerCol, session.id)
        .eq('student_user_id', studentId)
        .maybeSingle()
      if (!link) return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }

    // Get recent submissions
    const { data: submissions, error: subError } = await supabaseAdmin
      .from('problem_submissions')
      .select('*')
      .eq('student_user_id', studentId)
      .order('created_at', { ascending: false })
      .limit(10)

    if (subError) throw subError

    if (!submissions || submissions.length === 0) {
      return NextResponse.json({ ok: true, submissions: [] })
    }

    // Get problem items for each submission
    const submissionIds = submissions.map((s) => s.id)
    const { data: items, error: itemsError } = await supabaseAdmin
      .from('problem_items')
      .select('*')
      .in('submission_id', submissionIds)
      .order('item_no', { ascending: true })

    if (itemsError) throw itemsError

    const itemsBySubmission = new Map<string, typeof items>()
    ;(items || []).forEach((item) => {
      const existing = itemsBySubmission.get(item.submission_id) || []
      existing.push(item)
      itemsBySubmission.set(item.submission_id, existing)
    })

    const result = submissions.map((sub) => {
      const subItems = itemsBySubmission.get(sub.id) || []
      const total = subItems.length
      const correct = subItems.filter((i) => i.is_correct).length
      return {
        ...sub,
        items: subItems,
        stats: {
          total,
          correct,
          wrong: total - correct,
          rate: total > 0 ? Math.round((correct / total) * 100) : 0,
        },
      }
    })

    return NextResponse.json({ ok: true, submissions: result })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Grading GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
