import apiClient from './client'

export interface BlockedSlot {
  id: number
  block_type: string
  master_id: number | null
  post_id: number | null
  service_id: number | null
  start_date: string
  end_date: string
  start_time: string | null
  end_time: string | null
  reason: string | null
  created_at: string
  master_name: string | null
  post_number: number | null
  service_name: string | null
}

export interface BlockedSlotListResponse {
  items: BlockedSlot[]
  total: number
}

export interface BlockedSlotCreateRequest {
  block_type: string
  master_id?: number
  post_id?: number
  service_id?: number
  start_date: string
  end_date: string
  start_time?: string
  end_time?: string
  reason?: string
}

export const blocksApi = {
  getBlocks: async (
    startDate?: string,
    endDate?: string,
    blockType?: string
  ): Promise<BlockedSlotListResponse> => {
    let url = '/api/blocks?'
    if (startDate) url += `start_date=${startDate}&`
    if (endDate) url += `end_date=${endDate}&`
    if (blockType) url += `block_type=${blockType}&`
    const response = await apiClient.get(url)
    return response.data
  },

  createBlock: async (data: BlockedSlotCreateRequest): Promise<BlockedSlot> => {
    const response = await apiClient.post('/api/blocks', data)
    return response.data
  },

  deleteBlock: async (blockId: number): Promise<void> => {
    await apiClient.delete(`/api/blocks/${blockId}`)
  },

  toggleAccepting: async (accepting: boolean): Promise<{ accepting: boolean; message: string }> => {
    const response = await apiClient.patch(`/api/blocks/toggle-accepting?accepting=${accepting}`)
    return response.data
  },
}

