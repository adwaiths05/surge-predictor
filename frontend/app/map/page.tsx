'use client'

import { useState, useMemo, useCallback, useRef } from 'react'
import { useHeatmap } from '@/hooks/api'
import { motion, AnimatePresence } from 'framer-motion'
import { MapPin, TrendingUp, TrendingDown, Clock, X, RefreshCw, Layers } from 'lucide-react'
import { cn } from '@/lib/utils'
import { FadeIn } from '@/components/ui/animated'
import { Slider } from '@/components/ui/slider'
import { Skeleton } from '@/components/ui/skeleton'
import { format } from 'date-fns'
import Map, { Marker, Popup, NavigationControl } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useTheme } from 'next-themes'

/* ─── colour helpers ────────────────────────────────────────── */
function getSurgeColor(surge: number): string {
  if (surge < 1.3) return '#22D3EE'
  if (surge < 1.7) return '#84CC16'
  if (surge < 2.0) return '#FBBF24'
  if (surge < 2.5) return '#F97316'
  return '#EF4444'
}

function getSurgeLabel(surge: number): string {
  if (surge < 1.3) return 'Normal'
  if (surge < 1.7) return 'Moderate'
  if (surge < 2.0) return 'High'
  if (surge < 2.5) return 'Very High'
  return 'Extreme'
}

/* ─── zone data ─────────────────────────────────────────────── */
const ZONES: Record<string, { lat: number; lng: number; borough: string }> = {
  'Central Park':            { lat: 40.7825, lng: -73.9656, borough: 'Manhattan' },
  'Clinton East':            { lat: 40.7622, lng: -73.9899, borough: 'Manhattan' },
  'Clinton West':            { lat: 40.7667, lng: -73.9939, borough: 'Manhattan' },
  'Chinatown':               { lat: 40.7131, lng: -73.9983, borough: 'Manhattan' },
  'Battery Park City':       { lat: 40.7116, lng: -74.0161, borough: 'Manhattan' },
  'Alphabet City':           { lat: 40.7242, lng: -73.9770, borough: 'Manhattan' },
  'Central Harlem':          { lat: 40.8042, lng: -73.9521, borough: 'Manhattan' },
  'Brooklyn Heights':        { lat: 40.6962, lng: -73.9953, borough: 'Brooklyn'  },
  'Bushwick North':          { lat: 40.6991, lng: -73.9166, borough: 'Brooklyn'  },
  'Bushwick South':          { lat: 40.6963, lng: -73.9259, borough: 'Brooklyn'  },
  'Bedford':                 { lat: 40.6920, lng: -73.9492, borough: 'Brooklyn'  },
  'Boerum Hill':             { lat: 40.6856, lng: -73.9865, borough: 'Brooklyn'  },
  'Astoria':                 { lat: 40.7611, lng: -73.9215, borough: 'Queens'    },
  'Astoria Park':            { lat: 40.7786, lng: -73.9232, borough: 'Queens'    },
  'Baisley Park':            { lat: 40.6781, lng: -73.7917, borough: 'Queens'    },
  'Briarwood/Jamaica Hills': { lat: 40.7109, lng: -73.8073, borough: 'Queens'    },
  'Bayside':                 { lat: 40.7612, lng: -73.7717, borough: 'Queens'    },
  'Bedford Park':            { lat: 40.8688, lng: -73.8869, borough: 'Bronx'     },
  'Belmont':                 { lat: 40.8578, lng: -73.8860, borough: 'Bronx'     },
  'Newark Airport':          { lat: 40.6895, lng: -74.1768, borough: 'EWR'       },
  'Jamaica Bay':             { lat: 40.6257, lng: -73.8261, borough: 'Queens'    },
}

/* ─── map styles ─────────────────────────────────────────────── */
// Free OpenFreeMap tile styles — no token required
const MAP_STYLES = {
  dark:  'https://tiles.openfreemap.org/styles/dark',
  light: 'https://tiles.openfreemap.org/styles/positron',
}

/* ─── subcomponents ─────────────────────────────────────────── */
interface ZoneSidebarProps {
  zoneName: string
  surge: number
  onClose: () => void
}

