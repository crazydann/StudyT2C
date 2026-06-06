export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { scheduleNext } from '@/lib/review'

// GET /api/student/review — 오늘 복습할 문항(next_review_at <= now)
// next_review_at 컬럼이 아직 없으면 빈 큐로 graceful 처리
export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const nowIso = new Date().toISOString()

    const { data, error } = await supabaseAdmin
      .from('problem_items')
      .select('id, item_no, explanation_summary, key_concepts, reason_category, next_review_at')
      .eq('student_user_id', session.id)
      .lte('next_review_at', nowIso)
      .order('next_review_at', { ascending: true })
      .limit(20)

    if (error) {
      // 컬럼 미적용 등 → 복습 기능 비활성으로 간주
      return NextResponse.json({ ok: true, reviews: [] })
    }

    return NextResponse.json({ ok: true, reviews: data || [] })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Review GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}

// POST /api/student/review — 복습 결과 기록 → 다음 복습 시점 갱신
export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const { problemItemId, isCorrect } = await request.json()

    if (!problemItemId || typeof isCorrect !== 'boolean') {
      return NextResponse.json({ ok: false, error: '입력이 올바르지 않습니다.' }, { status: 400 })
    }

    // fsrs_state 컬럼이 없는 환경(마이그레이션 미적용)에서도 동작하도록 graceful 처리
    let ownerId: string | undefined
    let prevState: unknown = null
    const { data: item, error: selErr } = await supabaseAdmin
      .from('problem_items')
      .select('id, student_user_id, fsrs_state')
      .eq('id', problemItemId)
      .maybeSingle()

    if (selErr) {
      // fsrs_state 컬럼이 없을 수 있음 → 컬럼 없이 소유권만 재확인
      const { data: basic } = await supabaseAdmin
        .from('problem_items')
        .select('id, student_user_id')
        .eq('id', problemItemId)
        .maybeSingle()
      ownerId = basic?.student_user_id
    } else {
      ownerId = item?.student_user_id
      prevState = item?.fsrs_state
    }

    if (!ownerId || ownerId !== session.id) {
      return NextResponse.json({ ok: false, error: '문항을 찾을 수 없습니다.' }, { status: 404 })
    }

    const { nextReviewAt, state } = scheduleNext(prevState, isCorrect)

    // fsrs_state 포함 갱신 → 컬럼이 없으면 next_review_at 만이라도 갱신
    let { error } = await supabaseAdmin
      .from('problem_items')
      .update({ next_review_at: nextReviewAt, fsrs_state: state })
      .eq('id', problemItemId)

    if (error) {
      const retry = await supabaseAdmin
        .from('problem_items')
        .update({ next_review_at: nextReviewAt })
        .eq('id', problemItemId)
      error = retry.error
    }

    if (error) {
      console.error('Review update error:', error.message)
      return NextResponse.json({ ok: false, error: '복습 결과 저장에 실패했습니다.' }, { status: 500 })
    }

    return NextResponse.json({ ok: true, nextReviewAt })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Review POST error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
