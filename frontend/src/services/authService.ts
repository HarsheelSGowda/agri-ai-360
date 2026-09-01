import { api } from './api'
import type { AuthResponse } from '@/types'

export interface RegisterPayload {
  name: string
  email: string
  password: string
  location?: string
  preferred_language?: string
}

export interface LoginPayload {
  email: string
  password: string
}

export async function registerUser(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/register', payload)
  return data
}

export async function loginUser(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/login', payload)
  return data
}
