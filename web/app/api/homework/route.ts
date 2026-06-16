export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student', 'teacher', 'parent'])
    const { searchParams } = new URL(request.url)
    const requestedId = searchParams.get('studentId')

    // Students can only read their own homework
    if (session.role === 'student') {
      if (requestedId && requestedId !== session.id) {
        return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
      }
    }

    const studentId = session.role === 'student' ? session.id : (requestedId || session.id)

    // Teacher/parent must have a verified link to the requested student
    if ((session.role === 'teacher' || session.role === 'parent') && requestedId) {
      const linkTable = session.role === 'teacher' ? 'teacher_student_links' : 'parent_student_links'
      const ownerCol = session.role === 'teacher' ? 'teacher_user_id' : 'parent_user_id'
      const { data: link } = await supabaseAdmin
        .from(linkTable)
        .select('student_user_id')
        .eq(ownerCol, session.id)
        .eq('student_user_id', studentId)
        .maybeSingle()
      if (!link) {
        return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
      }
    }

    const { data: assignments, error: assignError } = await supabaseAdmin
      .from('homework_assignments')
      .select('*')
      .eq('student_user_id', studentId)
      .order('created_at', { ascending: false })

    if (assignError) throw assignError

    if (!assignments || assignments.length === 0) {
      return NextResponse.json({ ok: true, homework: [] })
    }

    const assignmentIds = assignments.map((a) => a.id)

    const { data: submissions } = await supabaseAdmin
      .from('homework_submissions')
      .select('*')
      .eq('student_user_id', studentId)
      .in('assignment_id', assignmentIds)

    const { data: nonSubmitReasons } = await supabaseAdmin
      .from('homework_non_submit_reasons')
      .select('*')
      .eq('student_user_id', studentId)
      .in('assignment_id', assignmentIds)

    const submissionMap = new Map((submissions || []).map((s) => [s.assignment_id, s]))
    const nonSubmitMap = new Map((nonSubmitReasons || []).map((r) => [r.assignment_id, r]))

    const homework = assignments.map((a) => ({
      ...a,
      submission: submissionMap.get(a.id) || null,
      non_submit_reason: nonSubmitMap.get(a.id) || null,
    }))

    return NextResponse.json({ ok: true, homework })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Homework GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const body = await request.json()
    const { assignment_id, reason_code } = body

    if (!assignment_id) {
      return NextResponse.json({ ok: false, error: '과제 ID가 필요합니다.' }, { status: 400 })
    }

    // Verify this assignment belongs to the calling student
    const { data: assignment } = await supabaseAdmin
      .from('homework_assignments')
      .select('student_user_id')
      .eq('id', assignment_id)
      .maybeSingle()

    if (!assignment || assignment.student_user_id !== session.id) {
      return NextResponse.json({ ok: false, error: '과제를 찾을 수 없습니다.' }, { status: 404 })
    }

    if (reason_code) {
      const VALID_REASONS = ['forgot', 'time', 'hard']
      if (!VALID_REASONS.includes(reason_code)) {
        return NextResponse.json({ ok: false, error: '잘못된 미제출 사유입니다.' }, { status: 400 })
      }
      const { error } = await supabaseAdmin
        .from('homework_non_submit_reasons')
        .upsert({ student_user_id: session.id, assignment_id, reason_code })

      if (error) throw error
    }

    return NextResponse.json({ ok: true })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    console.error('Homework POST error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
