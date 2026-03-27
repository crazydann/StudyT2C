export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

// PATCH /api/student/[id]/mode — parent or teacher sets studying/break mode
export async function PATCH(request: NextRequest, { params }: { params: { id: string } }) {
  try {
    requireSessionFromRequest(request, ['parent', 'teacher'])
    const { status } = await request.json()

    if (!['studying', 'break'].includes(status)) {
      return NextResponse.json({ ok: false, error: '잘못된 상태값' }, { status: 400 })
    }

    const { error } = await supabaseAdmin
      .from('users')
      .update({ status })
      .eq('id', params.id)

    if (error) throw error

    return NextResponse.json({ ok: true, status })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false }, { status: 403 })
    }
    console.error('Mode PATCH error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
