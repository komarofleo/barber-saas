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
}









