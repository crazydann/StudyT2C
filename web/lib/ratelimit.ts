// Simple in-memory sliding-window rate limiter.
// Suitable for single-instance MVP; upgrade to Redis/Upstash for multi-instance deployments.

const store = new Map<string, number[]>()

/**
 * Returns true if the request is allowed, false if the rate limit is exceeded.
 * @param key     - Unique identifier (e.g. "login:ip:1.2.3.4")
 * @param max     - Maximum number of requests allowed within the window
 * @param windowMs - Window size in milliseconds
 */
export function checkRateLimit(key: string, max: number, windowMs: number): boolean {
  const now = Date.now()
  const windowStart = now - windowMs
  const timestamps = (store.get(key) || []).filter((t) => t > windowStart)
  if (timestamps.length >= max) return false
  timestamps.push(now)
  store.set(key, timestamps)
  return true
}

// Prune stale entries every 10 minutes to prevent unbounded memory growth
setInterval(() => {
  const cutoff = Date.now() - 60 * 60 * 1000
  for (const [key, ts] of store.entries()) {
    const fresh = ts.filter((t) => t > cutoff)
    if (fresh.length === 0) store.delete(key)
    else store.set(key, fresh)
  }
}, 10 * 60 * 1000)
