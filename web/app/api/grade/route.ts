export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { gradeImage, gradeText } from '@/lib/openai'
import crypto from 'crypto'
import { GradedItem } from '@/lib/types'

function parseGradedItems(raw: string): GradedItem[] {
  try {
    // Extract JSON array from response
    const match = raw.match(/\[[\s\S]*\]/)
    if (!match) return []
    return JSON.parse(match[0]) as GradedItem[]
  } catch {
    return []
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = requireSessionFromRequest(request, ['student'])
    const contentType = request.headers.get('content-type') || ''

    let gradedItems: GradedItem[] = []
    let fileHash: string = crypto.randomUUID()

    if (contentType.includes('multipart/form-data')) {
      // Image upload
      const formData = await request.formData()
      const file = formData.get('file') as File | null

      if (!file) {
        return NextResponse.json({ ok: false, error: '파일을 업로드해주세요.' }, { status: 400 })
      }

      const buffer = Buffer.from(await file.arrayBuffer())
      const base64 = buffer.toString('base64')
      const mimeType = file.type || 'image/jpeg'

      // Hash for deduplication
      fileHash = crypto.createHash('sha256').update(buffer).digest('hex')

      const raw = await gradeImage(base64, mimeType)
      gradedItems = parseGradedItems(raw)
    } else {
      // Text submission
      const body = await request.json()
      const { text } = body

      if (!text?.trim()) {
        return NextResponse.json({ ok: false, error: '문제 텍스트를 입력해주세요.' }, { status: 400 })
      }

      fileHash = crypto.createHash('sha256').update(text).digest('hex')
      const raw = await gradeText(text)
      gradedItems = parseGradedItems(raw)
    }

    if (gradedItems.length === 0) {
      return NextResponse.json({ ok: false, error: '채점 결과를 분석하지 못했습니다. 다시 시도해주세요.' }, { status: 422 })
    }

    // Insert submission
    const { data: submission, error: subError } = await supabaseAdmin
      .from('problem_submissions')
      .insert({
        student_user_id: session.id,
        file_hash: fileHash,
      })
      .select()
      .single()

    if (subError) throw subError

    // Insert problem items
    const itemsToInsert = gradedItems.map((item) => ({
      student_user_id: session.id,
      submission_id: submission.id,
      item_no: item.item_no,
      is_correct: item.is_correct,
      key_concepts: item.key_concepts || [],
      explanation_summary: item.explanation_summary || '',
      reason_category: item.reason_category || '',
    }))

    const { error: itemsError } = await supabaseAdmin
      .from('problem_items')
      .insert(itemsToInsert)

    if (itemsError) throw itemsError

    return NextResponse.json({
      ok: true,
      submission_id: submission.id,
      items: gradedItems,
    })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false, error: '인증이 필요합니다.' }, { status: 401 })
    }
    if (err instanceof Error && err.message === 'FORBIDDEN') {
      return NextResponse.json({ ok: false, error: '권한이 없습니다.' }, { status: 403 })
    }
    console.error('Grade error:', err)
    return NextResponse.json({ ok: false, error: '채점 중 오류가 발생했습니다.' }, { status: 500 })
  }
}
