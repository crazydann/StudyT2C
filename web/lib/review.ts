// 간격 반복(spaced repetition) 스케줄 계산 — 의존성 0
// 원본 Streamlit review_service._next_review_fsrs 의 폴백(맞음 3일/틀림 1일)을
// 누진 간격으로 확장: 정답을 연속할수록 복습 주기가 길어진다.
//
// fsrs_state(JSONB)에 { reps, intervalDays, lastReviewedAt } 를 저장한다.

export interface ReviewState {
  reps: number // 연속 정답 횟수
  intervalDays: number // 마지막으로 부여한 간격(일)
  lastReviewedAt: string // ISO
}

// 연속 정답 횟수 → 다음 간격(일). 첫 정답 3일에서 시작해 점점 길어짐.
const INTERVALS = [1, 3, 7, 14, 30, 60]

export interface ScheduleResult {
  nextReviewAt: string // ISO
  state: ReviewState
}

function isReviewState(v: unknown): v is ReviewState {
  return (
    typeof v === 'object' &&
    v !== null &&
    typeof (v as ReviewState).reps === 'number'
  )
}

/**
 * 복습 결과로 다음 복습 시점을 계산한다.
 * - 틀림: reps 초기화, 1일 후 다시
 * - 맞음: reps 증가, INTERVALS[reps] 만큼 뒤로
 */
export function scheduleNext(
  prevState: unknown,
  isCorrect: boolean,
  now: Date = new Date(),
): ScheduleResult {
  const prev: ReviewState | null = isReviewState(prevState) ? prevState : null

  let reps: number
  let intervalDays: number

  if (!isCorrect) {
    reps = 0
    intervalDays = 1
  } else {
    reps = (prev?.reps ?? 0) + 1
    intervalDays = INTERVALS[Math.min(reps, INTERVALS.length - 1)]
  }

  const next = new Date(now.getTime() + intervalDays * 24 * 60 * 60 * 1000)
  return {
    nextReviewAt: next.toISOString(),
    state: { reps, intervalDays, lastReviewedAt: now.toISOString() },
  }
}

/**
 * 채점 직후 오답 문항의 최초 복습 시점(=1일 후)을 계산한다.
 */
export function initialReviewSchedule(now: Date = new Date()): ScheduleResult {
  return scheduleNext(null, false, now)
}
