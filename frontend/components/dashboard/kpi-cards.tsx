'use client'

import { Activity, Clock, Zap } from 'lucide-react'
import { useKpis } from '@/hooks/api'
import { Skeleton } from '@/components/ui/skeleton'
import { FadeIn } from '@/components/ui/animated'

interface KPICardProps {
  label: string
  value: string
  sub?: string
  icon: React.ReactNode
  accent: string
}

function KPICard({ label, value, sub, icon, accent }: KPICardProps) {
  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5 flex items-start gap-4">
      <div className={`p-2.5 rounded-lg ${accent} bg-opacity-10`}>{icon}</div>
      <div>
        <p className="text-xs text-text-secondary mb-1">{label}</p>
        <p className="text-2xl font-bold text-text-primary tabular-nums">{value}</p>
        {sub && <p className="text-xs text-text-secondary mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export function KPICards() {
  const { kpis, isLoading } = useKpis()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <FadeIn>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KPICard
          label="Inferences (24h)"
          value={kpis?.inference_count_24h?.toLocaleString() ?? '0'}
          sub="Total predictions served"
          icon={<Activity className="w-5 h-5 text-accent-blue" />}
          accent="bg-accent-blue"
        />
        <KPICard
          label="Avg Latency"
          value={`${kpis?.avg_latency_ms?.toFixed(1) ?? '—'} ms`}
          sub="Mean inference time"
          icon={<Clock className="w-5 h-5 text-surge-medium" />}
          accent="bg-surge-medium"
        />
        <KPICard
          label="P95 Latency"
          value={`${kpis?.p95_latency_ms?.toFixed(1) ?? '—'} ms`}
          sub="95th percentile latency"
          icon={<Zap className="w-5 h-5 text-surge-high" />}
          accent="bg-surge-high"
        />
      </div>
    </FadeIn>
  )
}
