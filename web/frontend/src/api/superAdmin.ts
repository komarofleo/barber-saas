/**
 * API для супер-администратора
 * 
 * Этот модуль содержит функции для работы с админ-панелью супер-админа:
 * - Авторизация супер-админа
 * - Управление компаниями
 * - Управление подписками
 * - Управление платежами
 * - Получение статистики
 */

import axios from 'axios'

// Отдельный клиент для супер-админа
const superAdminClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor для добавления токена супер-админа
superAdminClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('super_admin_token') || sessionStorage.getItem('super_admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  config.baseURL = undefined
  return config
})

// Interceptor для обработки ошибок
superAdminClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('super_admin_token')
      sessionStorage.removeItem('super_admin_token')
      localStorage.removeItem('super_admin')
      sessionStorage.removeItem('super_admin')
      window.location.href = '/super-admin/login'
    }
    return Promise.reject(error)
  }
)

// Используем обычный apiClient для логина (без токена)
import apiClient from './client'

// ==================== Типы данных ====================

/**
 * Данные для входа супер-админа
 */
export interface SuperAdminLoginRequest {
  username: string
  password: string
}

/**
 * Ответ на запрос входа
 */
export interface SuperAdminLoginResponse {
  access_token: string
  token_type: string
  super_admin: SuperAdmin
}

/**
 * Супер-администратор
 */
export interface SuperAdmin {
  id: number
  username: string
  email: string
  telegram_id: number | null
  is_active: boolean
  created_at: string
}

/**
 * Статусы подписки
 */
export enum SubscriptionStatus {
  ACTIVE = 'active',
  EXPIRED = 'expired',
  BLOCKED = 'blocked',
  PENDING = 'pending',
}

/**
 * Статусы платежей
 */
export enum PaymentStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded',
}

/**
 * Тарифный план
 */
export interface Plan {
  id: number
  name: string
  description: string | null
  price_monthly: number
  price_yearly: number
  max_bookings_per_month: number
  max_users: number
  max_masters: number
  is_active: boolean
  display_order: number
}

/**
 * Подписка компании
 */
export interface Subscription {
  id: number
  company_id: number
  plan: Plan
  start_date: string
  end_date: string
  status: SubscriptionStatus
}

/**
 * Платеж
 */
export interface Payment {
  id: number
  company_id: number | null
  plan_id: number
  amount: number
  currency: string
  status: PaymentStatus
  description: string
  yookassa_payment_id: string
  yookassa_confirmation_url: string | null
  yookassa_payment_status: string | null
  webhook_received_at: string | null
  webhook_signature_verified: boolean
  created_at: string
}

/**
 * Компания
 */
export interface Company {
  id: number
  name: string
  email: string
  phone: string | null
  telegram_bot_token: string
  admin_telegram_id: number | null
  plan_id: number | null
  subscription_status: SubscriptionStatus | null
  can_create_bookings: boolean
  subscription_end_date: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  plan: Plan | null
  subscriptions: Subscription[]
  payments: Payment[]
}

/**
 * Статистика дашборда
 */
export interface DashboardStats {
  total_companies: number
  active_companies: number
  total_subscriptions: number
  active_subscriptions: number
  total_revenue: number
  monthly_revenue: number
  companies_with_expiring_subscription: number
  new_companies_this_month: number
}

/**
 * Фильтры для компаний
 */
