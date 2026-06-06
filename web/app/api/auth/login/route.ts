export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { hashPassword, encodeSession } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'

export async function POST(request: NextRequest) {
  try {
    const { handle, password } = await request.json()

    if (!handle || !password) {
      return NextResponse.json(
        { ok: false, error: '아이디와 비밀번호를 입력해주세요.' },
        { status: 400 }
      )
    }

    const passwordHash = hashPassword(password)
    const normalized = handle.trim().toLowerCase()

    // 대소문자·공백·중복 행에 견고하도록: ilike로 후보를 조회한 뒤 JS에서 정규화 비교
    const { data: candidates, error } = await supabaseAdmin
      .from('users')
      .select('id, handle, role, status, password_hash')
      .ilike('handle', normalized)

    if (error) {
      console.error('Login query error:', error)
      return NextResponse.json(
        { ok: false, error: '서버 오류가 발생했습니다.' },
        { status: 500 }
      )
    }

    const matchedByHandle = (candidates || []).filter(
      (u) => (u.handle || '').trim().toLowerCase() === normalized
    )

    if (matchedByHandle.length === 0) {
      return NextResponse.json(
        { ok: false, error: '아이디 또는 비밀번호가 올바르지 않습니다.' },
        { status: 401 }
      )
    }

    const user = matchedByHandle.find((u) => u.password_hash === passwordHash)

    if (!user) {
      return NextResponse.json(
        { ok: false, error: '아이디 또는 비밀번호가 올바르지 않습니다.' },
        { status: 401 }
      )
    }

    if (user.status === 'inactive') {
      return NextResponse.json(
        { ok: false, error: '비활성화된 계정입니다. 관리자에게 문의하세요.' },
        { status: 403 }
      )
    }

    const sessionData = {
      id: user.id,
      handle: user.handle,
      role: user.role,
      status: user.status,
    }

    const encoded = encodeSession(sessionData)

    const response = NextResponse.json({
      ok: true,
      role: user.role,
      handle: user.handle,
    })

    response.cookies.set('st2c_session', encoded, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    })

    return response
  } catch (err) {
    console.error('Login error:', err)
    return NextResponse.json(
      { ok: false, error: '서버 오류가 발생했습니다.' },
      { status: 500 }
    )
  }
}
