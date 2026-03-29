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
      .select('quiz_data, student_user_id')
      .eq('id', quizId)
      .single()

    if (!quiz || quiz.student_user_id !== session.id) {
      return NextResponse.json({ ok: false, error: '퀴즈를 찾을 수 없습니다.' }, { status: 404 })
    }

    const isCorrect = quiz.quiz_data?.correct_index === selectedChoice

    await supabaseAdmin.from('concept_review_attempts').insert({
      quiz_id: quizId,
      student_user_id: session.id,
      selected_choice: selectedChoice,
      is_correct: isCorrect,
      created_at: new Date().toISOString(),
    })

    return NextResponse.json({
      ok: true,
      isCorrect,
      correctIndex: quiz.quiz_data?.correct_index,
      explanation: quiz.quiz_data?.explanation || '',
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Quiz attempt error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
