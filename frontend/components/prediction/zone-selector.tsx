'use client'

import { MapPin, Search } from 'lucide-react'
import { useState, useCallback } from 'react'
import { useZones } from '@/hooks/api'
import { usePredictionStore } from '@/store'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export function ZoneSelector() {
  const { zones, isLoading } = useZones()
  const { selectedZone, setSelectedZone } = usePredictionStore()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const filtered = zones.filter((z) =>
    z.toLowerCase().includes(query.toLowerCase()),
  )

  const handleSelect = useCallback(
    (zone: string) => {
      setSelectedZone({ zone_name: zone })
      setQuery(zone)
      setOpen(false)
    },
    [setSelectedZone],
  )

  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-4 w-20 mb-2" />
        <Skeleton className="h-10 w-full rounded-lg" />
      </div>
    )
  }

  return (
    <div className="relative">
      <label className="block text-xs text-text-secondary mb-2 font-medium">
        Select Zone
      </label>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary pointer-events-none" />
        <input
          type="text"
          placeholder="Search zones…"
          value={selectedZone ? selectedZone.zone_name : query}
          onFocus={() => {
            setQuery('')
            setOpen(true)
            if (selectedZone) setSelectedZone(null)
          }}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          className="w-full pl-9 pr-4 py-2.5 text-sm rounded-lg border border-border-subtle bg-surface-elevated text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent-blue/40 focus:border-accent-blue transition-all"
        />
      </div>

      {open && (
        <div className="absolute top-full mt-1 w-full max-h-60 overflow-y-auto z-30 rounded-lg border border-border-subtle bg-surface shadow-xl">
          {filtered.length === 0 ? (
            <p className="px-3 py-3 text-sm text-text-secondary">No zones found</p>
          ) : (
            filtered.map((zone) => (
              <button
                key={zone}
                onMouseDown={() => handleSelect(zone)}
                className={cn(
                  'w-full text-left px-3 py-2.5 text-sm flex items-center gap-2 hover:bg-surface-elevated transition-colors',
                  selectedZone?.zone_name === zone && 'bg-accent-blue/10 text-accent-blue',
                )}
              >
                <MapPin className="w-3.5 h-3.5 shrink-0 text-text-secondary" />
                {zone}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
