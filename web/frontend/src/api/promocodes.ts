import apiClient from './client'

export interface Promocode {
  id: number
  code: string
  discount_type: string
  discount_value: number
  service_id: number | null
  min_amount: number
  max_uses: number | null
  current_uses: number
  start_date: string | null
  end_date: string | null
  is_active: boolean
  description: string | null
  created_at: string
  service_name: string | null
}

export interface PromocodeListResponse {
  items: Promocode[]
  total: number
}

export interface PromocodeCreateRequest {
  code: string
  discount_type: string
  discount_value: number
  service_id?: number | null
  min_amount?: number
  max_uses?: number | null
  start_date?: string | null
  end_date?: string | null
  description?: string | null
}

export interface PromocodeUpdateRequest {
  discount_type?: string
  discount_value?: number
  service_id?: number | null
  min_amount?: number
  max_uses?: number | null
  start_date?: string | null
  end_date?: string | null
  is_active?: boolean
  description?: string | null
}

export const promocodesApi = {
  getPromocodes: async (page: number = 1, pageSize: number = 20, isActive?: boolean): Promise<PromocodeListResponse> => {
    let url = `/api/promocodes?page=${page}&page_size=${pageSize}`
    if (isActive !== undefined) {
      url += `&is_active=${isActive}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getPromocode: async (promocodeId: number): Promise<Promocode> => {
    const response = await apiClient.get(`/api/promocodes/${promocodeId}`)
    return response.data
  },

  createPromocode: async (data: PromocodeCreateRequest): Promise<Promocode> => {
    const response = await apiClient.post('/api/promocodes', data)
    return response.data
  },

  updatePromocode: async (promocodeId: number, data: PromocodeUpdateRequest): Promise<Promocode> => {
    const response = await apiClient.patch(`/api/promocodes/${promocodeId}`, data)
    return response.data
  },

  deletePromocode: async (promocodeId: number): Promise<void> => {
    await apiClient.delete(`/api/promocodes/${promocodeId}`)
  },
}









