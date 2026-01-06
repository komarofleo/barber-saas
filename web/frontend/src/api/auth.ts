import apiClient from './client'
import axios from 'axios'

export interface LoginRequest {
  username: string
  password: string
}

export interface User {
  id: number
  company_id: number | null
  telegram_id: number | null
  username: string | null
  first_name: string | null
  last_name: string | null
  is_admin: boolean
  is_master: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface SubscriptionInfo {
  id: number
  company_id: number
  plan_name: string
  status: 'active' | 'expired' | 'blocked' | 'cancelled'
  start_date: string
  end_date: string
  can_create_bookings: boolean
}

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const params = new URLSearchParams()
    params.append('username', data.username)
    params.append('password', data.password)
    
    console.log('Sending login request to /api/auth/login')
    try {
      const response = await axios.post('/api/auth/login', params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })
      console.log('Login response status:', response.status)
      console.log('Login response data:', response.data)
      return response.data
    } catch (error: any) {
      console.error('Auth API error:', error)
      console.error('Error response:', error.response)
      throw error
    }
  },
  
  getMe: async (): Promise<User> => {
    const token = localStorage.getItem('token')
    if (!token) {
      throw new Error('No token')
    }
    const response = await axios.get('/api/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
    return response.data
  },

  getSubscriptionInfo: async (): Promise<SubscriptionInfo> => {
    const token = localStorage.getItem('token')
    if (!token) {
      throw new Error('No token')
    }
    const response = await axios.get('/api/auth/subscription', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })
    return response.data
  },
  
  logout: async (): Promise<void> => {
    const token = localStorage.getItem('token')
    if (token) {
      await axios.post('/api/auth/logout', null, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
    }
  },
}
