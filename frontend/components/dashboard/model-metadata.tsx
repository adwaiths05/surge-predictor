'use client'

import { Brain, Calendar, BarChart2 } from 'lucide-react'
import { useModelMetadata } from '@/hooks/api'
import { Skeleton } from '@/components/ui/skeleton'

export function ModelMetadataCard() {
  const { metadata, isLoading } = useModelMetadata()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5">
        <Skeleton className="h-6 w-40 mb-4" />
        <Skeleton className="h-28 w-full" />
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4 text-accent-blue" />
        <h3 className="text-sm font-semibold text-text-primary">Model Metadata</h3>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-text-secondary flex items-center gap-1.5">
            <BarChart2 className="w-3 h-3" /> Version
          </span>
          <span className="text-xs font-mono font-medium text-text-primary">
            {metadata?.model_version ?? '—'}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-text-secondary flex items-center gap-1.5">
            <Calendar className="w-3 h-3" /> Trained
          </span>
          <span className="text-xs font-mono font-medium text-text-primary">
            {metadata?.training_date ?? '—'}
          </span>
        </div>

        {metadata?.metrics && (
          <div className="pt-2 border-t border-border-subtle space-y-2">
            {Object.entries(metadata.metrics).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between">
                <span className="text-xs text-text-secondary uppercase tracking-wide">
                  {k}
                </span>
                <span className="text-xs font-mono font-bold text-accent-blue">
                  {v.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
