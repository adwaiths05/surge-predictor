'use client'

import { Calendar } from 'lucide-react'
import { usePredictionStore } from '@/store'
import { format } from 'date-fns'

export function DateTimePicker() {
  const { selectedDateTime, setSelectedDateTime } = usePredictionStore()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const d = new Date(e.target.value)
    if (!isNaN(d.getTime())) setSelectedDateTime(d)
  }

  // Format for datetime-local input
  const localValue = format(selectedDateTime, "yyyy-MM-dd'T'HH:mm")

  return (
    <div>
      <label className="block text-xs text-text-secondary mb-2 font-medium">
        Date & Time
      </label>
      <div className="relative">
        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary pointer-events-none" />
        <input
          type="datetime-local"
          value={localValue}
          onChange={handleChange}
          className="w-full pl-9 pr-4 py-2.5 text-sm rounded-lg border border-border-subtle bg-surface-elevated text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue/40 focus:border-accent-blue transition-all [color-scheme:dark]"
        />
      </div>
      <p className="text-xs text-text-secondary mt-1.5">
        Prediction uses live data — time selection is for reference
      </p>
    </div>
  )
}
