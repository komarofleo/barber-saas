/**
 * API для публичных endpoints (регистрация компаний)
 * 
 * Этот модуль содержит функции для работы с публичными API:
 * - Регистрация новых компаний
 * - Получение тарифных планов
 * - Получение информации о планах
 */

import apiClient from './client'

// ==================== Типы данных ====================

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
 * Данные для регистрации компании
 */
export interface CompanyRegistration {
  name: string
  email: string
  phone: string
  telegram_bot_token: string
  admin_telegram_id: number
  plan_id: number
}

/**
 * Данные платежа
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
  created_at: string
}

/**
 * Данные подписки
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
 * Данные компании
 */
export interface Company {
  id: number
  name: string
  email: string
  phone: string | null
  admin_telegram_id: number | null
  plan: Plan | null
  subscription_status: SubscriptionStatus | null
  can_create_bookings: boolean
  subscription_end_date: string | null
  is_active: boolean
  created_at: string
}

/**
 * Ответ на запрос регистрации
 */
export interface RegistrationResponse {
  success: boolean
  payment_id: number
  confirmation_url: string
  message: string
}

// ==================== API функции ====================

/**
 * Получить список активных тарифных планов
 * 
 * @returns Массив активных тарифных планов
 * 
 * @example
 * const plans = await publicApi.getPlans()
 * console.log(plans)
 * // [
 * //   {
 * //     id: 1,
 * //     name: "Starter",
 * //     description: "Базовый тариф",
 * //     price_monthly: 1000,
 * //     ...
 * //   }
 * // ]
 */
export async function getPlans(): Promise<Plan[]> {
  try {
    const response = await apiClient.get<Plan[]>('/api/public/plans')
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения тарифных планов:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось загрузить тарифные планы')
  }
}

/**
 * Получить тарифный план по ID
 * 
 * @param planId - ID тарифного плана
 * @returns Объект тарифного плана
 * 
 * @throws Error если план не найден или не активен
 * 
 * @example
 * const plan = await publicApi.getPlanById(1)
 * console.log(plan)
 * // {
 * //   id: 1,
 * //   name: "Starter",
 * //   price_monthly: 1000,
 * //   ...
 * // }
 */
export async function getPlanById(planId: number): Promise<Plan> {
  try {
    const response = await apiClient.get<Plan>(`/api/public/plans/${planId}`)
    return response.data
  } catch (error: any) {
    console.error('Ошибка получения тарифного плана:', error)
    throw new Error(error.response?.data?.detail || 'Не удалось получить тарифный план')
  }
}

/**
 * Зарегистрировать новую компанию
 * 
 * @param data - Данные для регистрации компании
 * @returns Данные для оплаты через Юкассу
 * 
 * @throws Error при ошибках валидации или создания платежа
 * 
 * @example
 * const result = await publicApi.registerCompany({
 *   name: "ООО 'Точка'",
 *   email: "admin@avtoservis.ru",
 *   phone: "+79001234567",
 *   telegram_bot_token: "8332803813:AAG...",
 *   admin_telegram_id: 329621295,
 *   plan_id: 3
 * })
 * // {
 * //   success: true,
 * //   payment_id: 123,
 * //   confirmation_url: "https://yoomoney.ru/checkout/...",
 * //   message: "Платеж создан. Ожидает оплаты."
 * }
 */
export async function registerCompany(
  data: CompanyRegistration
): Promise<RegistrationResponse> {
  try {
    const response = await apiClient.post<RegistrationResponse>(
      '/api/public/companies/register',
      data
    )
    return response.data
  } catch (error: any) {
    console.error('Ошибка регистрации компании:', error)
    
    // Обработка ошибок валидации
    if (error.response?.status === 422) {
      const validationErrors = error.response.data.detail
      const errorMessages = Array.isArray(validationErrors)
        ? validationErrors.map((e: any) => e.msg).join('. ')
        : validationErrors
      throw new Error(errorMessages || 'Ошибка валидации данных')
    }
    
    throw new Error(error.response?.data?.detail || 'Не удалось зарегистрировать компанию')
  }
}

/**
 * Проверить здоровье публичного API
 * 
 * @returns Статус "ok"
 * 
 * @example
 * const health = await publicApi.healthCheck()
 * console.log(health) // { status: "ok" }
 */
export async function healthCheck(): Promise<{ status: string }> {
  try {
    const response = await apiClient.get<{ status: string }>('/api/public/health')
    return response.data
  } catch (error: any) {
    console.error('Ошибка проверки здоровья API:', error)
    throw new Error('API недоступен')
  }
}

// ==================== Объект API ====================

/**
 * Объект публичного API для удобного использования
 */
export const publicApi = {
  getPlans,
  getPlanById,
  registerCompany,
  healthCheck,
}

export default publicApi

