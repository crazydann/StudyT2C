import crypto from 'crypto'
import { cookies } from 'next/headers'
import { NextRequest } from 'next/server'
import { SessionData } from './types'

const SALT = 'studyt2c-mvp-2025'
const COOKIE_NAME = 'st2c_session'

export function hashPassword(plain: string): string {
  return crypto
    .createHash('sha256')
    .update(SALT + plain)
    .digest('hex')
}

export function encodeSession(session: SessionData): string {
  return Buffer.from(JSON.stringify(session)).toString('base64')
}

export function decodeSession(encoded: string): SessionData | null {
  try {
    const decoded = Buffer.from(encoded, 'base64').toString('utf-8')
    return JSON.parse(decoded) as SessionData
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
