export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { correctRate } from '@/lib/stats'

export async function GET(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])

    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    // Get recent submissions
    const { data: submissions } = await supabaseAdmin
      .from('problem_submissions')
      .select('id')
      .eq('student_user_id', session.id)
      .gte('created_at', thirtyDaysAgo.toISOString())

    if (!submissions || submissions.length === 0) {
      return NextResponse.json({ ok: true, snapshot: { strongConcepts: [], weakConcepts: [], totalProblems: 0, correctRate: 0 } })
    }

    const submissionIds = submissions.map((s) => s.id)

    const { data: items } = await supabaseAdmin
      .from('problem_items')
      .select('is_correct, key_concepts')
      .in('submission_id', submissionIds)

    if (!items || items.length === 0) {
      return NextResponse.json({ ok: true, snapshot: { strongConcepts: [], weakConcepts: [], totalProblems: 0, correctRate: 0 } })
    }

    // Aggregate concept stats
    const conceptStats: Record<string, { correct: number; total: number }> = {}

    for (const item of items) {
      const concepts = item.key_concepts || []
      for (const concept of concepts) {
        if (!conceptStats[concept]) conceptStats[concept] = { correct: 0, total: 0 }
        conceptStats[concept].total++
        if (item.is_correct) conceptStats[concept].correct++
      }
    }

    const conceptList = Object.entries(conceptStats)
      .filter(([, s]) => s.total >= 2)
      .map(([concept, s]) => ({ concept, rate: Math.round((s.correct / s.total) * 100), total: s.total }))
      .sort((a, b) => b.total - a.total)

    const strongConcepts = conceptList.filter((c) => c.rate >= 70).slice(0, 3).map((c) => c.concept)
    const weakConcepts = conceptList.filter((c) => c.rate < 60).slice(0, 3).map((c) => c.concept)

    return NextResponse.json({
      ok: true,
      snapshot: {
        strongConcepts,
        weakConcepts,
        totalProblems: items.length,
        correctRate: correctRate(items),
      },
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Snapshot error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
