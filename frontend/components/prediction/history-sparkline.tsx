'use client'

import { useHistory } from '@/hooks/api'
import { usePredictionStore } from '@/store'
import { Skeleton } from '@/components/ui/skeleton'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { format, parseISO } from 'date-fns'

export function HistorySparkline() {
  const { selectedZone } = usePredictionStore()
  const { history, isLoading } = useHistory(selectedZone?.zone_name ?? null, 14)

  if (!selectedZone) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5 flex items-center justify-center h-40">
        <p className="text-sm text-text-secondary">Select a zone to see history</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5">
        <Skeleton className="h-6 w-48 mb-4" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  const data = (history?.series ?? []).map((pt) => ({
    date: format(parseISO(pt.date), 'MMM d'),
    surge: pt.surge_multiplier,
  }))

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text-primary">
          Surge History — {selectedZone.zone_name}
        </h3>
        <p className="text-xs text-text-secondary">14-day trend</p>
      </div>
      <ResponsiveContainer width="100%" height={170}>
        <LineChart data={data} margin={{ top: 0, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval={2}
          />
          <YAxis
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-surface-elevated)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: '8px',
              color: 'var(--color-text-primary)',
              fontSize: 12,
            }}
            formatter={(v: number) => [`${v.toFixed(3)}×`, 'surge']}
          />
          <Line
            type="monotone"
            dataKey="surge"
            stroke="#22D3EE"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#22D3EE' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
