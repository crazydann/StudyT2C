import { createClient, SupabaseClient } from '@supabase/supabase-js'

function getSupabaseUrl(): string {
  return process.env.NEXT_PUBLIC_SUPABASE_URL || ''
}

function getAnonKey(): string {
  return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
}

function getServiceKey(): string {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!key) {
    if (process.env.NODE_ENV === 'production') throw new Error('SUPABASE_SERVICE_ROLE_KEY is required')
    return getAnonKey()
  }
  return key
}

let _supabaseAdmin: SupabaseClient | null = null

function getSupabaseAdmin(): SupabaseClient {
  if (!_supabaseAdmin) {
    _supabaseAdmin = createClient(getSupabaseUrl(), getServiceKey())
  }
  return _supabaseAdmin
}

// this 바인딩을 유지하는 Proxy
function makeLazyProxy(getter: () => SupabaseClient): SupabaseClient {
  return new Proxy({} as SupabaseClient, {
    get(_target, prop) {
      const client = getter()
      const value = client[prop as keyof SupabaseClient]
      if (typeof value === 'function') {
        return (value as Function).bind(client)
      }
      return value
    },
  })
}

export const supabaseAdmin = makeLazyProxy(getSupabaseAdmin)
