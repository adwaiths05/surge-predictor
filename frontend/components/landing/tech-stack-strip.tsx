'use client'

import { motion } from 'framer-motion'

const STACK = [
  { name: 'LightGBM', cat: 'Model', color: '#3B82F6' },
  { name: 'FastAPI', cat: 'Backend', color: '#22D3EE' },
  { name: 'Next.js', cat: 'Frontend', color: '#FFFFFF' },
  { name: 'Open-Meteo', cat: 'Weather', color: '#84CC16' },
  { name: 'TomTom', cat: 'Traffic', color: '#F97316' },
  { name: 'Calendarific', cat: 'Holidays', color: '#FBBF24' },
  { name: 'Azure ML', cat: 'MLOps', color: '#60A5FA' },
  { name: 'Recharts', cat: 'Charts', color: '#A78BFA' },
]

export function TechStackStrip() {
  return (
    <section className="py-16 px-4 border-t border-border-subtle bg-surface/40">
      <div className="max-w-4xl mx-auto">
        <p className="text-center text-xs font-medium text-text-secondary uppercase tracking-widest mb-8">
          Tech Stack
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {STACK.map((tech, i) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              className="flex items-center gap-2 px-4 py-2 rounded-full border border-border-subtle bg-surface text-sm"
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: tech.color }}
              />
              <span className="text-text-primary font-medium">{tech.name}</span>
              <span className="text-text-secondary text-xs">{tech.cat}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
