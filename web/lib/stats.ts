export interface CorrectStat { correct: number; total: number; rate: number }

// Given problem_items rows, compute overall correct rate (0-100 int)
export function correctRate(items: { is_correct: boolean }[] | null | undefined): number {
  if (!items || items.length === 0) return 0
  const correct = items.filter((i) => i.is_correct).length
  return Math.round((correct / items.length) * 100)
}

// Group items by a key extractor and compute per-key {correct,total,rate}
export function rateByKey<T extends { is_correct: boolean }>(
  items: T[] | null | undefined,
  keyOf: (item: T) => string,
): Record<string, CorrectStat> {
  const map: Record<string, { correct: number; total: number }> = {}
  for (const item of items || []) {
    const k = keyOf(item)
    if (!map[k]) map[k] = { correct: 0, total: 0 }
    map[k].total++
    if (item.is_correct) map[k].correct++
  }
  const out: Record<string, CorrectStat> = {}
  for (const [k, v] of Object.entries(map)) {
    out[k] = { correct: v.correct, total: v.total, rate: v.total > 0 ? Math.round((v.correct / v.total) * 100) : 0 }
  }
  return out
}
