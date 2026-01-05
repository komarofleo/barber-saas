import apiClient from './client'

export interface Broadcast {
  id: number
  text: string
  image_path: string | null
  target_audience: string
  filter_params: any
  status: string
  total_sent: number
  total_errors: number
  created_by: number | null
  created_at: string
  sent_at: string | null
}

export interface BroadcastListResponse {
  items: Broadcast[]
  total: number
}

export interface BroadcastCreateRequest {
  text: string
  image_path?: string | null
  target_audience: string
  filter_params?: any
}

export const broadcastsApi = {
  getBroadcasts: async (page: number = 1, pageSize: number = 20, status?: string): Promise<BroadcastListResponse> => {
    let url = `/api/broadcasts?page=${page}&page_size=${pageSize}`
    if (status) {
      url += `&status=${encodeURIComponent(status)}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getBroadcast: async (broadcastId: number): Promise<Broadcast> => {
    const response = await apiClient.get(`/api/broadcasts/${broadcastId}`)
    return response.data
  },

  createBroadcast: async (data: BroadcastCreateRequest): Promise<Broadcast> => {
    const response = await apiClient.post('/api/broadcasts', data)
    return response.data
  },

  deleteBroadcast: async (broadcastId: number): Promise<void> => {
    await apiClient.delete(`/api/broadcasts/${broadcastId}`)
  },

  uploadImage: async (file: File): Promise<{ image_path: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/api/broadcasts/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}




