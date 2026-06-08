'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ThemeToggle } from './theme-toggle'

export function Header() {
  const pathname = usePathname()

  if (pathname === '/') {
    return null
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur-sm">
      <nav className="mx-auto flex h-14 max-w-6xl items-center gap-5 px-4 text-sm">
        <Link href="/" className="font-semibold text-text-primary">SurgeCast</Link>
        <Link href="/predict" className="text-text-secondary hover:text-text-primary">Predict</Link>
        <Link href="/map" className="text-text-secondary hover:text-text-primary">Map</Link>
        <Link href="/dashboard" className="text-text-secondary hover:text-text-primary">Dashboard</Link>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </nav>
    </header>
  )
}
