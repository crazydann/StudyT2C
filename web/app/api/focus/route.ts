export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

// POST /api/focus — student page sends visibility events
export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const { event_type } = await request.json()

    if (!['left_tab', 'returned_tab', 'tab_closed'].includes(event_type)) {
      return NextResponse.json({ ok: false, error: '잘못된 이벤트 타입' }, { status: 400 })
    }

    await supabaseAdmin.from('focus_events').insert({
      student_user_id: session.id,
      event_type,
    })

    return NextResponse.json({ ok: true })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    // Silently fail — focus tracking is best-effort
    return NextResponse.json({ ok: false })
  }
}
