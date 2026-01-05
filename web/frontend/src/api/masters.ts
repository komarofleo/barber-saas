import apiClient from './client'
import { Booking } from './bookings'

export interface Master {
  id: number
  user_id: number | null
  full_name: string
  phone: string | null
  telegram_id: number | null
  specialization: string | null
  is_universal: boolean
  created_at: string
}

export interface MasterListResponse {
  items: Master[]
  total: number
  page: number
  page_size: number
}

export interface MasterCreateRequest {
  user_id?: number
  full_name: string
  phone?: string
  telegram_id?: number
  specialization?: string
  is_universal?: boolean
}

export interface MasterUpdateRequest {
  user_id?: number
  full_name?: string
  phone?: string
  telegram_id?: number
  specialization?: string
  is_universal?: boolean
}

export const mastersApi = {
  getMasters: async (page: number = 1, pageSize: number = 20, search?: string): Promise<MasterListResponse> => {
    let url = `/api/masters?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getMaster: async (masterId: number): Promise<Master> => {
    const response = await apiClient.get(`/api/masters/${masterId}`)
    return response.data
  },

  createMaster: async (data: MasterCreateRequest): Promise<Master> => {
    const response = await apiClient.post('/api/masters', data)
    return response.data
  },

  updateMaster: async (masterId: number, data: MasterUpdateRequest): Promise<Master> => {
    const response = await apiClient.patch(`/api/masters/${masterId}`, data)
    return response.data
  },

  deleteMaster: async (masterId: number): Promise<void> => {
    await apiClient.delete(`/api/masters/${masterId}`)
  },

  getMasterSchedule: async (masterId: number, date: string): Promise<{ master_id: number; master_name: string; date: string; bookings: Booking[] }> => {
    const response = await apiClient.get(`/api/masters/${masterId}/schedule?date=${date}`)
    return response.data
  },
}

