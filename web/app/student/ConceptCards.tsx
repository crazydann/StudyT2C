'use client'

import { useState } from 'react'

export interface ConceptCard {
  type: 'definition' | 'confusion' | 'example' | 'formula' | 'checkpoint'
  emoji: string
  title: string
  content: string
}

interface Props {
  concept: string
  cards: ConceptCard[]
  onClose: () => void
}

const CARD_STYLES: Record<string, { bg: string; border: string; titleColor: string; dot: string }> = {
  definition: { bg: 'bg-blue-50',   border: 'border-blue-200',  titleColor: 'text-blue-700',   dot: 'bg-blue-400' },
  confusion:  { bg: 'bg-red-50',    border: 'border-red-200',   titleColor: 'text-red-700',    dot: 'bg-red-400' },
  example:    { bg: 'bg-yellow-50', border: 'border-yellow-200',titleColor: 'text-yellow-700', dot: 'bg-yellow-400' },
  formula:    { bg: 'bg-purple-50', border: 'border-purple-200',titleColor: 'text-purple-700', dot: 'bg-purple-400' },
  checkpoint: { bg: 'bg-green-50',  border: 'border-green-200', titleColor: 'text-green-700',  dot: 'bg-green-400' },
}

export default function ConceptCards({ concept, cards, onClose }: Props) {
  const [activeIdx, setActiveIdx] = useState(0)

  const activeCard = cards[activeIdx]
  const style = CARD_STYLES[activeCard?.type] ?? CARD_STYLES.definition

  return (
    <div className="mt-3 bg-white rounded-2xl border border-gray-100 shadow-md overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">개념 카드</span>
          <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">{concept}</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
      </div>

      {/* Active card */}
      <div className={`mx-4 mt-4 rounded-xl border p-4 transition-all ${style.bg} ${style.border}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{activeCard?.emoji}</span>
          <span className={`text-sm font-bold ${style.titleColor}`}>{activeCard?.title}</span>
        </div>
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{activeCard?.content}</p>
      </div>

      {/* Dot nav */}
      <div className="flex items-center justify-center gap-2 py-3">
        {cards.map((card, idx) => (
          <button
            key={idx}
            onClick={() => setActiveIdx(idx)}
            className={`transition-all rounded-full ${
              idx === activeIdx
                ? `w-6 h-2.5 ${CARD_STYLES[card.type]?.dot ?? 'bg-gray-400'}`
                : 'w-2.5 h-2.5 bg-gray-200 hover:bg-gray-300'
            }`}
            title={card.title}
          />
        ))}
      </div>

      {/* Prev / Next */}
      <div className="flex border-t border-gray-100">
        <button
          onClick={() => setActiveIdx((i) => Math.max(0, i - 1))}
          disabled={activeIdx === 0}
          className="flex-1 py-2.5 text-sm text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors"
        >
          ← 이전
        </button>
        <div className="w-px bg-gray-100" />
        <button
          onClick={() => setActiveIdx((i) => Math.min(cards.length - 1, i + 1))}
          disabled={activeIdx === cards.length - 1}
          className="flex-1 py-2.5 text-sm text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors"
        >
          다음 →
        </button>
      </div>
    </div>
  )
}
