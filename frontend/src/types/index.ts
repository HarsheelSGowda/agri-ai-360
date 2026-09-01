export interface User {
  id: number
  name: string
  email: string
  location?: string | null
  preferred_language: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Farm {
  id: number
  name: string
  location: string
  area_acres: number
  soil_type: string
  irrigation_available: boolean
  created_at: string
}

export interface SoilRecord {
  id?: number
  farm_id?: number
  nitrogen: number
  phosphorus: number
  potassium: number
  ph: number
  soil_type: string
  organic_carbon?: number | null
  moisture?: number | null
  electrical_conductivity?: number | null
  created_at?: string
}

export interface SoilHealthResult {
  score: number
  breakdown: {
    nitrogen: number
    phosphorus: number
    potassium: number
    ph: number
  }
  insights: string[]
}

export interface WeatherData {
  temperature_c: number
  humidity_pct: number
  rainfall_mm: number
  wind_kmh: number
  condition: string
  forecast: { day: string; temp_c: number; condition: string }[]
  source: 'mock' | 'live'
}

export interface CropPredictionInput {
  nitrogen: number
  phosphorus: number
  potassium: number
  temperature: number
  humidity: number
  ph: number
  rainfall: number
}

export interface CropRankingItem {
  crop: string
  probability: number
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface TopCropsResponse {
  top_crops: CropRankingItem[]
  model_used: string
  model_version: string
  input: CropPredictionInput
}

export interface ShapContribution {
  feature: string
  value: number
  contribution: number
}

export interface ExplanationResponse {
  crop: string
  contributions: ShapContribution[]
  base_value: number
  predicted_value: number
  narrative: string
  method: 'shap'
}

export interface ModelMetrics {
  algorithm: string
  status: 'trained' | 'not_evaluated'
  accuracy: number | null
  precision: number | null
  recall: number | null
  f1_score: number | null
  trained_at: string | null
}

export interface ModelPerformanceResponse {
  models: ModelMetrics[]
  active_model: string
  dataset_records: number
  dataset_source: string
  feature_importance: { feature: string; importance: number }[] | null
  confusion_matrix: { labels: string[]; matrix: number[][] } | null
  classification_report?: Record<string, { precision: number; recall: number; f1_score: number; support: number }>
}

export interface PredictionHistoryItem {
  id: number
  farm_id: number
  farm_name: string
  crop: string
  score: number
  created_at: string
  soil_summary: string
  weather_summary: string
}

export interface YieldOptionsResponse {
  states: string[]
  seasons: string[]
  supported_crops: string[]
  dataset_records: number
  active_model: string | null
  active_model_r2: number | null
}

export interface YieldPredictionResponse {
  supported: boolean
  crop: string
  mapped_crop: string | null
  state: string | null
  season: string | null
  predicted_yield_tonnes_per_ha: number | null
  predicted_yield_quintal_per_acre: number | null
  model_used: string | null
  r2_score: number | null
  mae: number | null
  reason: string | null
}

export interface RiskBreakdown {
  overall: 'LOW' | 'MEDIUM' | 'HIGH'
  weather_risk: 'LOW' | 'MEDIUM' | 'HIGH'
  soil_risk: 'LOW' | 'MEDIUM' | 'HIGH'
  water_risk: 'LOW' | 'MEDIUM' | 'HIGH'
  disease_risk: 'LOW' | 'MEDIUM' | 'HIGH'
  notes: string[]
  is_prototype: true
}
