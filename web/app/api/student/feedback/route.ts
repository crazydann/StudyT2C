export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { REASON_LABELS } from '@/lib/reasons'

const UNDERSTANDING = ['understood', 'confused']
const REASONS = Object.keys(REASON_LABELS)

// GET /api/student/feedback?submissionId=...  — 해당 채점의 기존 자기평가 로드
export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const submissionId = new URL(request.url).searchParams.get('submissionId')
    if (!submissionId) {
      return NextResponse.json({ ok: false, error: 'submissionId가 필요합니다.' }, { status: 400 })
    }

    const { data } = await supabaseAdmin
      .from('problem_item_feedback')
      .select('problem_item_id, understanding, reason_category')
      .eq('student_user_id', session.id)
      .eq('submission_id', submissionId)

    const byItem: Record<string, { understanding: string; reason_category: string | null }> = {}
    ;(data || []).forEach((r) => {
      byItem[r.problem_item_id] = {
        understanding: r.understanding,
        reason_category: r.reason_category ?? null,
      }
    })

    return NextResponse.json({ ok: true, feedback: byItem })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Feedback GET error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}

// POST /api/student/feedback  — 문항별 자기평가 저장(upsert)
export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const body = await request.json()
    const { problemItemId, submissionId, understanding, reasonCategory } = body

    if (!problemItemId || !UNDERSTANDING.includes(understanding)) {
      return NextResponse.json({ ok: false, error: '입력이 올바르지 않습니다.' }, { status: 400 })
    }
    const reason = REASONS.includes(reasonCategory) ? reasonCategory : null

    const { error } = await supabaseAdmin.from('problem_item_feedback').upsert(
      {
        student_user_id: session.id,
        problem_item_id: problemItemId,
        submission_id: submissionId || null,
        understanding,
        reason_category: reason,
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'student_user_id,problem_item_id' },
    )

    if (error) {
      console.error('Feedback upsert error:', error.message)
      return NextResponse.json({ ok: false, error: '저장에 실패했습니다.' }, { status: 500 })
    }

    return NextResponse.json({ ok: true })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Feedback POST error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
