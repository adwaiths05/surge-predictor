import { create } from 'zustand'
import type { Zone, PredictionResponse } from '@/lib/types'

interface PredictionState {
  selectedZone: Zone | null
  selectedDateTime: Date
  prediction: PredictionResponse | null
  isLoading: boolean
  error: string | null
  setSelectedZone: (zone: Zone | null) => void
  setSelectedDateTime: (date: Date) => void
  setPrediction: (prediction: PredictionResponse | null) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

export const usePredictionStore = create<PredictionState>((set) => ({
  selectedZone: null,
  selectedDateTime: new Date(Date.now() + 3600000), // Default to 1 hour from now
  prediction: null,
  isLoading: false,
  error: null,
  setSelectedZone: (zone) => set({ selectedZone: zone, prediction: null, error: null }),
  setSelectedDateTime: (date) => set({ selectedDateTime: date, prediction: null, error: null }),
  setPrediction: (prediction) => set({ prediction, isLoading: false, error: null }),
  setIsLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),
  reset: () => set({ 
    selectedZone: null, 
    selectedDateTime: new Date(Date.now() + 3600000), 
    prediction: null, 
    isLoading: false, 
    error: null 
  }),
}))

interface MapState {
  selectedHour: number
  hoveredZone: number | null
  selectedZoneId: number | null
  setSelectedHour: (hour: number) => void
  setHoveredZone: (zoneId: number | null) => void
  setSelectedZoneId: (zoneId: number | null) => void
}

export const useMapStore = create<MapState>((set) => ({
  selectedHour: new Date().getHours(),
  hoveredZone: null,
  selectedZoneId: null,
  setSelectedHour: (hour) => set({ selectedHour: hour }),
  setHoveredZone: (zoneId) => set({ hoveredZone: zoneId }),
  setSelectedZoneId: (zoneId) => set({ selectedZoneId: zoneId }),
}))
