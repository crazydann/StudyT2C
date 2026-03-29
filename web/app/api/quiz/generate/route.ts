export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import OpenAI from 'openai'

let _openai: OpenAI | null = null
function getOpenAI() {
  if (!_openai) _openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || 'placeholder' })
  return _openai
}

export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])

    // Get recent chat messages (last 20) for quiz generation
    const { data: msgs } = await supabaseAdmin
      .from('chat_messages')
      .select('id, role, content')
      .eq('student_user_id', session.id)
      .order('created_at', { ascending: false })
      .limit(20)

    if (!msgs || msgs.length < 2) {
      return NextResponse.json({ ok: false, error: '퀴즈를 생성하려면 먼저 AI 튜터와 대화해 보세요.' }, { status: 400 })
    }

    const conversation = msgs
      .reverse()
      .map((m) => `${m.role === 'user' ? '학생' : 'AI'}: ${m.content}`)
      .join('\n')

    const messageIds = msgs.map((m) => m.id)

    const QUIZ_PROMPT = `다음은 학생과 AI 튜터의 학습 대화입니다. 이 대화의 핵심 개념을 바탕으로 5지선다 복습 문제를 1개 만들어주세요.

대화:
${conversation}

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "concept": "핵심 개념 (예: 이차방정식, 광합성, 현재완료)",
  "question": "문제 내용",
  "choices": ["선택지1", "선택지2", "선택지3", "선택지4", "선택지5"],
  "correct_index": 0,
  "explanation": "정답 해설"
}`

    const response = await getOpenAI().chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: QUIZ_PROMPT }],
      max_tokens: 800,
      temperature: 0.7,
    })

    const raw = response.choices[0]?.message?.content ?? '{}'
    let quizData
    try {
      const cleaned = raw.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim()
      quizData = JSON.parse(cleaned)
    } catch {
      return NextResponse.json({ ok: false, error: '퀴즈 생성에 실패했습니다.' }, { status: 500 })
    }

    const { data: saved, error } = await supabaseAdmin
      .from('concept_review_quizzes')
      .insert({
        student_user_id: session.id,
        quiz_data: quizData,
        source_message_ids: messageIds,
        created_at: new Date().toISOString(),
      })
      .select('id')
      .single()

    if (error) throw error

    return NextResponse.json({ ok: true, quiz: { id: saved.id, ...quizData } })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Quiz generate error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
