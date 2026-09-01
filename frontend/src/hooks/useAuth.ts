import { create } from 'zustand'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User, token: string) => void
  logout: () => void
}

function loadUser(): User | null {
  const raw = localStorage.getItem('agri_user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export const useAuth = create<AuthState>((set) => ({
  user: loadUser(),
  token: localStorage.getItem('agri_token'),
  isAuthenticated: Boolean(localStorage.getItem('agri_token')),
  setAuth: (user, token) => {
    localStorage.setItem('agri_token', token)
    localStorage.setItem('agri_user', JSON.stringify(user))
    set({ user, token, isAuthenticated: true })
  },
  logout: () => {
    localStorage.removeItem('agri_token')
    localStorage.removeItem('agri_user')
    set({ user: null, token: null, isAuthenticated: false })
  },
}))
