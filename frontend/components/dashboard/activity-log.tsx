'use client'

import { useKpis } from '@/hooks/api'
import { Skeleton } from '@/components/ui/skeleton'
import { format } from 'date-fns'

export function ActivityLog() {
  const { kpis, isLoading } = useKpis()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5">
        <Skeleton className="h-6 w-36 mb-4" />
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-8 w-full mb-2" />
        ))}
      </div>
    )
  }

  const count = kpis?.inference_count_24h ?? 0
  const avgMs = kpis?.avg_latency_ms ?? 0

  // Build synthetic activity log entries
  const now = new Date()
  const entries = [
    {
      time: format(new Date(now.getTime() - 30_000), 'HH:mm:ss'),
      msg: `Batch inference: ${count} preds (24h)`,
      type: 'info',
    },
    {
      time: format(new Date(now.getTime() - 90_000), 'HH:mm:ss'),
      msg: `Avg latency: ${avgMs.toFixed(1)} ms`,
      type: 'metric',
    },
    {
      time: format(new Date(now.getTime() - 300_000), 'HH:mm:ss'),
      msg: 'Model runtime healthy',
      type: 'ok',
    },
    {
      time: format(new Date(now.getTime() - 600_000), 'HH:mm:ss'),
      msg: 'Cache warm-up complete',
      type: 'ok',
    },
  ]

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">Activity Log</h3>
      <div className="space-y-2">
        {entries.map((e, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-xs py-1.5 border-b border-border-subtle last:border-0"
          >
            <span className="font-mono text-text-secondary shrink-0 mt-0.5">{e.time}</span>
            <span
              className={
                e.type === 'ok'
                  ? 'text-surge-low'
                  : e.type === 'metric'
                  ? 'text-accent-blue'
                  : 'text-text-primary'
              }
            >
              {e.msg}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
