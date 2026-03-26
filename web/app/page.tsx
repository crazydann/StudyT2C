import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { decodeSession } from '@/lib/auth'

export default async function RootPage() {
  const cookieStore = await cookies()
  const sessionCookie = cookieStore.get('st2c_session')

  if (sessionCookie?.value) {
    const session = decodeSession(sessionCookie.value)
    if (session) {
      if (session.role === 'student') redirect('/student')
      if (session.role === 'teacher') redirect('/teacher')
      if (session.role === 'parent') redirect('/parent')
    }
  }

  redirect('/login')
}
