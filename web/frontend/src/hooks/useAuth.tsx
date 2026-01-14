import { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react'
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
  const hasChecked = useRef(false)

  const refreshSubscription = async () => {
    // Не загружаем данные, если мы на страницах супер-админа
    const currentPath = window.location.pathname
    if (currentPath.startsWith('/super-admin')) {
      setSubscriptionLoading(false)
      return
    }
    
    try {
      setSubscriptionLoading(true)
      const subInfo = await authApi.getSubscriptionInfo()
      setSubscription(subInfo)
    } catch (error: any) {
      console.error('Failed to fetch subscription info:', error)
      // Если подписка не найдена (404), это нормально - просто нет подписки
      if (error.response?.status === 404) {
        setSubscription(null)
      } else {
        // Для других ошибок, оставляем null
        setSubscription(null)
      }
    } finally {
      setSubscriptionLoading(false)
    }
  }

  useEffect(() => {
    // Проверяем только один раз при монтировании
    if (hasChecked.current) {
      return
    }
    hasChecked.current = true
    
    // Не загружаем данные, если мы на страницах супер-админа
    const currentPath = window.location.pathname
    if (currentPath.startsWith('/super-admin')) {
      setLoading(false)
      setSubscriptionLoading(false)
      setUser(null)
      return
    }
    
    const token = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    
    // Если нет токена, сразу устанавливаем loading=false
    if (!token) {
      setLoading(false)
      setSubscriptionLoading(false)
      setUser(null)
      return
    }
    
    if (token && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser)
        setUser(parsedUser)
        
        // Получаем информацию о подписке только если не на страницах супер-админа
        if (!currentPath.startsWith('/super-admin')) {
          // Для пользователей с company_id (company_admin или tenant_user) подписка уже есть в user объекте
          if (parsedUser.company_id) {
            // Создаем subscriptionInfo из данных пользователя
            const subscriptionInfo: SubscriptionInfo = {
              id: parsedUser.company_id,
              company_id: parsedUser.company_id,
              plan_name: 'Business',
              status: (parsedUser.subscription_status || 'active') as 'active' | 'expired' | 'blocked' | 'cancelled',
              start_date: parsedUser.subscription_end_date ? new Date().toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
              end_date: parsedUser.subscription_end_date || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Если нет даты, ставим через год
              can_create_bookings: parsedUser.can_create_bookings ?? true, // По умолчанию true для пользователей с company_id
              days_remaining: parsedUser.subscription_end_date ? 
                Math.max(0, Math.ceil((new Date(parsedUser.subscription_end_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))) : 
                365
            }
            setSubscription(subscriptionInfo)
            setSubscriptionLoading(false)
          } else {
            // Обычный пользователь без company_id - получаем подписку через API
            refreshSubscription()
          }
          
          // Проверяем токен только если не на страницах супер-админа
          // Для company_admin не вызываем getMe, так как это не работает
          if (!parsedUser.company_id) {
            authApi.getMe().catch(() => {
              localStorage.removeItem('token')
              localStorage.removeItem('user')
              setUser(null)
            })
          }
        }
        setLoading(false)
      } catch (e) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        setLoading(false)
        setSubscriptionLoading(false)
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
      
      // Для пользователей с company_id (company_admin или tenant_user) подписка уже есть в user объекте
      if (response.user.company_id) {
        // Создаем subscriptionInfo из данных пользователя
        const subscriptionInfo: SubscriptionInfo = {
          id: response.user.company_id,
          company_id: response.user.company_id,
          plan_name: 'Business', // Можно получить из user если есть
          status: (response.user.subscription_status || 'active') as 'active' | 'expired' | 'blocked' | 'cancelled',
          start_date: response.user.subscription_end_date ? new Date().toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
          end_date: response.user.subscription_end_date || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Если нет даты, ставим через год
          can_create_bookings: response.user.can_create_bookings ?? true, // По умолчанию true для пользователей с company_id
          days_remaining: response.user.subscription_end_date ? 
            Math.max(0, Math.ceil((new Date(response.user.subscription_end_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))) : 
            365
        }
        setSubscription(subscriptionInfo)
        setSubscriptionLoading(false)
      } else {
        // Обычный пользователь без company_id - получаем подписку через API
        await refreshSubscription()
      }
      
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

  // Определяем canCreateBookings:
  // 1. Если есть subscription, используем его can_create_bookings
  // 2. Если нет subscription, но есть user с can_create_bookings, используем его
  // 3. Если пользователь - tenant_user с company_id, проверяем подписку компании из user объекта
  const canCreateBookings = subscription?.can_create_bookings ?? 
                            user?.can_create_bookings ?? 
                            (user?.company_id ? true : false) // Если есть company_id, считаем что подписка активна
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
