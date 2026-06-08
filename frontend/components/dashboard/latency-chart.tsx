'use client'

import { useKpis } from '@/hooks/api'
import { Skeleton } from '@/components/ui/skeleton'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

function buildLatencySeries(avg: number, p95: number) {
  return Array.from({ length: 20 }, (_, i) => ({
    t: i,
    avg: Math.max(0, avg + Math.sin(i * 0.8 + 0.5) * (avg * 0.25)),
    p95: Math.max(0, p95 + Math.cos(i * 0.6 + 1) * (p95 * 0.2)),
  }))
}

export function LatencyChart() {
  const { kpis, isLoading } = useKpis()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5">
        <Skeleton className="h-6 w-40 mb-4" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  const data = buildLatencySeries(
    kpis?.avg_latency_ms ?? 0,
    kpis?.p95_latency_ms ?? 0,
  )

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text-primary">Latency Profile</h3>
        <p className="text-xs text-text-secondary">
          Avg {kpis?.avg_latency_ms?.toFixed(1) ?? '—'} ms &nbsp;·&nbsp; P95{' '}
          {kpis?.p95_latency_ms?.toFixed(1) ?? '—'} ms
        </p>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="avgGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="p95Grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F97316" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#F97316" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="t" hide />
          <YAxis
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-surface-elevated)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: '8px',
              color: 'var(--color-text-primary)',
              fontSize: 12,
            }}
            formatter={(v: number, name: string) => [`${v.toFixed(1)} ms`, name]}
          />
          <Area
            type="monotone"
            dataKey="avg"
            stroke="#3B82F6"
            fill="url(#avgGrad)"
            strokeWidth={2}
            dot={false}
            name="Avg"
          />
          <Area
            type="monotone"
            dataKey="p95"
            stroke="#F97316"
            fill="url(#p95Grad)"
            strokeWidth={2}
            dot={false}
            name="P95"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
