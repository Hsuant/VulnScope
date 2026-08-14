export interface UserItem {
  id: number
  username: string
  email: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  created_at: string | null
}

export interface UserCreatePayload {
  username: string
  email?: string
  password: string
  role: string
}

export interface UserUpdatePayload {
  email?: string
  password?: string
  role?: string
  is_active?: boolean
}

export interface RoleItem {
  id: number
  name: string
  description: string | null
  permissions: string
}