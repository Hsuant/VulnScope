import service from './request'
import type { UserItem, UserCreatePayload, UserUpdatePayload, RoleItem } from '@/types/user'

export function listUsers(params?: { page?: number; page_size?: number }): Promise<{ items: UserItem[]; total: number }> {
  return service.get('/users', { params })
}

export function getUser(id: number): Promise<UserItem> {
  return service.get(`/users/${id}`)
}

export function createUser(data: UserCreatePayload): Promise<UserItem> {
  return service.post('/users', data)
}

export function updateUser(id: number, data: UserUpdatePayload): Promise<UserItem> {
  return service.put(`/users/${id}`, data)
}

export function deleteUser(id: number): Promise<{ deleted: boolean }> {
  return service.delete(`/users/${id}`)
}

export function listRoles(): Promise<RoleItem[]> {
  return service.get('/users/roles')
}