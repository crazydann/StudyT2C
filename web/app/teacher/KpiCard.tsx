'use client'

import { useEffect, useState } from 'react'

interface Props {
  icon: string
  label: string
  value: string | number
  sub?: string
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
}

const colorMap = {
  blue:   { bg: 'bg-blue-50',   text: 'text-blue-600',   border: 'border-blue-100' },
  green:  { bg: 'bg-green-50',  text: 'text-green-600',  border: 'border-green-100' },
  yellow: { bg: 'bg-yellow-50', text: 'text-yellow-600', border: 'border-yellow-100' },
  red:    { bg: 'bg-red-50',    text: 'text-red-600',    border: 'border-red-100' },
  purple: { bg: 'bg-purple-50', text: 'text-purple-600', border: 'border-purple-100' },
}

export default function KpiCard({ icon, label, value, sub, color = 'blue' }: Props) {
  const [displayed, setDisplayed] = useState<string | number>(
    typeof value === 'number' ? 0 : value
  )

  useEffect(() => {
    if (typeof value !== 'number') {
      setDisplayed(value)
      return
    }
    const target = value
    const duration = 1000
    const steps = 40
    const stepMs = duration / steps
    let current = 0
    const timer = setInterval(() => {
      current += 1
      const progress = current / steps
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayed(Math.round(eased * target))
      if (current >= steps) {
        setDisplayed(target)
        clearInterval(timer)
      }
    }, stepMs)
    return () => clearInterval(timer)
  }, [value])

  const c = colorMap[color]

  return (
    <div className={`rounded-xl border p-4 ${c.bg} ${c.border}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{icon}</span>
        <span className="text-xs font-medium text-gray-500">{label}</span>
      </div>
      <div className={`text-3xl font-bold ${c.text}`}>{displayed}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}
