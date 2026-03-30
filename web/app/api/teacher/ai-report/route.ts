export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import OpenAI from 'openai'

let _openai: OpenAI | null = null
function getOpenAI(): OpenAI {
  if (!_openai) {
    _openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || 'placeholder' })
  }
  return _openai
}

export async function POST(request: NextRequest) {
  try {
    requireSessionFromRequest(request, ['teacher'])

    const body = await request.json()
    const { studentId } = body as { studentId: string }
    if (!studentId) {
      return NextResponse.json({ ok: false, error: 'studentId가 필요합니다.' }, { status: 400 })
    }

    const now = new Date()
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

    // 1. Fetch student handle
    const { data: student, error: studentError } = await supabaseAdmin
      .from('users')
      .select('id, handle')
      .eq('id', studentId)
      .single()

    if (studentError || !student) {
      return NextResponse.json({ ok: false, error: '학생을 찾을 수 없습니다.' }, { status: 404 })
    }

    // 2. Fetch problem_items last 7 days
    const { data: items } = await supabaseAdmin
      .from('problem_items')
      .select('is_correct, key_concepts, reason_category')
      .eq('student_user_id', studentId)
      .gte('created_at', sevenDaysAgo.toISOString())

    const totalProblems = (items || []).length
    let correctRate = 0
    const conceptCounts: Record<string, number> = {}

    if (totalProblems > 0) {
      const correct = (items || []).filter((i) => i.is_correct).length
      correctRate = Math.round((correct / totalProblems) * 100)

      const wrongItems = (items || []).filter((i) => !i.is_correct)
      wrongItems.forEach((item) => {
        ;(item.key_concepts || []).forEach((c: string) => {
          conceptCounts[c] = (conceptCounts[c] || 0) + 1
        })
      })
    }

    const weakConcepts = Object.entries(conceptCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([c]) => c)

    const conceptsStr = weakConcepts.length > 0 ? weakConcepts.join(', ') : '없음'

    // 3. Fetch chat messages last 7 days
    const { data: chatMsgs } = await supabaseAdmin
      .from('chat_messages')
      .select('meta')
      .eq('student_user_id', studentId)
      .eq('role', 'user')
      .gte('created_at', sevenDaysAgo.toISOString())

    const totalChats = (chatMsgs || []).length
    const offTopicChats = (chatMsgs || []).filter((m) => m.meta?.is_study === false).length

    // 4. Fetch homework submissions last 7 days
    const { data: hwSubs } = await supabaseAdmin
      .from('homework_submissions')
      .select('id')
      .eq('student_user_id', studentId)
      .gte('created_at', sevenDaysAgo.toISOString())

    const hwCount = (hwSubs || []).length

    // 5. Call OpenAI
    const prompt = `학생 ${student.handle}의 이번 주 학습 리포트를 작성해주세요.

데이터:
- 채점 문제: ${totalProblems}개, 정답률: ${correctRate}%
- 주요 보완 개념: ${conceptsStr}
- AI 튜터 대화: ${totalChats}회 (비학습 ${offTopicChats}회)
- 숙제 제출: ${hwCount}건

다음 형식으로 학부모가 읽기 쉽게 200자 이내로 작성하세요:
[이번 주 총평 1-2문장]
[잘한 점 1가지]
[개선 필요 1가지]
[다음 주 추천 학습 방향 1가지]`

    const completion = await getOpenAI().chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 500,
      temperature: 0.7,
    })

    const report = completion.choices[0]?.message?.content ?? '리포트를 생성하지 못했습니다.'

    return NextResponse.json({ ok: true, report, generatedAt: now.toISOString() })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('AI report error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
