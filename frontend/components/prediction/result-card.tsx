'use client'

import { Zap, MapPin, Building2, Clock } from 'lucide-react'
import { usePredictionStore } from '@/store'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

function SurgeBar({ value }: { value: number }) {
  const pct = Math.min(((value - 1) / 2) * 100, 100)
  return (
    <div className="h-2 rounded-full bg-surface-elevated overflow-hidden">
      <div
        className={cn(
          'h-full rounded-full transition-all duration-700',
          value < 1.3 ? 'bg-surge-low' : value < 2.0 ? 'bg-surge-medium' : 'bg-surge-high',
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export function PredictionResultCard() {
  const { prediction, isLoading, error } = usePredictionStore()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-6 flex items-center justify-center h-40">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-sm text-text-secondary">Running inference…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-surge-high/30 bg-surface p-6">
        <p className="text-sm text-surge-high">{error}</p>
      </div>
    )
  }

  if (!prediction) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-6 flex items-center justify-center h-40">
        <div className="text-center">
          <Zap className="w-8 h-8 text-text-secondary mx-auto mb-2" />
          <p className="text-sm text-text-secondary">
            Select a zone and click Predict
          </p>
        </div>
      </div>
    )
  }

  const surge = prediction.surge_multiplier

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <MapPin className="w-4 h-4 text-text-secondary" />
            <p className="text-sm text-text-primary font-medium">
              {prediction.zone_name}
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-text-secondary" />
            <p className="text-xs text-text-secondary">{prediction.borough}</p>
          </div>
        </div>
        <span
          className={cn(
            'text-xs px-2.5 py-1 rounded-full font-medium',
            surge < 1.3
              ? 'bg-surge-low/20 text-surge-low'
              : surge < 2.0
              ? 'bg-surge-medium/20 text-surge-medium'
              : 'bg-surge-high/20 text-surge-high',
          )}
        >
          {prediction.confidence} confidence
        </span>
      </div>

      <div className="text-center py-2">
        <p className="text-5xl font-bold tabular-nums leading-none"
          style={{
            color:
              surge < 1.3
                ? 'var(--color-surge-low)'
                : surge < 2.0
                ? 'var(--color-surge-medium)'
                : 'var(--color-surge-high)',
          }}
        >
          {surge.toFixed(2)}×
        </p>
        <p className="text-sm text-text-secondary mt-1">surge multiplier</p>
      </div>

      <SurgeBar value={surge} />

      <div className="flex items-center gap-1.5 text-xs text-text-secondary">
        <Clock className="w-3 h-3" />
        <span>
          {format(new Date(prediction.timestamp), 'MMM d, HH:mm:ss')}
        </span>
      </div>
    </div>
  )
}
