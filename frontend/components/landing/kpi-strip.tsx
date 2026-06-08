'use client'

import { motion } from 'framer-motion'

const STATS = [
  { value: '21', label: 'NYC Zones', sub: 'covered' },
  { value: '10 min', label: 'Refresh', sub: 'interval' },
  { value: 'Live', label: 'Weather + Traffic', sub: 'signals' },
  { value: '87%', label: 'R² Score', sub: 'model accuracy' },
]

export function KPIStrip() {
  return (
    <section className="border-y border-border-subtle bg-surface/60 backdrop-blur-sm py-8 px-4">
      <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
        {STATS.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
            className="text-center"
          >
            <p className="text-2xl sm:text-3xl font-bold text-text-primary mb-0.5">
              {stat.value}
            </p>
            <p className="text-xs text-text-secondary font-medium">{stat.label}</p>
            <p className="text-xs text-text-secondary/60">{stat.sub}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
