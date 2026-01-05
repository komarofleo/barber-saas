import apiClient from './client'

export interface Client {
  id: number
  user_id: number
  full_name: string
  phone: string | null
  car_brand: string | null
  car_model: string | null
  car_year: number | null
  car_number: string | null
  total_visits: number
  total_amount: number | null
  created_at: string
  user_telegram_id: number | null
  user_first_name: string | null
  user_last_name: string | null
  user_is_admin: boolean | null
}

export interface ClientListResponse {
  items: Client[]
  total: number
  page: number
  page_size: number
}

export interface ClientCreateRequest {
  full_name: string
  phone: string
  car_brand?: string
  car_model?: string
  car_year?: number
  car_number?: string
}

export const clientsApi = {
  getClients: async (page: number = 1, pageSize: number = 50, search?: string): Promise<ClientListResponse> => {
    let url = `/api/clients?page=${page}&page_size=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  createClient: async (data: ClientCreateRequest): Promise<Client> => {
    const response = await apiClient.post('/api/clients', data)
    return response.data
  },

  updateClient: async (clientId: number, data: Partial<ClientCreateRequest>): Promise<Client> => {
    const response = await apiClient.patch(`/api/clients/${clientId}`, data)
    return response.data
  },
}



