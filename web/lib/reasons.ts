// 과목·오답원인 분류 체계 단일화(GAP 2 해결).
// 채점 자동분류(레거시 한국어)와 학생 자기평가(영어 코드)를 하나의 canonical 코드로 정규화한다.

export const SUBJECT_LABELS: Record<string, string> = {
  KOREAN: '국어',
  ENGLISH: '영어',
  MATH: '수학',
  SCIENCE: '과학',
  SOCIAL: '사회',
  HISTORY: '역사',
  OTHER: '기타',
}

export function normalizeSubject(raw?: string | null): string | null {
  if (!raw) return null
  const s = String(raw).trim().toUpperCase()
  return s in SUBJECT_LABELS ? s : null
}

// 오답 원인 canonical 코드 → 한국어 라벨
export const REASON_LABELS: Record<string, string> = {
  concept: '개념 미이해',
  calculation: '계산 실수',
  reading: '문제 오독',
  memorization: '공식·암기 실패',
  application: '응용력 부족',
  time: '시간 부족',
  guessing: '찍음/감',
  other: '기타',
}

// 학생 자기평가 UI에 노출할 코드(간결하게 5종)
export const SELF_ASSESS_REASONS: { value: string; label: string }[] = [
  { value: 'concept', label: '개념을 몰랐어요' },
  { value: 'calculation', label: '계산 실수했어요' },
  { value: 'reading', label: '문제를 잘못 읽었어요' },
  { value: 'time', label: '시간이 부족했어요' },
  { value: 'guessing', label: '찍었어요' },
]

// 채점 LLM이 내보내던 레거시 한국어 값 → canonical 코드
const LEGACY_KO_TO_CODE: Record<string, string> = {
  '개념 미이해': 'concept',
  '개념 부족': 'concept',
  '오개념': 'concept',
  '계산 실수': 'calculation',
  '문제 오독': 'reading',
  '문제 해석': 'reading',
  '독해': 'reading',
  '공식 암기 실패': 'memorization',
  '공식 암기': 'memorization',
  '암기 부족': 'memorization',
  '응용력 부족': 'application',
  '시간 부족': 'time',
  '찍음/감': 'guessing',
  '찍음': 'guessing',
  '기타': 'other',
}

// raw(코드·레거시 한국어·자유서술) → { code, label } | null
export function normalizeReason(raw?: string | null): { code: string; label: string } | null {
  if (!raw) return null
  const s = String(raw).trim()
  if (!s) return null
  if (s in REASON_LABELS) return { code: s, label: REASON_LABELS[s] }
  if (s in LEGACY_KO_TO_CODE) {
    const code = LEGACY_KO_TO_CODE[s]
    return { code, label: REASON_LABELS[code] }
  }
  // 알 수 없는 값: 짧으면 그대로 보여주고, 길면 기타로
  return { code: 'other', label: s.length <= 12 ? s : '기타' }
}
