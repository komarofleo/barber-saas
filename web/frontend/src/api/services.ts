import apiClient from './client'

export interface Service {
  id: number
  name: string
  description: string | null
  price: number
  duration: number
  is_active: boolean
  created_at: string
}

export interface ServiceListResponse {
  items: Service[]
  total: number
  page: number
  page_size: number
}

export interface ServiceCreateRequest {
  name: string
  description?: string
  price: number
  duration: number
  is_active?: boolean
}

export interface ServiceUpdateRequest {
  name?: string
  description?: string
  price?: number
  duration?: number
  is_active?: boolean
}

export const servicesApi = {
  getServices: async (page: number = 1, pageSize: number = 20, search?: string, isActive?: boolean): Promise<ServiceListResponse> => {
    let url = `/api/services?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    if (isActive !== undefined) {
      url += `&is_active=${isActive}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getService: async (serviceId: number): Promise<Service> => {
    const response = await apiClient.get(`/api/services/${serviceId}`)
    return response.data
  },

  createService: async (data: ServiceCreateRequest): Promise<Service> => {
    const response = await apiClient.post('/api/services', data)
    return response.data
  },

  updateService: async (serviceId: number, data: ServiceUpdateRequest): Promise<Service> => {
    const response = await apiClient.patch(`/api/services/${serviceId}`, data)
    return response.data
  },

  deleteService: async (serviceId: number): Promise<void> => {
    await apiClient.delete(`/api/services/${serviceId}`)
  },
}









