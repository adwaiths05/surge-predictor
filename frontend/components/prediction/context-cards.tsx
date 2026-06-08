'use client'

import { Cloud, CloudRain, Thermometer, Car } from 'lucide-react'
import { usePredictionStore } from '@/store'

interface ContextCardProps {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
}

function ContextCard({ icon, label, value, sub }: ContextCardProps) {
  return (
    <div className="flex items-center gap-3 p-3.5 rounded-lg bg-surface-elevated border border-border-subtle">
      <div className="text-accent-blue shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs text-text-secondary">{label}</p>
        <p className="text-sm font-semibold text-text-primary truncate">{value}</p>
        {sub && <p className="text-xs text-text-secondary">{sub}</p>}
      </div>
    </div>
  )
}

export function ContextCards() {
  const { prediction } = usePredictionStore()

  if (!prediction) return null

  const { weather, traffic } = prediction
  const flowPct = (traffic.traffic_flow_ratio * 100).toFixed(0)
  const congestionLabel =
    traffic.traffic_flow_ratio > 0.7
      ? 'Heavy congestion'
      : traffic.traffic_flow_ratio > 0.4
      ? 'Moderate traffic'
      : 'Light traffic'

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <ContextCard
        icon={<Thermometer className="w-5 h-5" />}
        label="Temperature"
        value={`${weather.temperature.toFixed(1)} °C`}
        sub="Live reading"
      />
      <ContextCard
        icon={
          weather.is_rainy ? (
            <CloudRain className="w-5 h-5 text-blue-400" />
          ) : (
            <Cloud className="w-5 h-5" />
          )
        }
        label="Precipitation"
        value={weather.is_rainy ? 'Raining' : 'Dry'}
        sub="Current conditions"
      />
      <ContextCard
        icon={<Car className="w-5 h-5" />}
        label="Traffic Flow"
        value={`${flowPct}%`}
        sub={congestionLabel}
      />
      <ContextCard
        icon={<Car className="w-5 h-5 text-surge-medium" />}
        label="Congestion Ratio"
        value={traffic.traffic_flow_ratio.toFixed(3)}
        sub="TomTom flow ratio"
      />
    </div>
  )
}
