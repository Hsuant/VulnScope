import service from './request'

export interface CommentItem {
  id: number
  poc_id: number
  user_id: number
  username: string
  content: string
  parent_id: number | null
  edited: boolean
  deleted: boolean
  created_at: string | null
  updated_at: string | null
  replies: CommentItem[]
}

export interface CommentCreatePayload {
  content: string
  parent_id?: number | null
}

export interface CommentUpdatePayload {
  content: string
}

/** 获取 POC 评论列表（树形结构） */
export function listComments(pocId: number): Promise<CommentItem[]> {
  return service.get(`/pocs/${pocId}/comments`)
}

/** 发表评论 */
export function createComment(pocId: number, data: CommentCreatePayload): Promise<CommentItem[]> {
  return service.post(`/pocs/${pocId}/comments`, data)
}

/** 编辑评论 */
export function updateComment(commentId: number, data: CommentUpdatePayload): Promise<CommentItem[]> {
  return service.put(`/pocs/comments/${commentId}`, data)
}

/** 删除评论 */
export function deleteComment(commentId: number): Promise<{ deleted: boolean; comment_id: number }> {
  return service.delete(`/pocs/comments/${commentId}`)
}