function ZoneSidebar({ zoneName, surge, onClose }: ZoneSidebarProps) {
  const zone = ZONES[zoneName]
  const color = getSurgeColor(surge)
  const label = getSurgeLabel(surge)

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      className="absolute top-0 right-0 w-72 h-full bg-surface border-l border-border-subtle z-20 overflow-y-auto shadow-2xl"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-text-primary">Zone Details</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-elevated transition-colors text-text-secondary hover:text-text-primary"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Zone name */}
          <div>
            <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">Zone</p>
            <p className="text-xl font-bold text-text-primary">{zoneName}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <MapPin className="w-3.5 h-3.5 text-text-secondary" />
              <p className="text-sm text-text-secondary">{zone?.borough}</p>
            </div>
          </div>

          {/* Surge multiplier */}
          <div className="p-4 rounded-xl border" style={{ borderColor: color + '40', backgroundColor: color + '10' }}>
            <p className="text-xs text-text-secondary mb-2">Current Surge</p>
            <div className="flex items-end gap-3">
              <span className="text-5xl font-bold tabular-nums" style={{ color }}>
                {surge.toFixed(2)}×
              </span>
            </div>
            <span
              className="mt-2 inline-block px-2.5 py-0.5 rounded-full text-xs font-medium"
              style={{ backgroundColor: color + '20', color }}
            >
              {label}
            </span>
          </div>

          {/* Surge bar */}
          <div>
            <div className="flex justify-between text-xs text-text-secondary mb-1.5">
              <span>Intensity</span>
              <span>{Math.round((Math.min(surge, 3) - 1) / 2 * 100)}%</span>
            </div>
            <div className="h-2 rounded-full bg-surface-elevated overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.round((Math.min(surge, 3) - 1) / 2 * 100)}%`,
                  backgroundColor: color,
                }}
              />
            </div>
          </div>

          {/* Est metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-surface-elevated text-center">
              <p className="text-xs text-text-secondary mb-1">Est. Pickups</p>
              <p className="text-lg font-semibold text-text-primary tabular-nums">
                {Math.floor(100 + surge * 50)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-surface-elevated text-center">
              <p className="text-xs text-text-secondary mb-1">Avg Wait</p>
              <p className="text-lg font-semibold text-text-primary tabular-nums">
                {Math.floor(2 + surge * 2)} min
              </p>
            </div>
          </div>

          {/* Coordinates */}
          <div className="p-3 rounded-lg bg-surface-elevated">
            <p className="text-xs text-text-secondary mb-1">Coordinates</p>
            <p className="text-xs font-mono text-text-primary">
              {zone?.lat.toFixed(4)}°N, {Math.abs(zone?.lng).toFixed(4)}°W
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function MapLegend() {
  const LEVELS = [
    { label: '< 1.3×',  color: '#22D3EE', name: 'Normal' },
    { label: '1.3–1.7×', color: '#84CC16', name: 'Moderate' },
    { label: '1.7–2.0×', color: '#FBBF24', name: 'High' },
    { label: '2.0–2.5×', color: '#F97316', name: 'Very High' },
    { label: '> 2.5×',  color: '#EF4444', name: 'Extreme' },
  ]
  return (
    <div className="absolute bottom-8 left-4 p-3 rounded-xl bg-surface/95 border border-border-subtle backdrop-blur-sm z-10 shadow-lg">
      <div className="flex items-center gap-1.5 mb-2">
        <Layers className="w-3.5 h-3.5 text-text-secondary" />
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Surge Multiplier</p>
      </div>
      <div className="space-y-1.5">
        {LEVELS.map((l) => (
          <div key={l.color} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: l.color }} />
            <span className="text-xs text-text-secondary">{l.name}</span>
            <span className="text-xs text-text-secondary/60 ml-auto pl-3">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── main page ─────────────────────────────────────────────── */
export default function MapPage() {
  const [selectedHour, setSelectedHour] = useState(new Date().getHours())
  const [selectedZone, setSelectedZone] = useState<string | null>(null)
  const [hoveredZone, setHoveredZone] = useState<string | null>(null)
  const { resolvedTheme } = useTheme()

  const { heatmap, isLoading: heatmapLoading, refresh } = useHeatmap()

  const surgeMap = useMemo(() => {
    const m: Record<string, number> = {}
    heatmap?.points?.forEach((p) => { m[p.zone_name] = p.surge_multiplier })
    return m
  }, [heatmap])

  const selectedSurge = selectedZone ? surgeMap[selectedZone] ?? 1.0 : null
  const mapStyle = resolvedTheme === 'light' ? MAP_STYLES.light : MAP_STYLES.dark

  return (
    <div className="h-[calc(100vh-3.5rem)] relative overflow-hidden">

      {/* ── Real MapLibre map ────────────────────────────────── */}
      <Map
        initialViewState={{
          longitude: -73.97,
          latitude:  40.73,
          zoom: 10.5,
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={mapStyle}
        attributionControl={false}
      >
        <NavigationControl position="bottom-right" />

        {/* Zone markers */}
        {!heatmapLoading && Object.entries(ZONES).map(([name, zone]) => {
          const surge = surgeMap[name] ?? 1.0
          const color = getSurgeColor(surge)
          const isSelected = selectedZone === name
          const isHovered = hoveredZone === name
          const radius = 12 + Math.max(0, (surge - 1) * 8)

          return (
            <Marker
              key={name}
              longitude={zone.lng}
              latitude={zone.lat}
              anchor="center"
            >
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: Math.random() * 0.3, type: 'spring' }}
                style={{ position: 'relative' }}
                onMouseEnter={() => setHoveredZone(name)}
                onMouseLeave={() => setHoveredZone(null)}
                onClick={() => setSelectedZone(name === selectedZone ? null : name)}
              >
                {/* Pulse ring */}
                {(isHovered || isSelected) && (
                  <motion.div
                    className="absolute rounded-full"
                    style={{
                      width: radius * 2.5,
                      height: radius * 2.5,
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      backgroundColor: color + '25',
                      border: `2px solid ${color}60`,
                    }}
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}

                {/* Main dot */}
                <div
                  className="rounded-full cursor-pointer relative"
                  style={{
                    width: radius * 2,
                    height: radius * 2,
                    backgroundColor: color,
                    opacity: isSelected ? 1 : 0.88,
                    boxShadow: isSelected
                      ? `0 0 0 3px white, 0 0 ${radius * 2}px ${color}80`
                      : `0 0 ${radius}px ${color}60`,
                    transition: 'box-shadow 0.2s, opacity 0.2s',
                  }}
                />
              </motion.div>
            </Marker>
          )
        })}

        {/* Hover popup */}
        {hoveredZone && !selectedZone && ZONES[hoveredZone] && (
          <Popup
            longitude={ZONES[hoveredZone].lng}
            latitude={ZONES[hoveredZone].lat}
            anchor="bottom"
            offset={20}
            closeButton={false}
            closeOnClick={false}
            style={{ zIndex: 30 }}
          >
            <div className="p-2.5 min-w-[160px]">
              <p className="font-semibold text-text-primary text-sm">{hoveredZone}</p>
              <p className="text-xs text-text-secondary">{ZONES[hoveredZone].borough}</p>
              <div className="flex items-center justify-between mt-1.5">
                <span className="text-xs text-text-secondary">Surge</span>
                <span
                  className="font-bold text-sm tabular-nums"
                  style={{ color: getSurgeColor(surgeMap[hoveredZone] ?? 1) }}
                >
                  {(surgeMap[hoveredZone] ?? 1).toFixed(2)}×
                </span>
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* ── Time-slider panel ────────────────────────────────── */}
      <FadeIn delay={0.2}>
        <div className="absolute top-4 left-4 right-4 md:left-auto md:right-4 md:w-80 p-4 rounded-xl bg-surface/95 border border-border-subtle backdrop-blur-md z-10 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-accent-blue" />
              <span className="text-sm font-semibold text-text-primary">
                Time: {String(selectedHour).padStart(2, '0')}:00
              </span>
            </div>
            <button
              onClick={() => refresh()}
              className="p-1.5 rounded-lg hover:bg-surface-elevated text-text-secondary hover:text-accent-blue transition-colors"
              title="Refresh heatmap"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <Slider
            value={[selectedHour]}
            onValueChange={([v]) => setSelectedHour(v)}
            min={0}
            max={23}
            step={1}
            className="w-full"
          />
          <div className="flex justify-between mt-2 text-xs text-text-secondary">
            <span>12 AM</span>
            <span>12 PM</span>
            <span>11 PM</span>
          </div>
          {heatmap?.generated_at && (
            <p className="text-xs text-text-secondary mt-3 border-t border-border-subtle pt-2">
              Updated: {format(new Date(heatmap.generated_at), 'HH:mm:ss')} · auto-refreshes every 10 min
            </p>
          )}
          {heatmapLoading && (
            <p className="text-xs text-accent-blue mt-2 animate-pulse">Loading surge data…</p>
          )}
        </div>
      </FadeIn>

      {/* ── Legend ───────────────────────────────────────────── */}
      <MapLegend />

      {/* ── Zone sidebar ─────────────────────────────────────── */}
      <AnimatePresence>
        {selectedZone && selectedSurge !== null && (
          <ZoneSidebar
            key={selectedZone}
            zoneName={selectedZone}
            surge={selectedSurge}
            onClose={() => setSelectedZone(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
