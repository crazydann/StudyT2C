export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'
import { requireSessionFromRequest } from '@/lib/auth'
import OpenAI from 'openai'

let _openai: OpenAI | null = null
function getOpenAI() {
  if (!_openai) _openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || 'placeholder' })
  return _openai
}

const CARD_PROMPT = `당신은 한국 중·고등학생을 위한 학습 개념 카드 전문가입니다.
주어진 문제 이미지와 학생의 질문을 분석하여, 이 문제에서 핵심이 되는 개념을 5장의 카드로 정리해주세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "concept": "핵심 개념명 (예: 이차방정식의 근의 공식)",
  "cards": [
    {
      "type": "definition",
      "emoji": "📌",
      "title": "핵심 개념",
      "content": "개념에 대한 명확하고 간결한 정의 (2~3문장)"
    },
    {
      "type": "confusion",
      "emoji": "⚠️",
      "title": "헷갈리는 포인트",
      "content": "학생들이 이 개념에서 자주 실수하거나 헷갈리는 이유와 주의사항"
    },
    {
      "type": "example",
      "emoji": "💡",
      "title": "쉽게 이해하기",
      "content": "비유나 구체적인 예시를 들어 직관적으로 설명 (실생활 예시 포함)"
    },
    {
      "type": "formula",
      "emoji": "📐",
      "title": "핵심 공식·원리",
      "content": "반드시 기억해야 할 공식, 원리, 또는 풀이 순서"
    },
    {
      "type": "checkpoint",
      "emoji": "✅",
      "title": "체크포인트",
      "content": "다음에 이런 유형의 문제를 만났을 때 바로 적용할 수 있는 핵심 팁 1~2가지"
    }
  ]
}`

export async function POST(request: NextRequest) {
  try {
    requireSessionFromRequest(request, ['student'])

    const contentType = request.headers.get('content-type') || ''
    let imageBase64: string | undefined
    let imageMimeType = 'image/jpeg'
    let question = ''

    if (contentType.includes('multipart/form-data')) {
      const formData = await request.formData()
      question = (formData.get('question') as string) || ''
      const file = formData.get('image') as File | null
      if (file) {
        const buffer = await file.arrayBuffer()
        imageBase64 = Buffer.from(buffer).toString('base64')
        imageMimeType = file.type
      }
    } else {
      const body = await request.json()
      question = body.question || ''
      imageBase64 = body.imageBase64
      imageMimeType = body.imageMimeType || 'image/jpeg'
    }

    if (!imageBase64) {
      return NextResponse.json({ ok: false, error: '이미지가 필요합니다.' }, { status: 400 })
    }

    const userContent: OpenAI.Chat.ChatCompletionContentPart[] = [
      {
        type: 'image_url',
        image_url: { url: `data:${imageMimeType};base64,${imageBase64}`, detail: 'high' },
      },
      {
        type: 'text',
        text: question
          ? `학생 질문: "${question}"\n\n이 문제 이미지를 분석하여 개념 카드를 만들어주세요.`
          : '이 문제 이미지를 분석하여 개념 카드를 만들어주세요.',
      },
    ]

    const response = await getOpenAI().chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: CARD_PROMPT },
        { role: 'user', content: userContent },
      ],
      max_tokens: 1500,
      temperature: 0.5,
      response_format: { type: 'json_object' },
    })

    const raw = response.choices[0]?.message?.content ?? '{}'
    let result
    try {
      result = JSON.parse(raw)
    } catch {
      return NextResponse.json({ ok: false, error: '카드 생성에 실패했습니다.' }, { status: 500 })
    }

    return NextResponse.json({ ok: true, concept: result.concept, cards: result.cards })
  } catch (err) {
    if (err instanceof Error && err.message === 'UNAUTHORIZED') {
      return NextResponse.json({ ok: false }, { status: 401 })
    }
    console.error('Concept cards error:', err)
    return NextResponse.json({ ok: false, error: '서버 오류' }, { status: 500 })
  }
}
