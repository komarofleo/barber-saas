import apiClient from './client'
import { Plan } from './public'

export type BillingPeriod = 'monthly' | 'yearly'

export interface BillingPayment {
  id: number
  plan_id: number
  amount: number
  currency: string
  status: string
  description: string | null
  yookassa_payment_status: string | null
  yookassa_confirmation_url: string | null
  created_at: string
}

export interface CreatePaymentRequest {
  plan_id: number
  billing_period: BillingPeriod
}

export interface CreatePaymentResponse {
  payment_id: number
  confirmation_url: string
}

export const billingApi = {
  getPlans: async (): Promise<Plan[]> => {
    const response = await apiClient.get('/api/public/plans')
    return response.data
  },

  getPayments: async (): Promise<BillingPayment[]> => {
    const response = await apiClient.get('/api/subscription/payments')
    return response.data
  },

  createPayment: async (data: CreatePaymentRequest): Promise<CreatePaymentResponse> => {
    const response = await apiClient.post('/api/subscription/payments', data)
    return response.data
  },
}
