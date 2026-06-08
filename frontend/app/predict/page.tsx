'use client'

import { Zap } from 'lucide-react'
import { format } from 'date-fns'
import { Button } from '@/components/ui/button'
import { FadeIn } from '@/components/ui/animated'
import { ZoneSelector } from '@/components/prediction/zone-selector'
import { DateTimePicker } from '@/components/prediction/datetime-picker'
import { PredictionResultCard } from '@/components/prediction/result-card'
import { FeatureImportanceChart } from '@/components/prediction/feature-chart'
import { HistorySparkline } from '@/components/prediction/history-sparkline'
import { ContextCards } from '@/components/prediction/context-cards'
import { usePredictionStore } from '@/store'
import { usePrediction } from '@/hooks/api'

export default function PredictPage() {
  const { 
    selectedZone, 
    selectedDateTime, 
    isLoading, 
    setIsLoading, 
    setPrediction, 
    setError 
  } = usePredictionStore()
  const { predict } = usePrediction()

  const handlePredict = async () => {
    if (!selectedZone) return
    
    setIsLoading(true)
    setError(null)
    
    try {
      const data = await predict(selectedZone.zone_name)
      setPrediction(data)
    } catch (err) {
      setError('Unable to reach prediction service')
    }
  }

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <FadeIn>
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-semibold text-text-primary mb-2">
              Surge Prediction
            </h1>
            <p className="text-text-secondary">
              Select a zone and time to predict the surge multiplier
            </p>
          </div>
        </FadeIn>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Panel - Input Form */}
          <FadeIn delay={0.1}>
            <div className="rounded-xl border border-border-subtle bg-surface p-6 space-y-6">
              <ZoneSelector />
              <DateTimePicker />
              
              <Button 
                onClick={handlePredict}
                disabled={!selectedZone || isLoading}
                className="w-full bg-accent-blue hover:bg-accent-blue/90 text-white"
                size="lg"
              >
                <Zap className="w-4 h-4 mr-2" />
                {isLoading ? 'Predicting...' : 'Get Prediction'}
              </Button>
            </div>
          </FadeIn>

          {/* Right Panel - Results */}
          <FadeIn delay={0.2}>
            <div className="space-y-6">
              <PredictionResultCard />
              <ContextCards />
            </div>
          </FadeIn>
        </div>

        {/* Bottom Section - Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          <FeatureImportanceChart />
          <HistorySparkline />
        </div>
      </div>
    </div>
  )
}
