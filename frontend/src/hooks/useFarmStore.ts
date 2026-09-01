import { create } from 'zustand'
import type { Farm, TopCropsResponse, WeatherData } from '@/types'

interface FarmState {
  activeFarm: Farm | null
  farms: Farm[]
  lastWeather: WeatherData | null
  lastPrediction: TopCropsResponse | null
  setFarms: (farms: Farm[]) => void
  setActiveFarm: (farm: Farm | null) => void
  setLastWeather: (weather: WeatherData) => void
  setLastPrediction: (prediction: TopCropsResponse) => void
}

export const useFarmStore = create<FarmState>((set) => ({
  activeFarm: null,
  farms: [],
  lastWeather: null,
  lastPrediction: null,
  setFarms: (farms) => set((state) => ({ farms, activeFarm: state.activeFarm ?? farms[0] ?? null })),
  setActiveFarm: (farm) => set({ activeFarm: farm }),
  setLastWeather: (weather) => set({ lastWeather: weather }),
  setLastPrediction: (prediction) => set({ lastPrediction: prediction }),
}))
