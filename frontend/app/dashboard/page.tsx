import { FadeIn } from '@/components/ui/animated'
import { KPICards } from '@/components/dashboard/kpi-cards'
import { InferenceVolumeChart } from '@/components/dashboard/inference-chart'
import { LatencyChart } from '@/components/dashboard/latency-chart'
import { DriftMonitor } from '@/components/dashboard/drift-monitor'
import { ModelMetadataCard } from '@/components/dashboard/model-metadata'
import { ActivityLog } from '@/components/dashboard/activity-log'

export default function DashboardPage() {
  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <FadeIn>
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-semibold text-text-primary mb-2">
              Analytics Dashboard
            </h1>
            <p className="text-text-secondary">
              MLOps monitoring and model performance metrics
            </p>
          </div>
        </FadeIn>

        {/* KPI Cards */}
        <div className="mb-8">
          <KPICards />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <InferenceVolumeChart />
          <LatencyChart />
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <DriftMonitor />
          <ModelMetadataCard />
          <ActivityLog />
        </div>
      </div>
    </div>
  )
}
