export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { textChat } from '@/lib/openai'
import { checkRateLimit } from '@/lib/ratelimit'
import { validateImageUpload, MAX_UPLOAD_BYTES } from '@/lib/upload'

// 20 messages per minute per user
const CHAT_RATE_LIMIT = { max: 20, windowMs: 60 * 1000 }

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    // Students can only read their own chat history
    const { data: messages, error } = await supabaseAdmin
      .from('chat_messages')
      .select('*')
      .eq('student_user_id', session.id)
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

    if (!checkRateLimit(`chat:${session.id}`, CHAT_RATE_LIMIT.max, CHAT_RATE_LIMIT.windowMs)) {
      return NextResponse.json({ ok: false, error: '너무 많은 요청입니다. 잠시 후 다시 시도해주세요.' }, { status: 429 })
    }

    let message: string
    let imageBase64: string | undefined
    let imageMimeType: string | undefined

    const contentType = request.headers.get('content-type') || ''
    if (contentType.includes('multipart/form-data')) {
      const formData = await request.formData()
      message = (formData.get('message') as string) || ''
      const file = formData.get('image') as File | null
      if (file) {
        const buffer = Buffer.from(await file.arrayBuffer())
        const validationError = validateImageUpload(file, buffer)
        if (validationError) {
          return NextResponse.json({ ok: false, error: validationError }, { status: 400 })
        }
        imageBase64 = buffer.toString('base64')
        imageMimeType = file.type
      }
    } else {
      const body = await request.json()
      message = body.message
    }

    if (!message?.trim()) {
      return NextResponse.json({ ok: false, error: '메시지를 입력해주세요.' }, { status: 400 })
    }
    if (message.length > 2000) {
      return NextResponse.json({ ok: false, error: '메시지가 너무 깁니다 (최대 2,000자).' }, { status: 400 })
    }

    // Always use the authenticated student's own ID — never trust client-provided studentId
    const targetStudentId = session.id

    const { data: studentRow } = await supabaseAdmin
      .from('users')
      .select('status')
      .eq('id', targetStudentId)
      .single()

    const mode = studentRow?.status === 'studying' ? 'studying' : 'break'

    const { error: insertError } = await supabaseAdmin
      .from('chat_messages')
      .insert({
        student_user_id: targetStudentId,
        role: 'user',
        content: message.trim(),
        meta: { mode, has_image: !!imageBase64 },
      })

    if (insertError) throw insertError

    const { data: history } = await supabaseAdmin
      .from('chat_messages')
      .select('role, content')
      .eq('student_user_id', targetStudentId)
      .order('created_at', { ascending: false })
      .limit(10)

    const historyMessages = (history || [])
      .reverse()
      .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    const { reply, isStudy, offTopicCategory } = await textChat(
      historyMessages,
      mode,
      imageBase64 ? { base64: imageBase64, mimeType: imageMimeType || 'image/jpeg' } : undefined,
    )

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
