'use client'

import { motion } from 'framer-motion'
import { CloudSun, BarChart2, Zap, RefreshCw } from 'lucide-react'

const STEPS = [
  {
    icon: <CloudSun className="w-6 h-6" />,
    title: 'Live Signal Ingestion',
    desc: 'Weather (1h cache), traffic (3h cache), and holiday (1d cache) data pulled in real-time from Open-Meteo, TomTom, and Calendarific.',
  },
  {
    icon: <BarChart2 className="w-6 h-6" />,
    title: 'Feature Engineering',
    desc: '20 features built per zone: datetime signals, rain history, congestion composites, demand growth rate, and encoded zone metadata.',
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: 'LightGBM Inference',
    desc: 'A trained LightGBM gradient boosting model predicts surge multipliers per zone with sub-100ms end-to-end latency.',
  },
  {
    icon: <RefreshCw className="w-6 h-6" />,
    title: 'Auto-Refresh Heatmap',
    desc: 'The live heatmap refreshes every 10 minutes across all 21 zones concurrently, with graceful fallbacks on API failures.',
  },
]

export function HowItWorks() {
  return (
    <section className="py-20 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-text-primary mb-3">
            How It Works
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto">
            End-to-end pipeline from live data to ML predictions
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.12, duration: 0.5 }}
              className="p-6 rounded-xl border border-border-subtle bg-surface hover:bg-surface-elevated transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center text-accent-blue mb-4">
                {step.icon}
              </div>
              <h3 className="font-semibold text-text-primary mb-2">{step.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
