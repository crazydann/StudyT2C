export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['teacher', 'parent'])

    let studentIds: string[] = []

    if (session.role === 'teacher') {
      const { data: links, error } = await supabaseAdmin
        .from('teacher_student_links')
        .select('student_user_id')
        .eq('teacher_user_id', session.id)

      if (error) throw error
      studentIds = (links || []).map((l) => l.student_user_id)
    } else if (session.role === 'parent') {
      const { data: links, error } = await supabaseAdmin
        .from('parent_student_links')
        .select('student_user_id')
        .eq('parent_user_id', session.id)

      if (error) throw error
      studentIds = (links || []).map((l) => l.student_user_id)
    }

    if (studentIds.length === 0) {
      return NextResponse.json({ ok: true, students: [] })
    }

    const { data: students, error: studentsError } = await supabaseAdmin
      .from('users')
      .select('id, handle, role, status')
      .in('id', studentIds)
      .eq('role', 'student')

    if (studentsError) throw studentsError

    return NextResponse.json({ ok: true, students: students || [] })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Students GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
