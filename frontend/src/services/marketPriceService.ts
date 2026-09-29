import { api } from './api'
import type { CurrentPriceResponse, MarketComparisonResponse, TrendResponse } from '@/types'

export async function getMarketCrops(): Promise<string[]> {
  const { data } = await api.get<{ crops: string[] }>('/market-prices/crops')
  return data.crops
}

export async function getMarketStates(crop: string): Promise<string[]> {
  const { data } = await api.get<{ states: string[] }>('/market-prices/states', { params: { crop } })
  return data.states
}

export async function getMarketDistricts(crop: string, state: string): Promise<string[]> {
  const { data } = await api.get<{ districts: string[] }>('/market-prices/districts', { params: { crop, state } })
  return data.districts
}

export async function getMarketMarkets(crop: string, state: string, district?: string): Promise<string[]> {
  const { data } = await api.get<{ markets: string[] }>('/market-prices/markets', { params: { crop, state, district } })
  return data.markets
}

export interface MarketPriceQuery {
  crop: string
  state: string
  district?: string
  market?: string
  variety?: string
}

export async function getCurrentPrice(query: MarketPriceQuery): Promise<CurrentPriceResponse> {
  const { data } = await api.get<CurrentPriceResponse>('/market-prices', { params: query })
  return data
}

export async function getPriceTrend(query: MarketPriceQuery & { days?: number }): Promise<TrendResponse> {
  const { data } = await api.get<TrendResponse>('/market-prices/trend', { params: query })
  return data
}

export async function getMarketComparison(query: { crop: string; state: string; district?: string }): Promise<MarketComparisonResponse> {
  const { data } = await api.get<MarketComparisonResponse>('/market-prices/comparison', { params: query })
  return data
}
