import apiClient from './client'

export interface Post {
  id: number
  number: number
  name: string | null
  description: string | null
  is_active: boolean
  created_at: string
}

export interface PostListResponse {
  items: Post[]
  total: number
  page: number
  page_size: number
}

export interface PostCreateRequest {
  number: number
  name?: string
  description?: string
  is_active?: boolean
}

export interface PostUpdateRequest {
  number?: number
  name?: string
  description?: string
  is_active?: boolean
}

export const postsApi = {
  getPosts: async (page: number = 1, pageSize: number = 20, search?: string, isActive?: boolean): Promise<PostListResponse> => {
    let url = `/api/posts?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    if (isActive !== undefined) {
      url += `&is_active=${isActive}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getPost: async (postId: number): Promise<Post> => {
    const response = await apiClient.get(`/api/posts/${postId}`)
    return response.data
  },

  createPost: async (data: PostCreateRequest): Promise<Post> => {
    const response = await apiClient.post('/api/posts', data)
    return response.data
  },

  updatePost: async (postId: number, data: PostUpdateRequest): Promise<Post> => {
    const response = await apiClient.patch(`/api/posts/${postId}`, data)
    return response.data
  },

  deletePost: async (postId: number): Promise<void> => {
    await apiClient.delete(`/api/posts/${postId}`)
  },
}









