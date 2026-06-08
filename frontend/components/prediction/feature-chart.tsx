'use client'

import { useModelFeatures } from '@/hooks/api'
import { Skeleton } from '@/components/ui/skeleton'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

const COLORS = [
  '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE',
  '#22D3EE', '#67E8F9', '#A5F3FC', '#CFFAFE',
  '#84CC16', '#A3E635',
]

export function FeatureImportanceChart() {
  const { features, isLoading } = useModelFeatures()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border-subtle bg-surface p-5">
        <Skeleton className="h-6 w-40 mb-4" />
        <Skeleton className="h-52 w-full" />
      </div>
    )
  }

  const data = (features?.top_features ?? []).map((f) => ({
    name: f.feature.replace(/_/g, ' '),
    importance: f.importance,
  }))

  return (
    <div className="rounded-xl border border-border-subtle bg-surface p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text-primary">
          Feature Importance
        </h3>
        <p className="text-xs text-text-secondary">Top model predictors</p>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 16, bottom: 0, left: 4 }}
        >
          <XAxis
            type="number"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            domain={[0, 'dataMax + 0.02']}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: 'var(--color-text-secondary)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={120}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-surface-elevated)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: '8px',
              color: 'var(--color-text-primary)',
              fontSize: 12,
            }}
            formatter={(v: number) => [(v * 100).toFixed(1) + '%', 'importance']}
          />
          <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
