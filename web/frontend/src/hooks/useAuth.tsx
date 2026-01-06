import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi, User, SubscriptionInfo } from '../api/auth'

interface AuthContextType {
  user: User | null
  company_id: number | null
  isAuthenticated: boolean
  loading: boolean
  subscription: SubscriptionInfo | null
  subscriptionLoading: boolean
  canCreateBookings: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshSubscription: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [subscriptionLoading, setSubscriptionLoading] = useState(true)

  const refreshSubscription = async () => {
    try {
      setSubscriptionLoading(true)
      const subInfo = await authApi.getSubscriptionInfo()
      setSubscription(subInfo)
    } catch (error) {
      console.error('Failed to fetch subscription info:', error)
      setSubscription(null)
    } finally {
      setSubscriptionLoading(false)
    }
  }

  useEffect(() => {
    const token = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    
    if (token && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser)
        setUser(parsedUser)
        
        // Получаем информацию о подписке
        refreshSubscription()
        
        // Проверяем токен
        authApi.getMe().catch(() => {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          setUser(null)
        })
      } catch (e) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    } else {
      setLoading(false)
      setSubscriptionLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    try {
      console.log('Attempting login with username:', username)
      const response = await authApi.login({ username, password })
      console.log('Login response received:', response)
      
      if (!response.access_token) {
        throw new Error('No access token received')
      }
      
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('user', JSON.stringify(response.user))
      
      // Синхронно обновляем state
      setUser(response.user)
      
      // Получаем информацию о подписке
      await refreshSubscription()
      
      console.log('Login successful, user set:', response.user)
      
      // Даем время React обновить state
      await new Promise(resolve => setTimeout(resolve, 50))
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    await authApi.logout()
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setSubscription(null)
  }

  const canCreateBookings = subscription?.can_create_bookings ?? false
  const company_id = user?.company_id ?? null

  return (
    <AuthContext.Provider
      value={{
        user,
        company_id,
        isAuthenticated: !!user,
        loading,
        subscription,
        subscriptionLoading,
        canCreateBookings,
        login,
        logout,
        refreshSubscription,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
