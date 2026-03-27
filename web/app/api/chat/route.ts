export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { textChat } from '@/lib/openai'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const { searchParams } = new URL(request.url)
    const studentId = searchParams.get('studentId') || session.id

    // Only allow students to see their own messages, or teachers/parents can see student messages
    const { data: messages, error } = await supabaseAdmin
      .from('chat_messages')
      .select('*')
      .eq('student_user_id', studentId)
      .order('created_at', { ascending: true })
      .limit(50)

    if (error) throw error

    return NextResponse.json({ ok: true, messages })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    console.error('Chat GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const { message, studentId } = await request.json()

    if (!message?.trim()) {
      return NextResponse.json({ ok: false, error: '메시지를 입력해주세요.' }, { status: 400 })
    }

    const targetStudentId = studentId || session.id

    // Save user message
    const { error: insertError } = await supabaseAdmin
      .from('chat_messages')
      .insert({
        student_user_id: targetStudentId,
        role: 'user',
        content: message.trim(),
        meta: {},
      })

    if (insertError) throw insertError

    // Get recent chat history for context (last 10 messages)
    const { data: history } = await supabaseAdmin
      .from('chat_messages')
      .select('role, content')
      .eq('student_user_id', targetStudentId)
      .order('created_at', { ascending: false })
      .limit(10)

    const historyMessages = (history || [])
      .reverse()
      .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    // Get AI response
    const reply = await textChat(historyMessages)

    // Save assistant response
    const { error: replyError } = await supabaseAdmin
      .from('chat_messages')
      .insert({
        student_user_id: targetStudentId,
        role: 'assistant',
        content: reply,
        meta: {},
      })

    if (replyError) throw replyError

    return NextResponse.json({ ok: true, reply })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Chat POST error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
