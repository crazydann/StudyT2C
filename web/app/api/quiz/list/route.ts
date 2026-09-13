export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])

    const { data: quizzes } = await supabaseAdmin
      .from('concept_review_quizzes')
      .select('id, quiz_question, options, correct_index, created_at')
      .eq('student_user_id', session.id)
      .order('created_at', { ascending: false })
      .limit(10)

    if (!quizzes || quizzes.length === 0) {
      return NextResponse.json({ ok: true, quizzes: [] })
    }

    // 최근 시도 결과 매핑: quiz_id 우선(정확), 컬럼 미적용/구 데이터는 quiz_question 텍스트로 폴백
    let { data: attempts } = await supabaseAdmin
      .from('concept_review_attempts')
      .select('quiz_id, quiz_question, is_correct, created_at')
      .eq('student_user_id', session.id)
      .order('created_at', { ascending: false })
    if (!attempts) {
      const retry = await supabaseAdmin
        .from('concept_review_attempts')
        .select('quiz_question, is_correct, created_at')
        .eq('student_user_id', session.id)
        .order('created_at', { ascending: false })
      attempts = retry.data as typeof attempts
    }

    const latestByQuizId: Record<string, { is_correct: boolean }> = {}
    const latestByQuestion: Record<string, { is_correct: boolean }> = {}
    for (const a of attempts || []) {
      const row = a as { quiz_id?: string | null; quiz_question?: string; is_correct: boolean }
      if (row.quiz_id && !latestByQuizId[row.quiz_id]) {
        latestByQuizId[row.quiz_id] = { is_correct: row.is_correct }
      }
      if (row.quiz_question && !latestByQuestion[row.quiz_question]) {
        latestByQuestion[row.quiz_question] = { is_correct: row.is_correct }
      }
    }

    const result = quizzes.map((q) => {
      const opts = (q.options || {}) as { choices?: string[]; concept?: string; explanation?: string }
      return {
        id: q.id,
        concept: opts.concept || q.quiz_question?.slice(0, 20) || '개념',
        question: q.quiz_question || '',
        choices: Array.isArray(opts.choices) ? opts.choices : Array.isArray(q.options) ? (q.options as string[]) : [],
        correct_index: q.correct_index ?? 0,
        explanation: opts.explanation || '',
        created_at: q.created_at,
        lastAttempt: latestByQuizId[q.id] || (q.quiz_question ? latestByQuestion[q.quiz_question] || null : null),
      }
    })

    return NextResponse.json({ ok: true, quizzes: result })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Quiz list error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
