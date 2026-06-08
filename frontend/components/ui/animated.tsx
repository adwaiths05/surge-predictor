'use client'

import { motion } from 'framer-motion'

interface FadeInProps {
  delay?: number
  duration?: number
  children: React.ReactNode
  className?: string
}

export function FadeIn({
  children,
  delay = 0,
  duration = 0.4,
  className,
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

export function SlideIn({
  children,
  delay = 0,
  duration = 0.4,
  className,
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
