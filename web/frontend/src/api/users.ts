import apiClient from './client'

export interface User {
  id: number
  telegram_id: number
  first_name: string | null
  last_name: string | null
  username: string | null
  phone: string | null
  is_admin: boolean
  is_master: boolean
  is_blocked: boolean
  created_at: string
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}

export interface UserCreateRequest {
  telegram_id: number
  first_name?: string
  last_name?: string
  username?: string
  phone?: string
  is_admin?: boolean
  is_master?: boolean
  is_blocked?: boolean
}

export const usersApi = {
  getUsers: async (page: number = 1, pageSize: number = 20, search?: string): Promise<UserListResponse> => {
    let url = `/api/users?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getUser: async (userId: number): Promise<User> => {
    const response = await apiClient.get(`/api/users/${userId}`)
    return response.data
  },

  toggleAdmin: async (userId: number, isAdmin: boolean): Promise<User> => {
    const response = await apiClient.patch(`/api/users/${userId}/admin?is_admin=${isAdmin}`)
    return response.data
  },

  createUser: async (data: UserCreateRequest): Promise<User> => {
    const response = await apiClient.post('/api/users', data)
    return response.data
  },

  updateUser: async (userId: number, data: Partial<UserCreateRequest>): Promise<User> => {
    const response = await apiClient.patch(`/api/users/${userId}`, data)
    return response.data
  },
}

