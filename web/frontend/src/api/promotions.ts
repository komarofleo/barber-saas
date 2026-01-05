import apiClient from './client'

export interface Promotion {
  id: number
  name: string
  description: string | null
  discount_type: string
  discount_value: number
  service_id: number | null
  start_date: string | null
  end_date: string | null
  is_active: boolean
  created_at: string
  service_name: string | null
}

export interface PromotionListResponse {
  items: Promotion[]
  total: number
}

export interface PromotionCreateRequest {
  name: string
  description?: string | null
  discount_type: string
  discount_value: number
  service_id?: number | null
  start_date?: string | null
  end_date?: string | null
}

export interface PromotionUpdateRequest {
  name?: string
  description?: string | null
  discount_type?: string
  discount_value?: number
  service_id?: number | null
  start_date?: string | null
  end_date?: string | null
  is_active?: boolean
}

export const promotionsApi = {
  getPromotions: async (page: number = 1, pageSize: number = 20, isActive?: boolean, serviceId?: number): Promise<PromotionListResponse> => {
    let url = `/api/promotions?page=${page}&page_size=${pageSize}`
    if (isActive !== undefined) {
      url += `&is_active=${isActive}`
    }
    if (serviceId !== undefined) {
      url += `&service_id=${serviceId}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getPromotion: async (promotionId: number): Promise<Promotion> => {
    const response = await apiClient.get(`/api/promotions/${promotionId}`)
    return response.data
  },

  createPromotion: async (data: PromotionCreateRequest): Promise<Promotion> => {
    const response = await apiClient.post('/api/promotions', data)
    return response.data
  },

  updatePromotion: async (promotionId: number, data: PromotionUpdateRequest): Promise<Promotion> => {
    const response = await apiClient.patch(`/api/promotions/${promotionId}`, data)
    return response.data
  },

  deletePromotion: async (promotionId: number): Promise<void> => {
    await apiClient.delete(`/api/promotions/${promotionId}`)
  },
}









