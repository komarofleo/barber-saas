import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Добавляем токен к каждому запросу
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface OverviewStats {
  period: {
    start: string
    end: string
  }
  bookings_count: number
  bookings_confirmed: number
  bookings_completed: number
  bookings_cancelled: number
  bookings_no_show: number
  revenue: number
  avg_check: number
  no_show_percent: number
  conversion: number
  new_clients: number
  returning_clients: number
}

export interface MasterStats {
  master_id: number
  master_name: string
  bookings_count: number
  revenue: number
  load_percentage: number
  avg_check: number
}

export interface MastersStatsResponse {
  period: {
    start: string
    end: string
  }
  masters: MasterStats[]
}

export interface HourlyStats {
  hour: number
  bookings_count: number
  load_percentage: number
}

export interface TimeStatsResponse {
  period: {
    start: string
    end: string
  }
  hourly_stats: HourlyStats[]
}

export interface DailyStats {
  date: string
  bookings: number
  revenue: number
  no_shows: number
  load_percentage: number
}

export interface DailyStatsResponse {
  period: {
    start: string
    end: string
  }
  daily_stats: DailyStats[]
}

export const statisticsApi = {
  async getOverview(startDate?: string, endDate?: string): Promise<OverviewStats> {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    
    const response = await api.get<OverviewStats>('/api/statistics/overview', { params })
    return response.data
  },

  async getByMasters(startDate?: string, endDate?: string): Promise<MastersStatsResponse> {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    
    const response = await api.get<MastersStatsResponse>('/api/statistics/by-masters', { params })
    return response.data
  },

  async getByTime(startDate?: string, endDate?: string): Promise<TimeStatsResponse> {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    
    const response = await api.get<TimeStatsResponse>('/api/statistics/by-time', { params })
    return response.data
  },

  async getDaily(startDate?: string, endDate?: string): Promise<DailyStatsResponse> {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    
    const response = await api.get<DailyStatsResponse>('/api/statistics/daily', { params })
    return response.data
  },
}




