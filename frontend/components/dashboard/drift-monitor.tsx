'use client'

import { AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react'
import { useDriftSummary } from '@/hooks/api'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export function DriftMonitor() {
  const { drift, isLoading } = useDriftSummary()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5">
        <Skeleton className="h-6 w-32 mb-4" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  const score = drift?.drift_score ?? 0
  const status = drift?.status ?? 'unknown'
  const isStable = status === 'stable'
  const pct = Math.min(score * 100, 100)

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">Drift Monitor</h3>
        <span
          className={cn(
            'text-xs px-2 py-0.5 rounded-full font-medium',
            isStable
              ? 'bg-surge-low/20 text-surge-low'
              : 'bg-surge-high/20 text-surge-high',
          )}
        >
          {status}
        </span>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          {isStable ? (
            <CheckCircle className="w-8 h-8 text-surge-low shrink-0" />
          ) : (
            <AlertTriangle className="w-8 h-8 text-surge-high shrink-0" />
          )}
          <div>
            <p className="text-2xl font-bold text-text-primary tabular-nums">
              {score.toFixed(3)}
            </p>
            <p className="text-xs text-text-secondary">drift score</p>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs text-text-secondary mb-1">
            <span>Stable</span>
            <span>Drifted</span>
          </div>
          <div className="h-1.5 rounded-full bg-surface-elevated overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-700',
                pct < 20 ? 'bg-surge-low' : pct < 50 ? 'bg-surge-medium' : 'bg-surge-high',
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        <p className="text-xs text-text-secondary flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          PSI-based feature drift detection
        </p>
      </div>
    </div>
  )
}
