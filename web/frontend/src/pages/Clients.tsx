import { useState, useEffect } from 'react'
import { clientsApi, Client } from '../api/clients'
import { mastersApi } from '../api/masters'
import { usersApi } from '../api/users'
import { useAuth } from '../hooks/useAuth'
import { SuccessNotification } from '../components/SuccessNotification'
import { broadcastsApi } from '../api/broadcasts'
import './Clients.css'

type SortField = 'id' | 'full_name' | 'phone' | 'total_visits' | 'total_amount' | 'created_at' | null
type SortDirection = 'asc' | 'desc'

function Clients() {
  const { user: currentUser } = useAuth()
  const [clients, setClients] = useState<Client[]>([])
  const [allClients, setAllClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showViewModal, setShowViewModal] = useState(false)
  const [viewingClient, setViewingClient] = useState<Client | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingClient, setEditingClient] = useState<Client | null>(null)
  const [showBroadcastModal, setShowBroadcastModal] = useState(false)
  const [selectedClientsForBroadcast, setSelectedClientsForBroadcast] = useState<number[]>([])
  const [showSuccessNotification, setShowSuccessNotification] = useState(false)
  
  // Сортировка
  const [sortField, setSortField] = useState<SortField>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  useEffect(() => {
    loadClients()
  }, [])

  // Применяем сортировку при изменении sortField или sortDirection
  useEffect(() => {
    if (sortField) {
      const sorted = [...allClients].sort((a, b) => {
        let aValue: any = a[sortField as keyof Client]
        let bValue: any = b[sortField as keyof Client]
        
        // Обработка null/undefined
        if (aValue == null || aValue === '') {
          aValue = sortField === 'total_visits' || sortField === 'total_amount' || sortField === 'id' ? 0 : ''
        }
        if (bValue == null || bValue === '') {
          bValue = sortField === 'total_visits' || sortField === 'total_amount' || sortField === 'id' ? 0 : ''
        }
        
        // Для дат
        if (sortField === 'created_at') {
          const aDate = new Date(a.created_at).getTime()
          const bDate = new Date(b.created_at).getTime()
          aValue = aDate
          bValue = bDate
        }
        
        // Для чисел
        if (sortField === 'total_visits' || sortField === 'total_amount' || sortField === 'id') {
          aValue = Number(aValue) || 0
          bValue = Number(bValue) || 0
        }
        
        // Для строк - приводим к нижнему регистру
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          aValue = aValue.toLowerCase()
          bValue = bValue.toLowerCase()
        }
        
        // Сравнение
        if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
        if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
        return 0
      })
      setClients(sorted)
    } else {
      setClients(allClients)
    }
  }, [sortField, sortDirection, allClients])

  const loadClients = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      // Загружаем все клиенты постранично
      let allClientsData: Client[] = []
      let page = 1
      const pageSize = 100
      let hasMore = true
      
      while (hasMore) {
        const data = await clientsApi.getClients(page, pageSize, search || undefined)
        allClientsData = [...allClientsData, ...data.items]
        
        // Проверяем, есть ли еще данные для загрузки
        if (data.items.length < pageSize || allClientsData.length >= data.total || data.total === 0) {
          hasMore = false
        } else {
          page++
        }
      }
      
      setAllClients(allClientsData)
    } catch (error: any) {
      console.error('Ошибка загрузки клиентов:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      } else if (error.response?.status === 403) {
        alert('У вас нет прав для просмотра клиентов. Требуются права администратора.')
        setAllClients([])
      } else {
        console.error('Детали ошибки:', error.response?.data || error.message)
        setAllClients([])
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadClients()
  }

  const handleReset = () => {
    setSearch('')
    setSortField(null)
    setSortDirection('asc')
    loadClients()
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Переключаем направление сортировки
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // Устанавливаем новое поле сортировки
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return '↕️'
    }
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  const handleView = (client: Client) => {
    setViewingClient(client)
    setShowViewModal(true)
  }

  const handleEdit = (client: Client) => {
    setEditingClient(client)
    setShowEditModal(true)
  }

  const handleAssignMaster = async (client: Client) => {
    if (!client.user_id || client.user_id === 0 || !client.user_telegram_id) {
      alert('У клиента нет Telegram ID. Попросите его написать боту /start')
      return
    }

    const confirmAssign = confirm(`Назначить клиента "${client.full_name}" мастером?`)
    if (!confirmAssign) {
      return
    }

    try {
      await mastersApi.createMasterFromClient(client.id)
      alert('Мастер назначен')
    } catch (error: any) {
      console.error('Ошибка назначения мастера:', error)
      alert(error.response?.data?.detail || 'Не удалось назначить мастером')
    }
  }

  const formatCurrency = (amount: number | null) => {
    if (!amount) return '0 ₽'
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  return (
    <div className="page-container">
      {showSuccessNotification && (
        <SuccessNotification
          message="Сообщение отправлено"
          onClose={() => setShowSuccessNotification(false)}
        />
      )}
      <div className="page-header-simple">
        <h1>Клиенты</h1>
      </div>

      <div className="clients-filters">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Поиск по ФИО или телефону..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn-search">🔍 Поиск</button>
          <button type="button" className="btn-reset" onClick={handleReset}>
            🗑️ Сброс
          </button>
        </form>
      </div>

      {showViewModal && viewingClient && (
        <ViewClientModal
          client={viewingClient}
          onClose={() => {
            setShowViewModal(false)
            setViewingClient(null)
          }}
          onAdminToggle={() => {
            loadClients()
          }}
        />
      )}

      {showEditModal && editingClient && (
        <EditClientModal
          client={editingClient}
          onClose={() => {
            setShowEditModal(false)
            setEditingClient(null)
          }}
          onSuccess={() => {
            setShowEditModal(false)
            setEditingClient(null)
            loadClients()
          }}
        />
      )}

      {showBroadcastModal && (
        <BroadcastModal
          preSelectedClients={selectedClientsForBroadcast}
          onClose={() => {
            setShowBroadcastModal(false)
            setSelectedClientsForBroadcast([])
          }}
          onSuccess={() => {
            setShowBroadcastModal(false)
            setSelectedClientsForBroadcast([])
            setShowSuccessNotification(true)
          }}
        />
      )}

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : clients.length === 0 ? (
        <div className="empty-state">
          <p>Клиенты не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={selectedClientsForBroadcast.length === clients.length && clients.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedClientsForBroadcast(clients.map(c => c.id))
                        } else {
                          setSelectedClientsForBroadcast([])
                        }
                      }}
                    />
                  </th>
                  <th className="sortable" onClick={() => handleSort('id')}>
                    ID {getSortIcon('id')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('full_name')}>
                    ФИО {getSortIcon('full_name')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('phone')}>
                    Телефон {getSortIcon('phone')}
                  </th>
                  <th>Telegram ID</th>
                  <th className="sortable" onClick={() => handleSort('total_visits')}>
                    Визитов {getSortIcon('total_visits')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('total_amount')}>
                    Сумма {getSortIcon('total_amount')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('created_at')}>
                    Дата регистрации {getSortIcon('created_at')}
                  </th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((client) => (
                  <tr key={client.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedClientsForBroadcast.includes(client.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedClientsForBroadcast([...selectedClientsForBroadcast, client.id])
                          } else {
                            setSelectedClientsForBroadcast(selectedClientsForBroadcast.filter(id => id !== client.id))
                          }
                        }}
                      />
                    </td>
                    <td>{client.id}</td>
                    <td>{client.full_name}</td>
                    <td>{client.phone || '-'}</td>
                    <td>{client.user_telegram_id || '-'}</td>
                    <td>{client.total_visits}</td>
                    <td>{formatCurrency(client.total_amount)}</td>
                  <td>{formatDate(client.created_at)}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn-sm btn-view" onClick={() => handleView(client)}>
                        👁️ Просмотр
                      </button>
                      <button className="btn-sm btn-edit" onClick={() => handleEdit(client)}>
                        ✏️ Редактировать
                      </button>
                      <button className="btn-sm" onClick={() => handleAssignMaster(client)}>
                        🧑‍🔧 В мастера
                      </button>
                    </div>
                  </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="table-info">
            Всего клиентов: {clients.length}
          </div>
        </>
      )}
    </div>
  )
}

