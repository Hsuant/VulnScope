export interface TagItem {
  id: number
  namespace: string
  name: string
  color: string | null
  description: string | null
  poc_count: number
}

export interface TagCreatePayload {
  namespace: string
  name: string
  color?: string
  description?: string
}

export interface TagUpdatePayload {
  namespace?: string
  name?: string
  color?: string
  description?: string
}