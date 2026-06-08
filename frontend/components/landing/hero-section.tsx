'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { Zap, ArrowRight, MapPin } from 'lucide-react'

export function HeroSection() {
  return (
    <section className="relative min-h-[88vh] flex items-center justify-center overflow-hidden px-4">
      {/* Animated gradient background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-accent-blue/5" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-blue/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-surge-medium/10 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      <div className="max-w-4xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-blue/30 bg-accent-blue/10 text-accent-blue text-xs font-medium mb-8">
            <Zap className="w-3.5 h-3.5" />
            Real-time ML Inference · LightGBM on Azure ML
          </div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary mb-6 leading-tight"
        >
          NYC Ride-Hail
          <br />
          <span className="bg-gradient-to-r from-accent-blue to-surge-medium bg-clip-text text-transparent">
            Surge Predictor
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-lg text-text-secondary mb-10 max-w-2xl mx-auto"
        >
          Production-grade surge multiplier predictions for 21 NYC zones. Powered by
          live weather, traffic, and holiday signals — refreshed every 10 minutes.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Link
            href="/predict"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-accent-blue text-white font-medium hover:bg-accent-blue/90 transition-all shadow-lg shadow-accent-blue/25 hover:shadow-accent-blue/40"
          >
            <Zap className="w-4 h-4" />
            Get a Prediction
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/map"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl border border-border-subtle bg-surface text-text-primary font-medium hover:bg-surface-elevated transition-all"
          >
            <MapPin className="w-4 h-4" />
            View Live Map
          </Link>
        </motion.div>
      </div>
    </section>
  )
}