interface ViewClientModalProps {
  client: Client
  onClose: () => void
  onAdminToggle?: () => void
}

function ViewClientModal({ client, onClose, onAdminToggle }: ViewClientModalProps) {
  const { user: currentUser } = useAuth()
  const [isAdmin, setIsAdmin] = useState<boolean | null>(client.user_is_admin ?? null)
  const [togglingAdmin, setTogglingAdmin] = useState(false)

  // Обновляем isAdmin при изменении client
  useEffect(() => {
    setIsAdmin(client.user_is_admin ?? null)
  }, [client.user_is_admin])

  const handleToggleAdmin = async () => {
    if (!client.user_id || !currentUser?.is_admin) return
    
    try {
      setTogglingAdmin(true)
      await usersApi.toggleAdmin(client.user_id, !isAdmin)
      setIsAdmin(!isAdmin)
      if (onAdminToggle) {
        onAdminToggle()
      }
    } catch (error: any) {
      console.error('Ошибка изменения статуса администратора:', error)
      alert(error.response?.data?.detail || 'Не удалось изменить статус администратора')
    } finally {
      setTogglingAdmin(false)
    }
  }
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Клиент: {client.full_name}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="client-details-grid">
            <div className="client-detail-section">
              <h3 className="detail-section-title">👤 Контактная информация</h3>
              <div className="detail-item">
                <div className="detail-label">ФИО:</div>
                <div className="detail-value">{client.full_name}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Телефон:</div>
                <div className="detail-value">{client.phone || '-'}</div>
              </div>
              {client.user_telegram_id && (
                <div className="detail-item">
                  <div className="detail-label">Telegram ID:</div>
                  <div className="detail-value">{client.user_telegram_id}</div>
                </div>
              )}
              {(client.user_first_name || client.user_last_name) && (
                <div className="detail-item">
                  <div className="detail-label">Имя в Telegram:</div>
                  <div className="detail-value">
                    {[client.user_first_name, client.user_last_name].filter(Boolean).join(' ') || '-'}
                  </div>
                </div>
              )}
              {client.user_id && currentUser?.is_admin && (
                <div className="detail-item">
                  <div className="detail-label">Статус администратора:</div>
                  <div className="detail-value">
                    {isAdmin !== null ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className={`badge ${isAdmin ? 'badge-success' : 'badge-default'}`}>
                          {isAdmin ? 'Администратор' : 'Не администратор'}
                        </span>
                        <button
                          className="btn-sm"
                          onClick={handleToggleAdmin}
                          disabled={togglingAdmin}
                          style={{ marginLeft: '10px' }}
                        >
                          {togglingAdmin ? '...' : isAdmin ? '❌ Снять админа' : '✅ Назначить админом'}
                        </button>
                      </div>
                    ) : (
                      '-'
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="client-detail-section">
              <h3 className="detail-section-title">📊 Статистика</h3>
              <div className="detail-item">
                <div className="detail-label">Всего визитов:</div>
                <div className="detail-value">{client.total_visits}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Общая сумма:</div>
                <div className="detail-value detail-value-amount">
                  {new Intl.NumberFormat('ru-RU', {
                    style: 'currency',
                    currency: 'RUB',
                    minimumFractionDigits: 0
                  }).format(client.total_amount || 0)}
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Дата регистрации:</div>
                <div className="detail-value">
                  {new Date(client.created_at).toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Компонент модального окна для создания рассылки из страницы клиентов
interface BroadcastModalProps {
  preSelectedClients: number[]
  onClose: () => void
  onSuccess: () => void
}

function BroadcastModal({ preSelectedClients, onClose, onSuccess }: BroadcastModalProps) {
  const [text, setText] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

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

      if (imageFile) {
        const uploadResult = await broadcastsApi.uploadImage(imageFile)
        imagePath = uploadResult.image_path
      }

      await broadcastsApi.createBroadcast({
        text: text.trim(),
        image_path: imagePath,
        target_audience: 'selected_clients',
        filter_params: { client_ids: preSelectedClients }
      })

      onSuccess()
    } catch (error: any) {
      console.error('Ошибка создания рассылки:', error)
      alert(error.response?.data?.detail || 'Не удалось создать рассылку')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Создать рассылку для выбранных клиентов</h2>
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
              <div className="selected-count">
                Будет отправлено {preSelectedClients.length} клиентам
              </div>
            </div>

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

interface EditClientModalProps {
  client: Client
  onClose: () => void
  onSuccess: () => void
}

function EditClientModal({ client, onClose, onSuccess }: EditClientModalProps) {
  const { user: currentUser } = useAuth()
  const [formData, setFormData] = useState({
    full_name: client.full_name,
    phone: client.phone || '',
  })
  const [isAdmin, setIsAdmin] = useState<boolean | null>(client.user_is_admin ?? null)
  const [loading, setLoading] = useState(false)
  const [togglingAdmin, setTogglingAdmin] = useState(false)

  // Обновляем isAdmin при изменении client
  useEffect(() => {
    setIsAdmin(client.user_is_admin ?? null)
  }, [client.user_is_admin])

  const handleToggleAdmin = async () => {
    if (!client.user_id || !currentUser?.is_admin) return
    
    try {
      setTogglingAdmin(true)
      await usersApi.toggleAdmin(client.user_id, !isAdmin)
      setIsAdmin(!isAdmin)
      onSuccess() // Обновляем список клиентов
    } catch (error: any) {
      console.error('Ошибка изменения статуса администратора:', error)
      alert(error.response?.data?.detail || 'Не удалось изменить статус администратора')
    } finally {
      setTogglingAdmin(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.full_name || !formData.phone) {
      alert('Заполните обязательные поля: ФИО и Телефон')
      return
    }

    try {
      setLoading(true)
      await clientsApi.updateClient(client.id, {
        full_name: formData.full_name,
        phone: formData.phone,
      })
      onSuccess()
    } catch (error: any) {
      console.error('Ошибка обновления клиента:', error)
      alert(error.response?.data?.detail || 'Не удалось обновить клиента')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Редактировать клиента</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>ФИО *</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              required
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label>Телефон *</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              required
              className="form-input"
            />
          </div>

          {client.user_id && currentUser?.is_admin && (
            <div className="form-group">
              <label>Статус администратора</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '8px' }}>
                <span className={`badge ${isAdmin ? 'badge-success' : 'badge-default'}`}>
                  {isAdmin !== null ? (isAdmin ? 'Администратор' : 'Не администратор') : 'Неизвестно'}
                </span>
                <button
                  type="button"
                  className="btn-sm"
                  onClick={handleToggleAdmin}
                  disabled={togglingAdmin || isAdmin === null}
                >
                  {togglingAdmin ? '...' : isAdmin ? '❌ Снять админа' : '✅ Назначить админом'}
                </button>
              </div>
            </div>
          )}

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Clients
