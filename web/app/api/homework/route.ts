export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request)
    const { searchParams } = new URL(request.url)
    const studentId = searchParams.get('studentId') || session.id

    // Get homework assignments for the student
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

    // Get submissions
    const { data: submissions } = await supabaseAdmin
      .from('homework_submissions')
      .select('*')
      .eq('student_user_id', studentId)
      .in('assignment_id', assignmentIds)

    // Get non-submit reasons
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

    if (reason_code) {
      // Submit non-submit reason
      const { error } = await supabaseAdmin
        .from('homework_non_submit_reasons')
        .upsert({
          student_user_id: session.id,
          assignment_id,
          reason_code,
        })

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
