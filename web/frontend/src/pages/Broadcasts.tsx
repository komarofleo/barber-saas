import { useState, useEffect } from 'react'
import { broadcastsApi, Broadcast, BroadcastCreateRequest } from '../api/broadcasts'
import { clientsApi, Client } from '../api/clients'
import { SuccessNotification } from '../components/SuccessNotification'
import './Broadcasts.css'

type TargetAudience = 'all' | 'active' | 'new' | 'selected_clients'

function Broadcasts() {
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [preSelectedClients, setPreSelectedClients] = useState<number[]>([])
  const [showSuccessNotification, setShowSuccessNotification] = useState(false)
  
  const pageSize = 20

  useEffect(() => {
    loadBroadcasts()
  }, [page, statusFilter])

  const loadBroadcasts = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await broadcastsApi.getBroadcasts(
        page, 
        pageSize, 
        statusFilter !== 'all' ? statusFilter : undefined
      )
      setBroadcasts(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки рассылок:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (data: BroadcastCreateRequest) => {
    try {
      await broadcastsApi.createBroadcast(data)
      setShowCreateModal(false)
      setPreSelectedClients([])
      setShowSuccessNotification(true)
      loadBroadcasts()
    } catch (error: any) {
      console.error('Ошибка создания рассылки:', error)
      alert(error.response?.data?.detail || 'Не удалось создать рассылку')
    }
  }

  const handleDelete = async (broadcastId: number) => {
    if (!confirm('Вы уверены, что хотите удалить эту рассылку?')) {
      return
    }
    
    try {
      await broadcastsApi.deleteBroadcast(broadcastId)
      loadBroadcasts()
    } catch (error: any) {
      console.error('Ошибка удаления рассылки:', error)
      alert('Не удалось удалить рассылку')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusLabel = (status: string) => {
    const labels: { [key: string]: string } = {
      pending: 'Ожидает',
      sending: 'Отправляется',
      completed: 'Завершена',
      failed: 'Ошибка'
    }
    return labels[status] || status
  }

  const getStatusClass = (status: string) => {
    return `status status-${status}`
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      {showSuccessNotification && (
        <SuccessNotification
          message="Сообщение отправлено"
          onClose={() => setShowSuccessNotification(false)}
        />
      )}
      <div className="page-header-simple">
        <h1>Рассылки</h1>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          + Создать рассылку
        </button>
      </div>

      <div className="broadcasts-filters">
        <div className="filter-group">
          <button
            className={`filter-btn ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            Все
          </button>
          <button
            className={`filter-btn ${statusFilter === 'pending' ? 'active' : ''}`}
            onClick={() => setStatusFilter('pending')}
          >
            Ожидают
          </button>
          <button
            className={`filter-btn ${statusFilter === 'sending' ? 'active' : ''}`}
            onClick={() => setStatusFilter('sending')}
          >
            Отправляются
          </button>
          <button
            className={`filter-btn ${statusFilter === 'completed' ? 'active' : ''}`}
            onClick={() => setStatusFilter('completed')}
          >
            Завершены
          </button>
          <button
            className={`filter-btn ${statusFilter === 'failed' ? 'active' : ''}`}
            onClick={() => setStatusFilter('failed')}
          >
            Ошибки
          </button>
        </div>
      </div>

      {showCreateModal && (
        <CreateBroadcastModal
          preSelectedClients={preSelectedClients}
          onClose={() => {
            setShowCreateModal(false)
            setPreSelectedClients([])
          }}
          onSave={handleCreate}
        />
      )}

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : broadcasts.length === 0 ? (
        <div className="empty-state">
          <p>Рассылки не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Текст</th>
                  <th>Аудитория</th>
                  <th>Статус</th>
                  <th>Отправлено</th>
                  <th>Ошибок</th>
                  <th>Создана</th>
                  <th>Отправлена</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {broadcasts.map((broadcast) => (
                  <tr key={broadcast.id}>
                    <td>{broadcast.id}</td>
                    <td className="broadcast-text">
                      {broadcast.text.length > 50 
                        ? `${broadcast.text.substring(0, 50)}...` 
                        : broadcast.text}
                      {broadcast.image_path && <span className="image-badge">📷</span>}
                    </td>
                    <td>{getAudienceLabel(broadcast.target_audience)}</td>
                    <td>
                      <span className={getStatusClass(broadcast.status)}>
                        {getStatusLabel(broadcast.status)}
                      </span>
                    </td>
                    <td>{broadcast.total_sent}</td>
                    <td>{broadcast.total_errors}</td>
                    <td>{formatDate(broadcast.created_at)}</td>
                    <td>{broadcast.sent_at ? formatDate(broadcast.sent_at) : '-'}</td>
                    <td>
                      <button 
                        className="btn-sm btn-delete" 
                        onClick={() => handleDelete(broadcast.id)}
                      >
                        🗑️ Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination-btn"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                ‹ Назад
              </button>
              <span className="pagination-info">
                Страница {page} из {totalPages} (всего: {total})
              </span>
              <button
                className="pagination-btn"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Вперед ›
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function getAudienceLabel(audience: string): string {
  const labels: { [key: string]: string } = {
    all: 'Все пользователи',
    active: 'Активные пользователи',
    new: 'Новые пользователи',
    selected_clients: 'Выбранные клиенты',
    by_service: 'По услуге'
  }
  return labels[audience] || audience
}

interface CreateBroadcastModalProps {
  preSelectedClients?: number[]
  onClose: () => void
  onSave: (data: BroadcastCreateRequest) => void
}

function CreateBroadcastModal({ preSelectedClients = [], onClose, onSave }: CreateBroadcastModalProps) {
  const [text, setText] = useState('')
  const [targetAudience, setTargetAudience] = useState<TargetAudience>('all')
  const [selectedClients, setSelectedClients] = useState<number[]>(preSelectedClients)
  const [clients, setClients] = useState<Client[]>([])
  const [loadingClients, setLoadingClients] = useState(false)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (preSelectedClients.length > 0) {
      setTargetAudience('selected_clients')
      setSelectedClients(preSelectedClients)
    }
  }, [preSelectedClients])

  useEffect(() => {
    if (targetAudience === 'selected_clients') {
      loadClients()
    }
  }, [targetAudience])

  const loadClients = async () => {
    try {
      setLoadingClients(true)
      // Загружаем все клиенты
      let allClients: Client[] = []
      let page = 1
      const pageSize = 100
      let hasMore = true
      
      while (hasMore) {
        const data = await clientsApi.getClients(page, pageSize)
        allClients = [...allClients, ...data.items]
        
        if (data.items.length < pageSize || allClients.length >= data.total) {
          hasMore = false
        } else {
          page++
        }
      }
      
      setClients(allClients)
    } catch (error: any) {
      console.error('Ошибка загрузки клиентов:', error)
    } finally {
      setLoadingClients(false)
    }
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImageFile(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!text.trim()) {
      alert('Введите текст рассылки')
      return
    }

    try {
      setUploading(true)
      let imagePath: string | null = null

      // Загружаем изображение если есть
      if (imageFile) {
        const uploadResult = await broadcastsApi.uploadImage(imageFile)
        imagePath = uploadResult.image_path
      }

      const broadcastData: BroadcastCreateRequest = {
        text: text.trim(),
        image_path: imagePath,
        target_audience: targetAudience,
        filter_params: targetAudience === 'selected_clients' 
          ? { client_ids: selectedClients }
          : undefined
      }

      await onSave(broadcastData)
    } catch (error: any) {
      console.error('Ошибка создания рассылки:', error)
      alert(error.response?.data?.detail || 'Не удалось создать рассылку')
    } finally {
      setUploading(false)
    }
  }

  const toggleClient = (clientId: number) => {
    setSelectedClients(prev => 
      prev.includes(clientId)
        ? prev.filter(id => id !== clientId)
        : [...prev, clientId]
    )
  }

  const selectAllClients = () => {
    setSelectedClients(clients.map(c => c.id))
  }

  const deselectAllClients = () => {
    setSelectedClients([])
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Создать рассылку</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Текст сообщения *</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="form-textarea"
                rows={5}
                placeholder="Введите текст рассылки..."
                required
              />
            </div>

            <div className="form-group">
              <label>Изображение (необязательно)</label>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="form-input"
              />
              {imagePreview && (
                <div className="image-preview">
                  <img src={imagePreview} alt="Preview" />
                  <button 
                    type="button"
                    className="btn-remove-image"
                    onClick={() => {
                      setImageFile(null)
                      setImagePreview(null)
                    }}
                  >
                    ✕ Удалить
                  </button>
                </div>
              )}
            </div>

            <div className="form-group">
              <label>Аудитория *</label>
              <select
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value as TargetAudience)}
                className="form-select"
                required
              >
                <option value="all">Все пользователи</option>
                <option value="active">Активные пользователи (с активными записями)</option>
                <option value="new">Новые пользователи (за последние 30 дней)</option>
                <option value="selected_clients">Выбранные клиенты</option>
              </select>
            </div>

            {targetAudience === 'selected_clients' && (
              <div className="form-group">
                <div className="clients-selection-header">
                  <label>Выберите клиентов *</label>
                  <div className="selection-actions">
                    <button type="button" className="btn-link" onClick={selectAllClients}>
                      Выбрать всех
                    </button>
                    <button type="button" className="btn-link" onClick={deselectAllClients}>
                      Снять выбор
                    </button>
                  </div>
                </div>
                {loadingClients ? (
                  <div className="loading">Загрузка клиентов...</div>
                ) : (
                  <div className="clients-selection">
                    {clients.map(client => (
                      <label key={client.id} className="client-checkbox">
                        <input
                          type="checkbox"
                          checked={selectedClients.includes(client.id)}
                          onChange={() => toggleClient(client.id)}
                        />
                        <span>{client.full_name} {client.phone && `(${client.phone})`}</span>
                      </label>
                    ))}
                    {clients.length === 0 && (
                      <div className="empty-state">Клиенты не найдены</div>
                    )}
                  </div>
                )}
                {selectedClients.length > 0 && (
                  <div className="selected-count">
                    Выбрано клиентов: {selectedClients.length}
                  </div>
                )}
              </div>
            )}

            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={onClose} disabled={uploading}>
                Отмена
              </button>
              <button type="submit" className="btn-primary" disabled={uploading}>
                {uploading ? 'Создание...' : 'Создать рассылку'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Broadcasts


