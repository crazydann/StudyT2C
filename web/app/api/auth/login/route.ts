export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { verifyPassword, hashPassword, encodeSession } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { checkRateLimit } from '@/lib/ratelimit'

// Rate limits: 10 attempts per 5 min per IP, 5 per 5 min per handle
const WINDOW_MS = 5 * 60 * 1000
const IP_MAX = 10
const HANDLE_MAX = 5

function getClientIp(request: NextRequest): string {
  return (
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-real-ip') ||
    'unknown'
  )
}

export async function POST(request: NextRequest) {
  try {
    const ip = getClientIp(request)

    // Parse body first so we can rate-limit by handle too
    let handle: string | undefined
    let password: string | undefined
    try {
      const body = await request.json()
      handle = body.handle
      password = body.password
    } catch {
      return NextResponse.json({ ok: false, error: '잘못된 요청입니다.' }, { status: 400 })
    }

    if (!handle || !password) {
      return NextResponse.json(
        { ok: false, error: '아이디와 비밀번호를 입력해주세요.' },
        { status: 400 },
      )
    }

    const normalized = handle.trim().toLowerCase()

    // Rate limit: IP-based and handle-based
    if (!checkRateLimit(`login:ip:${ip}`, IP_MAX, WINDOW_MS)) {
      return NextResponse.json(
        { ok: false, error: '잠시 후 다시 시도해주세요. (요청 초과)' },
        { status: 429 },
      )
    }
    if (!checkRateLimit(`login:handle:${normalized}`, HANDLE_MAX, WINDOW_MS)) {
      return NextResponse.json(
        { ok: false, error: '잠시 후 다시 시도해주세요. (요청 초과)' },
        { status: 429 },
      )
    }

    const { data: candidates, error } = await supabaseAdmin
      .from('users')
      .select('id, handle, role, status, password_hash')
      .ilike('handle', normalized)

    if (error) {
      console.error('Login query error:', error)
      return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
    }

    const matchedByHandle = (candidates || []).filter(
      (u) => (u.handle || '').trim().toLowerCase() === normalized,
    )

    if (matchedByHandle.length === 0) {
      return NextResponse.json(
        { ok: false, error: '아이디 또는 비밀번호가 올바르지 않습니다.' },
        { status: 401 },
      )
    }

    const user = matchedByHandle.find((u) => verifyPassword(password!, u.password_hash))

    if (!user) {
      return NextResponse.json(
        { ok: false, error: '아이디 또는 비밀번호가 올바르지 않습니다.' },
        { status: 401 },
      )
    }

    if (user.status === 'inactive') {
      return NextResponse.json(
        { ok: false, error: '비활성화된 계정입니다. 관리자에게 문의하세요.' },
        { status: 403 },
      )
    }

    // Migrate legacy SHA-256 hash → scrypt in the background (fire-and-forget)
    if (!user.password_hash.startsWith('scrypt:')) {
      const newHash = hashPassword(password!)
      supabaseAdmin
        .from('users')
        .update({ password_hash: newHash })
        .eq('id', user.id)
        .then(({ error: e }) => {
          if (e) console.error('[auth] password rehash failed:', e.message)
        })
    }

    const sessionData = { id: user.id, handle: user.handle, role: user.role, status: user.status }
    const encoded = encodeSession(sessionData)

    const response = NextResponse.json({ ok: true, role: user.role, handle: user.handle })
    response.cookies.set('st2c_session', encoded, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7,
      path: '/',
    })
    return response
  } catch (err) {
    console.error('Login error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류가 발생했습니다.' }, { status: 500 })
  }
}
