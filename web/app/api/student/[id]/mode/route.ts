export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

// PATCH /api/student/[id]/mode — parent or teacher sets studying/break mode
// Access control: caller must have a verified link to the target student
export async function PATCH(request: NextRequest, { params }: { params: { id: string } }) {
  try {
    const session = requireSessionFromRequest(request, ['parent', 'teacher'])
    const studentId = params.id

    // Verify the caller is linked to this specific student
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

    const { status } = await request.json()
    if (!['studying', 'break'].includes(status)) {
      return NextResponse.json({ ok: false, error: '잘못된 상태값' }, { status: 400 })
    }

    const { error } = await supabaseAdmin.from('users').update({ status }).eq('id', studentId)
    if (error) throw error

    return NextResponse.json({ ok: true, status })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false }, { status: 403 })
    }
    console.error('Mode PATCH error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
