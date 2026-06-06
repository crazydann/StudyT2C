import crypto from 'crypto'
import { cookies } from 'next/headers'
import { NextRequest } from 'next/server'
import { SessionData } from './types'

const SALT = 'studyt2c-mvp-2025'
const COOKIE_NAME = 'st2c_session'

// 세션 서명용 비밀키: 전용 SESSION_SECRET → 서비스 키(이미 Vercel에 설정, 클라이언트 비노출) → 상수 순으로 사용
function getSessionSecret(): string {
  return (
    process.env.SESSION_SECRET ||
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    'studyt2c-session-secret-2025'
  )
}

export function hashPassword(plain: string): string {
  return crypto
    .createHash('sha256')
    .update(SALT + plain)
    .digest('hex')
}

function base64url(input: Buffer | string): string {
  return Buffer.from(input)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

function sign(payload: string): string {
  return base64url(crypto.createHmac('sha256', getSessionSecret()).update(payload).digest())
}

// 서명된 세션 토큰 생성: "<base64url(json)>.<base64url(hmac)>"
export function encodeSession(session: SessionData): string {
  const payload = base64url(JSON.stringify(session))
  return `${payload}.${sign(payload)}`
}

// 서명 검증 후에만 파싱. 서명이 없거나 위조된 쿠키는 거부(null).
export function decodeSession(encoded: string): SessionData | null {
  try {
    const dot = encoded.lastIndexOf('.')
    if (dot <= 0) return null // 서명 없는(구버전/위조) 쿠키 거부 → 재로그인 유도

    const payload = encoded.slice(0, dot)
    const providedSig = encoded.slice(dot + 1)
    const expectedSig = sign(payload)

    // 타이밍 공격 방지를 위한 상수 시간 비교
    const a = Buffer.from(providedSig)
    const b = Buffer.from(expectedSig)
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
      return null
    }

    const json = Buffer.from(payload.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8')
    return JSON.parse(json) as SessionData
  } catch {
    return null
  }
}

export function getSessionFromRequest(request: NextRequest): SessionData | null {
  const cookie = request.cookies.get(COOKIE_NAME)
  if (!cookie?.value) return null
  return decodeSession(cookie.value)
}

export async function getSession(): Promise<SessionData | null> {
  const cookieStore = await cookies()
  const cookie = cookieStore.get(COOKIE_NAME)
  if (!cookie?.value) return null
  return decodeSession(cookie.value)
}

export function requireSessionFromRequest(
  request: NextRequest,
  allowedRoles?: string[]
): SessionData {
  const session = getSessionFromRequest(request)
  if (!session) {
    throw new Error('UNAUTHORIZED')
  }
  if (allowedRoles && !allowedRoles.includes(session.role)) {
    throw new Error('FORBIDDEN')
  }
  return session
}

export const COOKIE_NAME_EXPORT = COOKIE_NAME
