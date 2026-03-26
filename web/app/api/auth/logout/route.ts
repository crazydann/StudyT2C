import { NextResponse } from 'next/server'

export async function POST() {
  const response = NextResponse.json({ ok: true })
  response.cookies.set('st2c_session', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
  })
  return response
}

export async function GET() {
  const response = NextResponse.redirect(new URL('/login', process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'))
  response.cookies.set('st2c_session', '', {
    httpOnly: true,
    maxAge: 0,
    path: '/',
  })
  return response
}
