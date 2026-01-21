import apiClient from './client'

export interface Setting {
  id: number
  key: string
  value: string
  description: string | null
  updated_at: string
}

export interface SettingUpdateRequest {
  value: string
}

export interface CompanyCredentials {
  email: string
  name: string
  admin_telegram_id: number | null
  telegram_bot_token: string | null
}

export interface CompanyCredentialsUpdateRequest {
  name?: string | null
  admin_telegram_id?: number | null
  telegram_bot_token?: string | null
}

export interface CompanyCredentialsSendResponse {
  success: boolean
  message: string
}

export const settingsApi = {
  getSettings: async (): Promise<Setting[]> => {
    const response = await apiClient.get('/api/settings')
    return response.data
  },

  getSetting: async (key: string): Promise<Setting> => {
    const response = await apiClient.get(`/api/settings/${key}`)
    return response.data
  },

  updateSetting: async (key: string, data: SettingUpdateRequest): Promise<Setting> => {
    const response = await apiClient.patch(`/api/settings/${key}`, data)
    return response.data
  },
  uploadSettingFile: async (key: string, file: File): Promise<Setting> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post(`/api/settings/upload/${key}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getCompanyCredentials: async (): Promise<CompanyCredentials> => {
    const response = await apiClient.get('/api/settings/company')
    return response.data
  },

  updateCompanyCredentials: async (
    data: CompanyCredentialsUpdateRequest
  ): Promise<CompanyCredentials> => {
    const response = await apiClient.patch('/api/settings/company', data)
    return response.data
  },

  sendCompanyCredentials: async (): Promise<CompanyCredentialsSendResponse> => {
    const response = await apiClient.post('/api/settings/company/send-credentials')
    return response.data
  },
}









