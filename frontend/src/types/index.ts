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

export interface ProfitOptionsResponse {
  supported_crops: string[]
  price_year: string
}

export interface ProfitPredictionResponse {
  supported: boolean
  crop: string
  mapped_crop: string | null
  state: string | null
  season: string | null
  yield_tonnes_per_ha: number | null
  price_rs_per_quintal: number | null
  price_source: 'state' | 'national_fallback' | null
  cost_per_acre: number | null
  revenue_per_acre: number | null
  profit_per_acre: number | null
  revenue_per_ha: number | null
  profit_per_ha: number | null
  margin_pct: number | null
  total_farm_profit: number | null
  reason: string | null
}

export interface WaterOptionsResponse {
  supported_crops: string[]
  states: string[]
}

export interface WaterRequirementResponse {
  supported: boolean
  crop: string
  kc_mid: number | null
  kc_category: 'specific' | 'generic_legume' | null
  kc_source_row: string | null
  kc_note: string | null
  state: string | null
  latitude_deg: number | null
  month: string | null
  p_value: number | null
  reference_et0_mm_per_day: number | null
  crop_water_use_mm_per_day: number | null
  effective_rainfall_mm_per_day: number | null
  net_irrigation_mm_per_day: number | null
  net_irrigation_liters_per_acre_per_day: number | null
  net_irrigation_liters_total_per_day: number | null
  reason: string | null
}

export interface YieldRiskOptionsResponse {
  supported_crops: string[]
  active_model: string | null
  active_model_accuracy: number | null
  dataset_records: number
}

export interface YieldRiskResponse {
  supported: boolean
  crop: string
  mapped_crop: string | null
  state: string | null
  season: string | null
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | null
  probabilities: { LOW: number; MEDIUM: number; HIGH: number } | null
  model_used: string | null
  model_accuracy: number | null
  reason: string | null
}

export interface DiseasePrediction {
  crop: string
  condition: string
  is_healthy: boolean
  probability: number
}

export interface CareGuidance {
  pathogen_type: string | null
  pathogen: string | null
  severity: string
  recommended_actions: string[]
  prevention: string[]
}

export interface DiseaseDiagnosisResponse {
  top_prediction: DiseasePrediction
  alternatives: DiseasePrediction[]
  care_guidance: CareGuidance
  model_used: string
  model_accuracy: number
  supported_crops: string[]
  saved_to_history: boolean
}

export interface DiseaseOptionsResponse {
  supported_crops: string[]
  classes: string[]
  active_model: string | null
  active_model_accuracy: number | null
  dataset_records: number
}

export interface DiseaseHistoryItem {
  id: number
  farm_id: number
  farm_name: string
  crop: string
  condition: string
  is_healthy: boolean
  probability: number
  model_used: string
  created_at: string
}

export interface CurrentPriceResponse {
  found: boolean
  crop: string | null
  state: string | null
  district: string | null
  market: string | null
  variety: string | null
  as_of_date: string | null
  min_price: number | null
  max_price: number | null
  modal_price: number | null
  markets_reporting: number | null
  source: string | null
  is_live: boolean | null
  reason: string | null
}

export interface TrendPoint {
  date: string
  min_price: number
  max_price: number
  modal_price: number
}

export interface TrendResponse {
  found: boolean
  points: TrendPoint[]
  trend_direction: 'UP' | 'DOWN' | 'FLAT' | null
  change_pct: number | null
  source: string | null
  is_live: boolean | null
  reason: string | null
}

export interface MarketComparisonItem {
  market: string
  district: string
  min_price: number
  max_price: number
  modal_price: number
  arrivals_tonnes: number | null
}

export interface MarketComparisonResponse {
  found: boolean
  as_of_date: string | null
  markets: MarketComparisonItem[]
  best_market: MarketComparisonItem | null
  source: string | null
  is_live: boolean | null
  reason: string | null
}

export interface NutrientStatus {
  nutrient: string
  current_value: number
  optimal_range: string
  status: 'DEFICIENT' | 'ADEQUATE' | 'EXCESS'
  recommended_category: string | null
}

export interface FertilizerRecommendationResponse {
  crop: string
  growth_stage: string
  farm_area_acres: number | null
  deficiencies: NutrientStatus[]
  organic_matter_guidance: string | null
  application_timing: string
  warnings: string[]
  disclaimer: string
}

export interface FertilizerOptionsResponse {
  growth_stages: string[]
}

export type NotificationCategory = 'WEATHER' | 'CROP' | 'DISEASE' | 'MARKET' | 'FERTILIZER' | 'WATER' | 'RISK'

export interface NotificationItem {
  id: number
  farm_id: number | null
  category: NotificationCategory
  priority: 'LOW' | 'MEDIUM' | 'HIGH'
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export interface DashboardSummary {
  farm: { id: number; name: string; location: string }
  soil_health: SoilHealthResult | null
  weather: WeatherData
  farm_health: number | null
  risk: RiskBreakdown
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

export interface AssistantMessage {
  role: 'farmer' | 'ai'
  content: string
  created_at: string
}

export interface AssistantHistoryResponse {
  session_id: number | null
  messages: AssistantMessage[]
}

export interface AssistantAskResponse {
  session_id: number
  reply: AssistantMessage
  used_data: string[]
  suggested_questions: string[]
}

export interface SatellitePlannedMetric {
  key: string
  label: string
  description: string
}

export interface SatelliteStatusResponse {
  status: 'PLANNED' | string
  configured: boolean
  location: string
  planned_metrics: SatellitePlannedMetric[]
  message: string
}

export interface SensorReading {
  id: number
  farm_id: number
  sensor_type: 'soil_moisture' | 'temperature' | 'humidity' | 'ec'
  value: number
  unit: string
  source: 'demo_simulation' | 'device'
  recorded_at: string
}

export interface IoTReadingsResponse {
  farm_id: number
  readings: SensorReading[]
  has_real_device_data: boolean
}
