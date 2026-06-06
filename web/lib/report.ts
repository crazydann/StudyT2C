// 리포트 인사이트 합성 — 누적 데이터를 LLM으로 분석해 "코치" 문장을 생성한다.
// 선생님(행동 지시) / 학부모(안심·이해)로 톤을 분리한다.
// LLM 실패·키 없음·파싱 오류 시 호출부가 넘긴 룰베이스 폴백을 그대로 반환한다.

import OpenAI from 'openai'

let _openai: OpenAI | null = null
function getOpenAI(): OpenAI {
  if (!_openai) _openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || 'placeholder' })
  return _openai
}

export interface ReportInsightInput {
  audience: 'teacher' | 'parent'
  studentHandle: string
  avgCorrectRate: number // 0-100
  totalQuestions: number
  submissionRate: number // 0-100
  streakDays: number
  offTopicTotal: number
  weakConcepts: { name: string; count: number }[]
  wrongReasons: { code: string; label: string; count: number }[]
  timeline: { month: string; score: number }[] // score 0-1
  falseConfidence?: { total: number; count: number } | null // ③ understood 인데 오답
}

export interface ReportInsight {
  recommendation: string
  trendSentence: string
  storyCard: { improved: string; stillWeak: string; nextPlan: string }
}

const TEACHER_SYSTEM = `당신은 학원 선생님의 수업 준비를 돕는 학습 데이터 분석가입니다.
주어진 한 학생의 최근 학습 데이터를 바탕으로, 선생님이 "다음 오프라인 수업"에서 바로 실행할 수 있는 분석을 작성하세요.

원칙:
- 단정적이고 구체적이며 실행 가능한 행동 지시 위주로. (예: "이번 주 이차방정식 15분 보강, 계산 실수 유형 5문항 점검")
- 막연한 칭찬·격려가 아니라 "무엇을·왜·어떻게" 보강할지.
- 데이터에 없는 내용을 지어내지 말 것. 데이터가 부족하면 솔직히 그렇게.
- 모든 문장은 한국어.`

const PARENT_SYSTEM = `당신은 학부모에게 자녀의 학습 상태를 따뜻하고 쉽게 설명하는 학습 코치입니다.
주어진 한 학생의 최근 학습 데이터를 바탕으로, 학부모가 안심하고 이해할 수 있는 분석을 작성하세요.

원칙:
- 전문용어·숫자 나열을 피하고, 쉽고 따뜻한 문장으로.
- 아이가 어디서 막히는지, 최근 어떻게 나아지고 있는지, 가정에서 무엇을 격려하면 좋을지.
- 불안을 자극하지 말되, 사실은 숨기지 말 것. 데이터에 없는 내용을 지어내지 말 것.
- 모든 문장은 한국어.`

function buildUserPrompt(input: ReportInsightInput): string {
  const trend =
    input.timeline.length >= 2
      ? `정답률 추이(월별, 0~1): ${input.timeline.map((t) => `${t.month}:${t.score.toFixed(2)}`).join(', ')}`
      : '정답률 추이: 데이터 부족'
  const weak =
    input.weakConcepts.length > 0
      ? input.weakConcepts.map((c) => `${c.name}(${c.count}회)`).join(', ')
      : '없음'
  const reasons =
    input.wrongReasons.length > 0
      ? input.wrongReasons.map((r) => `${r.label}(${r.count}건)`).join(', ')
      : '없음'
  const fc =
    input.falseConfidence && input.falseConfidence.total > 0
      ? `자기평가상 '이해했다'고 했으나 실제 오답인 문항: ${input.falseConfidence.count}/${input.falseConfidence.total}건 (가짜 자신감 신호)`
      : '메타인지 자기평가 데이터: 없음'

  return `학생: ${input.studentHandle}
최근 30일 평균 정답률: ${input.avgCorrectRate}%
최근 30일 튜터 질문 수: ${input.totalQuestions}건
숙제 제출률: ${input.submissionRate}%
연속 학습: ${input.streakDays}일
공부 외 질문(7일): ${input.offTopicTotal}건
자주 틀리는 개념: ${weak}
오답 유형: ${reasons}
${trend}
${fc}

위 데이터를 분석해 아래 JSON 형식으로만 응답하세요(다른 텍스트 없이):
{
  "recommendation": "다음 수업/학습을 위한 핵심 권고 1~2문장",
  "trendSentence": "최근 학습 추이를 요약한 1문장",
  "storyCard": {
    "improved": "최근 좋아진 점 1문장",
    "stillWeak": "아직 약한 점 1문장",
    "nextPlan": "다음 계획 1문장"
  }
}`
}

function isValidInsight(v: unknown): v is ReportInsight {
  if (typeof v !== 'object' || v === null) return false
  const o = v as Record<string, unknown>
  return (
    typeof o.recommendation === 'string' &&
    typeof o.trendSentence === 'string' &&
    typeof o.storyCard === 'object' &&
    o.storyCard !== null &&
    typeof (o.storyCard as Record<string, unknown>).improved === 'string' &&
    typeof (o.storyCard as Record<string, unknown>).stillWeak === 'string' &&
    typeof (o.storyCard as Record<string, unknown>).nextPlan === 'string'
  )
}

/**
 * 누적 데이터를 LLM으로 분석해 코치 문장을 생성한다.
 * 실패 시 호출부가 넘긴 룰베이스 폴백을 그대로 반환한다(절대 throw 하지 않음).
 */
export async function synthesizeReportInsight(
  input: ReportInsightInput,
  fallback: ReportInsight,
): Promise<ReportInsight> {
  if (!process.env.OPENAI_API_KEY) return fallback

  try {
    const response = await getOpenAI().chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: input.audience === 'teacher' ? TEACHER_SYSTEM : PARENT_SYSTEM },
        { role: 'user', content: buildUserPrompt(input) },
      ],
      max_tokens: 600,
      temperature: 0.4,
      response_format: { type: 'json_object' },
    })

    const raw = response.choices[0]?.message?.content ?? ''
    const parsed = JSON.parse(raw)
    if (isValidInsight(parsed)) {
      return {
        recommendation: parsed.recommendation.trim(),
        trendSentence: parsed.trendSentence.trim(),
        storyCard: {
          improved: parsed.storyCard.improved.trim(),
          stillWeak: parsed.storyCard.stillWeak.trim(),
          nextPlan: parsed.storyCard.nextPlan.trim(),
        },
      }
    }
    return fallback
  } catch {
    return fallback
  }
}
