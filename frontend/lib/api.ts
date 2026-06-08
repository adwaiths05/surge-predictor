import type {
  PredictionResponse,
  HeatmapResponse,
  HistoryResponse,
  ModelMetadataResponse,
  ModelFeaturesResponse,
  DriftSummaryResponse,
  AnalyticsKpisResponse,
  ApiHealthResponse,
  ZonesResponse,
} from '@/lib/types'

// When running server-side (Next.js API routes), use the full backend URL.
// When running client-side, use the Next.js proxy routes under /api/*.
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

// ─── Client-side fetchers (via Next.js /api proxy) ────────────────────────
// These are the URLs used from the browser.

export const API_ROUTES = {
  predict: '/api/predict',
  zones: '/api/zones',
  heatmap: '/api/map/heatmap',
  history: (zone: string, days = 7) =>
    `/api/history?zone=${encodeURIComponent(zone)}&days=${days}`,
  kpis: '/api/analytics/kpis',
  modelMetadata: '/api/model/metadata',
  modelFeatures: '/api/model/features',
  drift: '/api/drift',
  health: '/api/health',
} as const

// ─── Server-side fetchers (direct to FastAPI) ─────────────────────────────
// Used inside Next.js route handlers.

async function serverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BACKEND_URL}${path}`
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`Backend ${path} failed ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function serverFetchZones(): Promise<ZonesResponse> {
  return serverFetch<ZonesResponse>('/zones')
}

export async function serverFetchHeatmap(): Promise<HeatmapResponse> {
  return serverFetch<HeatmapResponse>('/map/heatmap')
}

export async function serverFetchHistory(
  zone: string,
  days = 7,
): Promise<HistoryResponse> {
  return serverFetch<HistoryResponse>(
    `/history?zone=${encodeURIComponent(zone)}&days=${days}`,
  )
}

export async function serverFetchKpis(): Promise<AnalyticsKpisResponse> {
  return serverFetch<AnalyticsKpisResponse>('/analytics/kpis')
}

export async function serverFetchModelMetadata(): Promise<ModelMetadataResponse> {
  return serverFetch<ModelMetadataResponse>('/model/metadata')
}

export async function serverFetchModelFeatures(): Promise<ModelFeaturesResponse> {
  return serverFetch<ModelFeaturesResponse>('/model/features')
}

export async function serverFetchDrift(): Promise<DriftSummaryResponse> {
  return serverFetch<DriftSummaryResponse>('/drift/summary')
}

export async function serverFetchHealth(): Promise<ApiHealthResponse> {
  return serverFetch<ApiHealthResponse>('/health')
}

export async function serverPredict(
  zone_name: string,
): Promise<PredictionResponse> {
  return serverFetch<PredictionResponse>('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone_name }),
  })
}