export interface CompanyFilters {
  search?: string
  subscription_status?: SubscriptionStatus
  is_active?: boolean
  plan_id?: number
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

/**
 * Ответ со списком компаний
 */
export interface CompaniesResponse {
  companies: Company[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * Данные для обновления компании
 */
export interface CompanyUpdateData {
  name?: string
  email?: string
  phone?: string
  plan_id?: number
  subscription_status?: SubscriptionStatus
  can_create_bookings?: boolean
  subscription_end_date?: string
  is_active?: boolean
}

/**
 * Данные для создания ручного платежа
 */
export interface ManualPaymentRequest {
  company_id: number
  plan_id: number
  amount: number
  description: string
}

// ==================== API функции ====================

/**
 * Войти в систему как супер-администратор
 * 
 * @param data - Данные для входа
 * @returns Данные супер-админа и токен доступа
 * 
 * @throws Error при неверном логине или пароле
 * 
 * @example
 * const result = await superAdminApi.login({
 *   username: 'admin',
 *   password: 'admin123'
 * })
 * // {
 * //   access_token: 'eyJ0eXAiOiJK...',
 * //   super_admin: { id: 1, username: 'admin', ... }
 * // }
 */
export async function login(data: SuperAdminLoginRequest): Promise<SuperAdminLoginResponse> {
  try {
    const response = await apiClient.post<SuperAdminLoginResponse>(
      '/api/super-admin/auth/login',
      {
        username: data.username,
        password: data.password,
      }
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка входа супер-админа:', error)
    
    // Извлекаем сообщение об ошибке
    let errorMessage = 'Неверный логин или пароль'
    
    if (error.response?.data) {
      const data = error.response.data
      if (typeof data.detail === 'string') {
        errorMessage = data.detail
      } else if (typeof data.detail === 'object' && data.detail !== null) {
        // Если detail - объект, пытаемся извлечь сообщение
        if (data.detail.message) {
          errorMessage = String(data.detail.message)
        } else if (data.detail.msg) {
          errorMessage = String(data.detail.msg)
        } else {
          errorMessage = JSON.stringify(data.detail)
        }
      } else if (typeof data.message === 'string') {
        errorMessage = data.message
      } else if (typeof data.error === 'string') {
        errorMessage = data.error
      }
    } else if (error.message && typeof error.message === 'string') {
      errorMessage = error.message
    }
    
    throw new Error(errorMessage)
  }
}

/**
 * Получить статистику дашборда
 * 
 * @returns Статистика системы
 * 
 * @example
 * const stats = await superAdminApi.getDashboardStats()
 * // {
 * //   total_companies: 150,
 * //   active_companies: 145,
 * //   total_revenue: 1500000,
 * //   ...
 * // }
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    const response = await superAdminClient.get<DashboardStats>('/api/super-admin/dashboard/stats')
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения статистики дашборда:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось получить статистику')
  }
}

/**
 * Получить список компаний
 * 
 * @param filters - Фильтры для поиска и сортировки
 * @returns Список компаний с пагинацией
 * 
 * @example
 * const result = await superAdminApi.getCompanies({
 *   page: 1,
 *   page_size: 20,
 *   subscription_status: 'active'
 * })
 * // {
 * //   companies: [...],
 * //   total: 150,
 * //   page: 1,
 * //   page_size: 20,
 * //   total_pages: 8
 * // }
 */
export async function getCompanies(
  filters: CompanyFilters = {}
): Promise<CompaniesResponse> {
  try {
    const params = new URLSearchParams()
    
    if (filters.search) params.append('search', filters.search)
    if (filters.subscription_status) params.append('subscription_status', filters.subscription_status)
    if (filters.is_active !== undefined) params.append('is_active', String(filters.is_active))
    if (filters.plan_id) params.append('plan_id', String(filters.plan_id))
    if (filters.page) params.append('page', String(filters.page))
    if (filters.page_size) params.append('page_size', String(filters.page_size))
    if (filters.sort_by) params.append('sort_by', filters.sort_by)
    if (filters.sort_order) params.append('sort_order', filters.sort_order)

    const queryString = params.toString()
    const response = await superAdminClient.get<CompaniesResponse>(
      `/api/super-admin/companies${queryString ? `?${queryString}` : ''}`
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения компаний:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось получить список компаний')
  }
}

/**
 * Получить детальную информацию о компании
 * 
 * @param companyId - ID компании
 * @returns Полная информация о компании с подписками и платежами
 * 
 * @throws Error если компания не найдена
 * 
 * @example
 * const company = await superAdminApi.getCompanyById(1)
 * // {
 * //   id: 1,
 * //   name: "ООО 'Точка'",
 * //   email: "admin@avtoservis.ru",
 * //   plan: { id: 3, name: "Business", ... },
 * //   subscriptions: [...],
 * //   payments: [...]
 * // }
 */
export async function getCompanyById(companyId: number): Promise<Company> {
  try {
    const response = await superAdminClient.get<Company>(`/api/super-admin/companies/${companyId}`)
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения компании:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось получить компанию')
  }
}

/**
 * Обновить информацию о компании
 * 
 * @param companyId - ID компании
 * @param data - Данные для обновления
 * @returns Обновленная компания
 * 
 * @throws Error если компания не найдена или данные неверны
 * 
 * @example
 * const company = await superAdminApi.updateCompany(1, {
 *   subscription_status: 'active',
 *   can_create_bookings: true
 * })
 */
export async function updateCompany(
  companyId: number,
  data: CompanyUpdateData
): Promise<Company> {
  try {
    const response = await superAdminClient.put<Company>(
      `/api/super-admin/companies/${companyId}`,
      data
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка обновления компании:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось обновить компанию')
  }
}

/**
 * Деактивировать компанию
 * 
 * @param companyId - ID компании
 * @returns Деактивированная компания
 * 
 * @throws Error если компания не найдена или уже деактивирована
 * 
 * @example
 * const company = await superAdminApi.deactivateCompany(1)
 * // { id: 1, is_active: false, ... }
 */
export async function deactivateCompany(companyId: number): Promise<Company> {
  try {
    const response = await superAdminClient.patch<Company>(
      `/api/super-admin/companies/${companyId}/deactivate`
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка деактивации компании:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось деактивировать компанию')
  }
}

/**
 * Получить подписки компании
 * 
 * @param companyId - ID компании
 * @returns Список подписок компании
 * 
 * @example
 * const subscriptions = await superAdminApi.getCompanySubscriptions(1)
 * // [
 * //   { id: 1, company_id: 1, plan: {...}, status: 'active', ... },
 * //   { id: 2, company_id: 1, plan: {...}, status: 'expired', ... }
 * // ]
 */
export async function getCompanySubscriptions(companyId: number): Promise<Subscription[]> {
  try {
    const response = await superAdminClient.get<Subscription[]>(
      `/api/super-admin/companies/${companyId}/subscriptions`
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения подписок:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось получить подписки')
  }
}

/**
 * Получить платежи компании
 * 
 * @param companyId - ID компании
 * @returns Список платежей компании
 * 
 * @example
 * const payments = await superAdminApi.getCompanyPayments(1)
 * // [
 * //   { id: 1, company_id: 1, amount: 5000, status: 'completed', ... },
 * //   { id: 2, company_id: 1, amount: 5000, status: 'pending', ... }
 * // ]
 */
export async function getCompanyPayments(companyId: number): Promise<Payment[]> {
  try {
    const response = await superAdminClient.get<Payment[]>(
      `/api/super-admin/companies/${companyId}/payments`
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения платежей:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось получить платежи')
  }
}

/**
 * Создать ручной платеж
 * 
 * @param data - Данные для создания платежа
 * @returns Созданный платеж
 * 
 * @throws Error если данные неверны
 * 
 * @example
 * const payment = await superAdminApi.createManualPayment({
 *   company_id: 1,
 *   plan_id: 3,
 *   amount: 5000,
 *   description: 'Ручное продление подписки'
 * })
 * // { id: 100, company_id: 1, amount: 5000, status: 'completed', ... }
 */
export async function createManualPayment(
  data: ManualPaymentRequest
): Promise<Payment> {
  try {
    const response = await superAdminClient.post<Payment>(
      '/api/super-admin/companies/manual-payment',
      data
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка создания ручного платежа:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось создать платеж')
  }
}

/**
 * Выйти из системы
 * 
 * @returns void
 * 
 * @example
 * await superAdminApi.logout()
 * // Токен удален из localStorage
 */
export async function logout(): Promise<void> {
  try {
      await superAdminClient.post('/api/super-admin/auth/logout')
      localStorage.removeItem('super_admin_token')
      sessionStorage.removeItem('super_admin_token')
      localStorage.removeItem('super_admin')
      sessionStorage.removeItem('super_admin')
  } catch (error: any) {
    console.error('Ошибка выхода:', error)
    // Удаляем токен локально даже при ошибке API
    localStorage.removeItem('super_admin_token')
    localStorage.removeItem('super_admin')
  }
}

// ==================== Объект API ====================

/**
 * Объект API супер-админа для удобного использования
 */
export const superAdminApi = {
  login,
  getDashboardStats,
  getCompanies,
  getCompanyById,
  updateCompany,
  deactivateCompany,
  getCompanySubscriptions,
  getCompanyPayments,
  createManualPayment,
  logout,
}

export default superAdminApi

