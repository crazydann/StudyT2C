export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const { quizId, selectedChoice } = await request.json()

    if (!quizId || selectedChoice === undefined) {
      return NextResponse.json({ ok: false, error: '퀴즈 ID와 선택 번호가 필요합니다.' }, { status: 400 })
    }

    const { data: quiz } = await supabaseAdmin
      .from('concept_review_quizzes')
      .select('quiz_question, options, correct_index, student_user_id')
      .eq('id', quizId)
      .single()

    if (!quiz || quiz.student_user_id !== session.id) {
      return NextResponse.json({ ok: false, error: '퀴즈를 찾을 수 없습니다.' }, { status: 404 })
    }

    const opts = (quiz.options || {}) as { concept?: string; explanation?: string }
    const correctIndex = quiz.correct_index ?? 0
    const isCorrect = correctIndex === selectedChoice

    // 실제 스키마에 맞게 저장 (quiz_id 컬럼 없음 → quiz_question으로 매칭)
    await supabaseAdmin.from('concept_review_attempts').insert({
      student_user_id: session.id,
      source_question: opts.concept || null,
      quiz_question: quiz.quiz_question,
      correct_index: correctIndex,
      user_choice_index: selectedChoice,
      is_correct: isCorrect,
    })

    return NextResponse.json({
      ok: true,
      isCorrect,
      correctIndex,
      explanation: opts.explanation || '',
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Quiz attempt error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
