import service from './request'
import type { LoginRequest, LoginResponse, TokenResponse, UserInfo } from '@/types/auth'

export function login(data: LoginRequest): Promise<LoginResponse> {
  return service.post('/auth/login', data)
}

export function refresh(refresh_token: string): Promise<TokenResponse> {
  return service.post('/auth/refresh', { refresh_token })
}

export function getMe(): Promise<UserInfo> {
  return service.get('/auth/me')
}

export function updateProfile(data: Record<string, string>): Promise<UserInfo> {
  return service.put('/auth/profile', data)
}