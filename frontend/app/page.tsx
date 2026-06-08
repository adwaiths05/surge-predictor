import { HeroSection } from '@/components/landing/hero-section'
import { KPIStrip } from '@/components/landing/kpi-strip'
import { HowItWorks } from '@/components/landing/how-it-works'
import { TechStackStrip } from '@/components/landing/tech-stack-strip'

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <HeroSection />
      <KPIStrip />
      <HowItWorks />
      <TechStackStrip />
    </div>
  )
}
