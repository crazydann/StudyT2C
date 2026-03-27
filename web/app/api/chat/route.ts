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

    // Get student's current mode
    const { data: studentRow } = await supabaseAdmin
      .from('users')
      .select('status')
      .eq('id', targetStudentId)
      .single()

    const mode = studentRow?.status === 'studying' ? 'studying' : 'break'

    // Save user message
    const { error: insertError } = await supabaseAdmin
      .from('chat_messages')
      .insert({
        student_user_id: targetStudentId,
        role: 'user',
        content: message.trim(),
        meta: { mode },
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

    // Get AI response with mode-aware system prompt
    const { reply, isStudy, offTopicCategory } = await textChat(historyMessages, mode)

    // Save assistant response with study metadata
    const { error: replyError } = await supabaseAdmin
      .from('chat_messages')
      .insert({
        student_user_id: targetStudentId,
        role: 'assistant',
        content: reply,
        meta: { mode, is_study: isStudy, offtopic_category: offTopicCategory || null },
      })

    if (replyError) throw replyError

    return NextResponse.json({ ok: true, reply, isStudy, mode })
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
