// ─── Backend response types ────────────────────────────────────────────────

export interface Zone {
  zone_name: string
  borough?: string
}

export interface WeatherContext {
  temperature: number
  is_rainy: boolean
}

export interface TrafficContext {
  traffic_flow_ratio: number
}

export interface PredictionResponse {
  zone_name: string
  borough: string
  surge_multiplier: number
  confidence: string
  weather: WeatherContext
  traffic: TrafficContext
  timestamp: string
}

export interface HeatmapZonePoint {
  zone_name: string
  borough: string
  lat: number
  lon: number
  surge_multiplier: number
}

export interface HeatmapResponse {
  generated_at: string
  points: HeatmapZonePoint[]
}

export interface HistoryPoint {
  date: string
  surge_multiplier: number
}

export interface HistoryResponse {
  zone_name: string
  days: number
  series: HistoryPoint[]
}

export interface ModelMetadataResponse {
  model_version: string
  training_date: string
  metrics: Record<string, number>
}

export interface ModelFeatureItem {
  feature: string
  importance: number
}

export interface ModelFeaturesResponse {
  top_features: ModelFeatureItem[]
}

export interface DriftSummaryResponse {
  drift_score: number
  status: string
}

export interface AnalyticsKpisResponse {
  inference_count_24h: number
  avg_latency_ms: number
  p95_latency_ms: number
}

export interface ApiHealthResponse {
  status: string
  service: string
  ready: boolean
}

// For backwards compatibility — ZonesResponse is just string[]
export type ZonesResponse = string[]
