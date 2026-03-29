export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])

    const { data: quizzes } = await supabaseAdmin
      .from('concept_review_quizzes')
      .select('id, quiz_data, created_at')
      .eq('student_user_id', session.id)
      .order('created_at', { ascending: false })
      .limit(10)

    if (!quizzes || quizzes.length === 0) {
      return NextResponse.json({ ok: true, quizzes: [] })
    }

    const quizIds = quizzes.map((q) => q.id)

    // Get latest attempt per quiz
    const { data: attempts } = await supabaseAdmin
      .from('concept_review_attempts')
      .select('quiz_id, is_correct, created_at')
      .eq('student_user_id', session.id)
      .in('quiz_id', quizIds)
      .order('created_at', { ascending: false })

    const latestAttemptByQuiz: Record<string, { is_correct: boolean; created_at: string }> = {}
    for (const attempt of attempts || []) {
      if (!latestAttemptByQuiz[attempt.quiz_id]) {
        latestAttemptByQuiz[attempt.quiz_id] = { is_correct: attempt.is_correct, created_at: attempt.created_at }
      }
    }

    const result = quizzes.map((q) => ({
      id: q.id,
      concept: q.quiz_data?.concept || '개념',
      question: q.quiz_data?.question || '',
      choices: q.quiz_data?.choices || [],
      correct_index: q.quiz_data?.correct_index ?? 0,
      explanation: q.quiz_data?.explanation || '',
      created_at: q.created_at,
      lastAttempt: latestAttemptByQuiz[q.id] || null,
    }))

    return NextResponse.json({ ok: true, quizzes: result })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Quiz list error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
