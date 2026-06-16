import crypto from 'crypto'
import { cookies } from 'next/headers'
import { NextRequest } from 'next/server'
import { SessionData } from './types'

const COOKIE_NAME = 'st2c_session'
const LEGACY_SALT = 'studyt2c-mvp-2025'

// SESSION_SECRET must be set in production. Falls back to service role key (with warning)
// so existing deployments don't break before the env var is added.
// Never falls back to a hardcoded constant.
function getSessionSecret(): string {
  const secret = process.env.SESSION_SECRET
  if (secret) return secret
  if (process.env.NODE_ENV === 'production') {
    const srvKey = process.env.SUPABASE_SERVICE_ROLE_KEY
    if (srvKey) {
      console.warn('[auth] SESSION_SECRET not set — using service role key as session secret. Set SESSION_SECRET immediately.')
      return srvKey
    }
    throw new Error('SESSION_SECRET environment variable is required in production')
  }
  return 'studyt2c-session-secret-dev-only'
}

// Legacy SHA-256 hash — used only for backward-compat verification during re-hash migration
function hashPasswordLegacy(plain: string): string {
  return crypto.createHash('sha256').update(LEGACY_SALT + plain).digest('hex')
}

// Current password hash: scrypt with per-user random salt.
// Format: "scrypt:<hex_salt>:<hex_hash>"
export function hashPassword(plain: string): string {
  const salt = crypto.randomBytes(16).toString('hex')
  const hash = crypto.scryptSync(plain, salt, 64).toString('hex')
  return `scrypt:${salt}:${hash}`
}

/**
 * Verifies a plaintext password against a stored hash.
 * Handles both scrypt (new) and legacy SHA-256 (old) formats.
 * Always performs constant-time comparison to resist timing attacks.
 */
export function verifyPassword(plain: string, stored: string): boolean {
  if (stored.startsWith('scrypt:')) {
    const parts = stored.split(':')
    if (parts.length !== 3) return false
    const [, salt, expectedHex] = parts
    try {
      const actual = crypto.scryptSync(plain, salt, 64)
      const expected = Buffer.from(expectedHex, 'hex')
      if (actual.length !== expected.length) return false
      return crypto.timingSafeEqual(actual, expected)
    } catch {
      return false
    }
  }
  // Legacy SHA-256: constant-time compare
  const legacyHash = hashPasswordLegacy(plain)
  const a = Buffer.from(legacyHash)
  const b = Buffer.from(stored)
  if (a.length !== b.length) return false
  return crypto.timingSafeEqual(a, b)
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

export function encodeSession(session: SessionData): string {
  const payload = base64url(JSON.stringify(session))
  return `${payload}.${sign(payload)}`
}

// Verifies signature before parsing. Forged or unsigned cookies return null.
export function decodeSession(encoded: string): SessionData | null {
  try {
    const dot = encoded.lastIndexOf('.')
    if (dot <= 0) return null

    const payload = encoded.slice(0, dot)
    const providedSig = encoded.slice(dot + 1)
    const expectedSig = sign(payload)

    const a = Buffer.from(providedSig)
    const b = Buffer.from(expectedSig)
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null

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
  allowedRoles?: string[],
): SessionData {
  const session = getSessionFromRequest(request)
  if (!session) throw new Error('UNAUTHORIZED')
  if (allowedRoles && !allowedRoles.includes(session.role)) throw new Error('FORBIDDEN')
  return session
}
