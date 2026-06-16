export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = requireSessionFromRequest(request, ['teacher'])
    const studentId = params.id

    const { data: note, error } = await supabaseAdmin
      .from('teacher_student_notes')
      .select('*')
      .eq('teacher_user_id', session.id)
      .eq('student_user_id', studentId)
      .single()

    if (error && error.code !== 'PGRST116') throw error

    return NextResponse.json({ ok: true, note: note || null })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Notes GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = requireSessionFromRequest(request, ['teacher'])
    const studentId = params.id
    const { note } = await request.json()

    if (typeof note !== 'string') {
      return NextResponse.json({ ok: false, error: '노트 내용을 입력해주세요.' }, { status: 400 })
    }
    if (note.length > 10000) {
      return NextResponse.json({ ok: false, error: '노트가 너무 깁니다 (최대 10,000자).' }, { status: 400 })
    }

    const { error } = await supabaseAdmin
      .from('teacher_student_notes')
      .upsert(
        {
          teacher_user_id: session.id,
          student_user_id: studentId,
          note,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'teacher_user_id,student_user_id' }
      )

    if (error) throw error

    return NextResponse.json({ ok: true })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Notes POST error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
