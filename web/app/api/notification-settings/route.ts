export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['parent', 'teacher'])
    const { searchParams } = new URL(request.url)
    const studentId = searchParams.get('studentId')

    if (!studentId) {
      return NextResponse.json({ ok: false, error: '학생 ID가 필요합니다.' }, { status: 400 })
    }

    const { data } = await supabaseAdmin
      .from('notification_settings')
      .select('*')
      .eq('user_id', session.id)
      .eq('student_user_id', studentId)
      .single()

    return NextResponse.json({ ok: true, settings: data || null })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    return NextResponse.json({ ok: true, settings: null })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['parent', 'teacher'])
    const { studentId, email, emailEnabled, receiveWeeklyReport, receiveOfftopic } = await request.json()

    if (!studentId) {
      return NextResponse.json({ ok: false, error: '학생 ID가 필요합니다.' }, { status: 400 })
    }

    const { error } = await supabaseAdmin
      .from('notification_settings')
      .upsert(
        {
          user_id: session.id,
          student_user_id: studentId,
          role: session.role,
          email: email || '',
          email_enabled: emailEnabled ?? false,
          receive_weekly_report: receiveWeeklyReport ?? false,
          receive_offtopic: receiveOfftopic ?? false,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'user_id,student_user_id' }
      )

    if (error) throw error

    return NextResponse.json({ ok: true })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Notification settings POST error:', err)
    return NextResponse.json({ ok: false, error: '저장 실패' }, { status: 500 })
  }
}
