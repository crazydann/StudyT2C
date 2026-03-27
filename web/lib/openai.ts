import OpenAI from 'openai'

let _openai: OpenAI | null = null

function getOpenAI(): OpenAI {
  if (!_openai) {
    _openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY || 'placeholder',
    })
  }
  return _openai
}

const KOREAN_TUTOR_SYSTEM_PROMPT = `당신은 한국 중·고등학생을 위한 학습 도우미입니다. 수학, 국어, 영어, 과학, 사회 등 학습 관련 질문에만 답변하세요.

규칙:
1. 항상 한국어로 답변하세요.
2. 학습과 관련없는 질문에는 정중하게 거절하고 학습 관련 질문을 유도하세요.
3. 설명은 쉽고 친절하게, 예시를 들어 설명하세요.
4. 학생의 수준에 맞는 언어를 사용하세요.
5. 틀린 개념이 있으면 바로잡아 주세요.`

const STUDYING_MODE_SYSTEM_PROMPT = `당신은 한국 중·고등학생을 위한 학습 도우미입니다.
현재 학생은 선생님·학부모가 설정한 '공부 모드' 상태입니다.

규칙:
1. 항상 한국어로 답변하세요.
2. 수학, 국어, 영어, 과학, 사회, 역사 등 학습·숙제·개념·시험과 직접 관련된 질문에만 답변하세요.
3. 게임, 연애, 주식, 잡담, 농담, 영화, 유튜브, 연예인, 스포츠 관람 등 공부와 무관한 질문은 반드시 거절하세요.
4. 거절할 때는 "지금은 공부 시간이에요! 수학, 영어, 과학 등 학습 관련 질문을 해주세요. 😊" 라고 말하세요.
5. 설명은 쉽고 친절하게, 예시를 들어 설명하세요.
6. 틀린 개념이 있으면 바로잡아 주세요.`

const OFF_TOPIC_PATTERNS: { keywords: string[]; category: string }[] = [
  { keywords: ['게임', '롤', '로블록스', '마인크래프트', '배그', '오버워치', '리그오브레전드'], category: '게임/오락' },
  { keywords: ['유튜브', '틱톡', '인스타', '릴스', '쇼츠'], category: '소셜미디어/동영상' },
  { keywords: ['연예인', '아이돌', '오빠', '팬덤', '콘서트', '드라마', '영화'], category: '연예/엔터테인먼트' },
  { keywords: ['연애', '좋아하는 사람', '남자친구', '여자친구', '짝사랑', '썸'], category: '연애/인간관계' },
  { keywords: ['주식', '코인', '비트코인', '재테크', '투자'], category: '주식/재테크' },
  { keywords: ['맛집', '음식', '뭐 먹', '배고파', '치킨', '피자', '라면'], category: '음식/잡담' },
  { keywords: ['농담', '웃긴', '개그', 'ㅋㅋ', '재미있는 이야기'], category: '잡담/농담' },
  { keywords: ['축구', '야구', '농구', '스포츠', '경기 결과', '선수'], category: '스포츠 관람' },
]

const STUDY_KEYWORDS = ['문제', '공부', '학습', '시험', '숙제', '개념', '공식', '이론', '풀이', '계산', '설명', '뜻', '의미', '예시', '방법', '어떻게']

function detectOffTopic(message: string): { offTopic: boolean; category: string } {
  const hasStudyKeyword = STUDY_KEYWORDS.some((kw) => message.includes(kw))
  if (hasStudyKeyword) return { offTopic: false, category: '' }

  for (const { keywords, category } of OFF_TOPIC_PATTERNS) {
    if (keywords.some((kw) => message.includes(kw))) {
      return { offTopic: true, category }
    }
  }
  return { offTopic: false, category: '' }
}

export interface ChatMessageInput {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatResult {
  reply: string
  isStudy: boolean
  offTopicCategory: string
}

export async function textChat(messages: ChatMessageInput[], mode: 'studying' | 'break' = 'break'): Promise<ChatResult> {
  const systemPrompt = mode === 'studying' ? STUDYING_MODE_SYSTEM_PROMPT : KOREAN_TUTOR_SYSTEM_PROMPT

  const systemMessage: ChatMessageInput = {
    role: 'system',
    content: systemPrompt,
  }

  const lastUserMessage = messages.filter((m) => m.role === 'user').pop()

  if (lastUserMessage) {
    const { offTopic, category } = detectOffTopic(lastUserMessage.content)
    if (offTopic) {
      const refusal =
        mode === 'studying'
          ? `지금은 공부 시간이에요! 수학, 영어, 과학 등 학습 관련 질문을 해주세요. 😊`
          : `죄송해요! 저는 학습 관련 질문만 도와드릴 수 있어요. 수학, 국어, 영어, 과학, 사회 등 공부와 관련된 질문을 해주세요! 😊`
      return { reply: refusal, isStudy: false, offTopicCategory: category }
    }
  }

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [systemMessage, ...messages],
    max_tokens: 1000,
    temperature: 0.7,
  })

  const reply = response.choices[0]?.message?.content ?? '죄송합니다, 답변을 생성하지 못했습니다.'
  return { reply, isStudy: true, offTopicCategory: '' }
}

export async function gradeImage(base64: string, mimeType: string): Promise<string> {
  const GRADE_SYSTEM_PROMPT = `당신은 한국 중·고등학교 시험지 채점 전문가입니다.
주어진 이미지에서 문제와 학생의 답안을 분석하여 채점 결과를 JSON 형식으로 반환하세요.

반드시 다음 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {
    "item_no": 1,
    "is_correct": true,
    "key_concepts": ["개념1", "개념2"],
    "explanation_summary": "이 문제는 ...",
    "reason_category": "계산 실수"
  }
]

reason_category는 오답인 경우에만: "개념 미이해", "계산 실수", "문제 오독", "공식 암기 실패", "응용력 부족", "기타"`

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o',
    messages: [
      { role: 'system', content: GRADE_SYSTEM_PROMPT },
      {
        role: 'user',
        content: [
          {
            type: 'image_url',
            image_url: { url: `data:${mimeType};base64,${base64}`, detail: 'high' },
          },
          { type: 'text', text: '이 시험지를 채점하고 각 문항의 결과를 JSON으로 반환해주세요.' },
        ],
      },
    ],
    max_tokens: 2000,
    temperature: 0.1,
  })

  return response.choices[0]?.message?.content ?? '[]'
}

export async function gradeText(problemText: string): Promise<string> {
  const GRADE_TEXT_PROMPT = `당신은 한국 중·고등학교 채점 전문가입니다.
주어진 문제와 답안 텍스트를 분석하여 채점 결과를 JSON 형식으로 반환하세요.

반드시 다음 JSON 배열 형식으로만 응답하세요:
[
  {
    "item_no": 1,
    "is_correct": true,
    "key_concepts": ["개념1", "개념2"],
    "explanation_summary": "이 문제는 ...",
    "reason_category": "계산 실수"
  }
]`

  const response = await getOpenAI().chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: GRADE_TEXT_PROMPT },
      { role: 'user', content: `다음 문제와 답안을 채점해주세요:\n\n${problemText}` },
    ],
    max_tokens: 2000,
    temperature: 0.1,
  })

  return response.choices[0]?.message?.content ?? '[]'
}
