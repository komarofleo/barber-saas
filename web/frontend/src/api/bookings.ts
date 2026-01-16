import apiClient from './client'

export interface Booking {
  id: number
  booking_number: string
  client_id: number
  service_id: number | null
  master_id: number | null
  post_id: number | null
  service_date: string
  request_date: string | null
  time: string
  duration: number
  end_time: string
  status: string
  amount: number | null
  is_paid: boolean
  payment_method: string | null
  comment: string | null
  admin_comment: string | null
  created_at: string
  confirmed_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  client_name: string | null
  client_phone: string | null
  client_telegram_id: number | null
  client_car_brand: string | null
  client_car_model: string | null
  service_name: string | null
  master_name: string | null
  post_number: number | null
  notification_sent?: boolean | null
}

export interface BookingListResponse {
  items: Booking[]
  total: number
  page: number
  page_size: number
}

export interface BookingCreateRequest {
  client_id: number
  service_id?: number
  master_id?: number
  post_id?: number
  service_date: string
  time: string
  duration?: number
  status?: string
  amount?: number
  comment?: string
}

export interface BookingUpdateRequest {
  client_id?: number
  service_id?: number
  master_id?: number
  post_id?: number
  service_date?: string
  request_date?: string
  time?: string
  duration?: number
  status?: string
  amount?: number
  is_paid?: boolean
  payment_method?: string
  comment?: string
  admin_comment?: string
}

export const bookingsApi = {
  getBookings: async (
    page: number = 1,
    pageSize: number = 20,
    filters?: {
      status?: string
      start_date?: string
      end_date?: string
      master_id?: number
      service_id?: number
      post_id?: number
      search?: string
    }
  ): Promise<BookingListResponse> => {
    let url = `/api/bookings?page=${page}&page_size=${pageSize}`
    if (filters) {
      if (filters.status) url += `&status=${filters.status}`
      if (filters.start_date) url += `&start_date=${filters.start_date}`
      if (filters.end_date) url += `&end_date=${filters.end_date}`
      if (filters.master_id) url += `&master_id=${filters.master_id}`
      if (filters.service_id) url += `&service_id=${filters.service_id}`
      if (filters.post_id) url += `&post_id=${filters.post_id}`
      if (filters.search) url += `&search=${encodeURIComponent(filters.search)}`
    }
    const response = await apiClient.get(url)
    return response.data
  },

  getBooking: async (bookingId: number): Promise<Booking> => {
    const response = await apiClient.get(`/api/bookings/${bookingId}`)
    return response.data
  },

  createBooking: async (data: BookingCreateRequest): Promise<Booking> => {
    const response = await apiClient.post('/api/bookings', data)
    return response.data
  },

  updateBooking: async (bookingId: number, data: BookingUpdateRequest): Promise<Booking> => {
    const response = await apiClient.patch(`/api/bookings/${bookingId}`, data)
    return response.data
  },

  getAvailableSlots: async (
    date: string,
    serviceId?: number,
    masterId?: number,
    postId?: number
  ): Promise<string[]> => {
    let url = `/api/bookings/available-slots?date=${date}`
    if (serviceId) url += `&service_id=${serviceId}`
    if (masterId) url += `&master_id=${masterId}`
    if (postId) url += `&post_id=${postId}`
    // Добавляем timestamp для предотвращения кэширования
    url += `&_t=${Date.now()}`
    const response = await apiClient.get(url)
    return response.data
  },
}

