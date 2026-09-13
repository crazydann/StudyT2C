export const dynamic = 'force-dynamic'

import { NextResponse } from 'next/server'

const COOKIE_CLEAR = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'strict' as const,
  maxAge: 0,
  path: '/',
}

export async function POST() {
  const response = NextResponse.json({ ok: true })
  response.cookies.set('st2c_session', '', COOKIE_CLEAR)
  return response
}

export async function GET() {
  const response = NextResponse.redirect(
    new URL('/login', process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'),
  )
  response.cookies.set('st2c_session', '', COOKIE_CLEAR)
  return response
}
