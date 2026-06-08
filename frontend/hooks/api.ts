'use client'

import useSWR from 'swr'
import type {
  PredictionResponse,
  HeatmapResponse,
  HistoryResponse,
  ModelMetadataResponse,
  ModelFeaturesResponse,
  DriftSummaryResponse,
  AnalyticsKpisResponse,
  ZonesResponse,
} from '@/lib/types'
import { API_ROUTES } from '@/lib/api'

const jsonFetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`Fetch ${url} failed: ${r.status}`)
    return r.json()
  })

// ─── Heatmap — refreshes every 10 minutes ────────────────────────────────
export function useHeatmap() {
  const { data, error, isLoading, mutate } = useSWR<HeatmapResponse>(
    API_ROUTES.heatmap,
    jsonFetcher,
    {
      refreshInterval: 10 * 60 * 1000, // 10 minutes
      revalidateOnFocus: false,
    },
  )
  return { heatmap: data, error, isLoading, refresh: mutate }
}

// ─── Zones list — fetched once ────────────────────────────────────────────
export function useZones() {
  const { data, error, isLoading } = useSWR<ZonesResponse>(
    API_ROUTES.zones,
    jsonFetcher,
    { revalidateOnFocus: false },
  )
  return { zones: data ?? [], error, isLoading }
}

// ─── Analytics KPIs — refreshes every 60 seconds ─────────────────────────
export function useKpis() {
  const { data, error, isLoading } = useSWR<AnalyticsKpisResponse>(
    API_ROUTES.kpis,
    jsonFetcher,
    { refreshInterval: 60_000 },
  )
  return { kpis: data, error, isLoading }
}

// ─── Model metadata — static, fetched once ───────────────────────────────
export function useModelMetadata() {
  const { data, error, isLoading } = useSWR<ModelMetadataResponse>(
    API_ROUTES.modelMetadata,
    jsonFetcher,
    { revalidateOnFocus: false },
  )
  return { metadata: data, error, isLoading }
}

// ─── Model features — static, fetched once ───────────────────────────────
export function useModelFeatures() {
  const { data, error, isLoading } = useSWR<ModelFeaturesResponse>(
    API_ROUTES.modelFeatures,
    jsonFetcher,
    { revalidateOnFocus: false },
  )
  return { features: data, error, isLoading }
}

// ─── Drift summary — refreshes every 5 minutes ───────────────────────────
export function useDriftSummary() {
  const { data, error, isLoading } = useSWR<DriftSummaryResponse>(
    API_ROUTES.drift,
    jsonFetcher,
    { refreshInterval: 5 * 60 * 1000 },
  )
  return { drift: data, error, isLoading }
}

// ─── Zone history — depends on selected zone ─────────────────────────────
export function useHistory(zone: string | null, days = 7) {
  const key = zone ? API_ROUTES.history(zone, days) : null
  const { data, error, isLoading } = useSWR<HistoryResponse>(
    key,
    jsonFetcher,
    { revalidateOnFocus: false },
  )
  return { history: data, error, isLoading }
}

// ─── Prediction — imperative POST, not SWR ───────────────────────────────
export function usePrediction() {
  const predict = async (zone_name: string): Promise<PredictionResponse> => {
    const res = await fetch(API_ROUTES.predict, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zone_name }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail ?? `Prediction failed: ${res.status}`)
    }
    return res.json()
  }
  return { predict }
}
