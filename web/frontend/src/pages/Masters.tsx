import { useState, useEffect } from 'react'
import { mastersApi, Master, MasterCreateRequest } from '../api/masters'
import { settingsApi } from '../api/settings'
import { bookingsApi } from '../api/bookings'
import './Masters.css'

function Masters() {
  const [masters, setMasters] = useState<Master[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingMaster, setEditingMaster] = useState<Master | null>(null)
  const [showWorkOrderModal, setShowWorkOrderModal] = useState(false)
  const [selectedMaster, setSelectedMaster] = useState<Master | null>(null)
  const [workOrderDate, setWorkOrderDate] = useState(new Date().toISOString().split('T')[0])
  const [workOrderBookings, setWorkOrderBookings] = useState<any[]>([])
  const [loadingWorkOrder, setLoadingWorkOrder] = useState(false)
  
  const pageSize = 20

  useEffect(() => {
    loadMasters()
  }, [page])

  const loadMasters = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await mastersApi.getMasters(page, pageSize, search || undefined)
      setMasters(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки мастеров:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadMasters()
  }

  const handleCreate = async (data: MasterCreateRequest) => {
    try {
      await mastersApi.createMaster(data)
      setShowCreateModal(false)
      loadMasters()
    } catch (error: any) {
      console.error('Ошибка создания мастера:', error)
      const message = error.response?.data?.detail || 'Не удалось создать мастера'
      alert(message)
    }
  }

  const handleUpdate = async (masterId: number, data: Partial<MasterCreateRequest>) => {
    try {
      await mastersApi.updateMaster(masterId, data)
      setShowEditModal(false)
      setEditingMaster(null)
      loadMasters()
    } catch (error: any) {
      console.error('Ошибка обновления мастера:', error)
      alert('Не удалось обновить мастера')
    }
  }

  const handleDelete = async (masterId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этого мастера?')) {
      return
    }
    
    try {
      await mastersApi.deleteMaster(masterId)
      loadMasters()
    } catch (error: any) {
      console.error('Ошибка удаления мастера:', error)
      alert('Не удалось удалить мастера')
    }
  }

  const handleEdit = (master: Master) => {
    setEditingMaster(master)
    setShowEditModal(true)
  }

  const handleViewWorkOrder = async (master: Master) => {
    setSelectedMaster(master)
    setWorkOrderDate('') // Пустая дата = за все время
    setShowWorkOrderModal(true)
    await loadWorkOrder(master.id, '')
  }

  const loadWorkOrder = async (masterId: number, date: string) => {
    try {
      setLoadingWorkOrder(true)
      // Если дата не указана, загружаем все записи мастера
      if (!date) {
        // Загружаем все записи мастера (confirmed и new)
        let allBookings: any[] = []
        let page = 1
        const pageSize = 1000
        
        // Загружаем confirmed
        const confirmedData = await bookingsApi.getBookings(page, pageSize, {
          master_id: masterId,
          status: 'confirmed'
        })
        allBookings = [...allBookings, ...confirmedData.items]
        
        // Загружаем new
        const newData = await bookingsApi.getBookings(page, pageSize, {
          master_id: masterId,
          status: 'new'
        })
        allBookings = [...allBookings, ...newData.items]
        
        // Сортируем по дате услуги и времени
        allBookings.sort((a, b) => {
          const dateA = new Date(`${a.service_date}T${a.time}`)
          const dateB = new Date(`${b.service_date}T${b.time}`)
          return dateA.getTime() - dateB.getTime()
        })
        
        setWorkOrderBookings(allBookings)
      } else {
        const data = await mastersApi.getMasterSchedule(masterId, date)
        setWorkOrderBookings(data.bookings)
      }
    } catch (error: any) {
      console.error('Ошибка загрузки лист-наряда:', error)
      alert('Не удалось загрузить лист-наряд')
      setWorkOrderBookings([])
    } finally {
      setLoadingWorkOrder(false)
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Мастера</h1>
      </div>

      <div className="masters-filters">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Поиск по имени или телефону..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn-search">🔍 Поиск</button>
        </form>
        <button className="btn-primary btn-add-master" onClick={() => setShowCreateModal(true)}>
          + Добавить мастера
        </button>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : masters.length === 0 ? (
        <div className="empty-state">
          <p>Мастера не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>ФИО</th>
                  <th>Специализация</th>
                  <th>Телефон</th>
                  <th>Telegram ID</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {masters.map((master) => (
                      <tr key={master.id}>
                        <td>{master.id}</td>
                        <td>{master.full_name}</td>
                        <td>{master.is_universal ? 'Универсальный мастер' : (master.specialization || '-')}</td>
                        <td>{master.phone || '-'}</td>
                    <td>{master.telegram_id || '-'}</td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-sm btn-view" onClick={() => handleViewWorkOrder(master)}>
                          📋 Лист-наряд
                        </button>
                        <button className="btn-sm btn-edit" onClick={() => handleEdit(master)}>
                          ✏️ Редактировать
                        </button>
                        <button className="btn-sm btn-delete" onClick={() => handleDelete(master.id)}>
                          🗑️ Удалить
                        </button>
                      </div>
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

      {showCreateModal && (
        <MasterModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {showEditModal && editingMaster && (
        <MasterModal
          master={editingMaster}
          onClose={() => {
            setShowEditModal(false)
            setEditingMaster(null)
          }}
          onSave={(data) => handleUpdate(editingMaster.id, data)}
        />
      )}

      {showWorkOrderModal && selectedMaster && (
        <WorkOrderModal
          master={selectedMaster}
          date={workOrderDate}
          bookings={workOrderBookings}
          loading={loadingWorkOrder}
          onDateChange={(newDate) => {
            setWorkOrderDate(newDate)
            loadWorkOrder(selectedMaster.id, newDate)
          }}
          onClose={() => {
            setShowWorkOrderModal(false)
            setSelectedMaster(null)
            setWorkOrderBookings([])
          }}
        />
      )}
    </div>
  )
}

interface WorkOrderModalProps {
  master: Master
  date: string
  bookings: any[]
  loading: boolean
  onDateChange: (date: string) => void
  onClose: () => void
}

function WorkOrderModal({ master, date, bookings, loading, onDateChange, onClose }: WorkOrderModalProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      weekday: 'long'
    })
  }

  const formatTime = (timeString: string) => {
    return timeString.substring(0, 5)
  }

  const formatDateShort = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📋 Лист-наряд: {master.full_name}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="form-group">
            <label>Дата</label>
            <input
              type="date"
              value={date}
              onChange={(e) => onDateChange(e.target.value)}
              className="form-input"
            />
          </div>

          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : bookings.length === 0 ? (
            <div className="empty-state">
              <p>{date ? `На ${formatDate(date)} записей нет` : 'Записей нет'}</p>
            </div>
          ) : (
            <div className="work-order-content">
              <div className="work-order-header">
                <h3>{date ? `Лист-наряд на ${formatDate(date)}` : 'Лист-наряд (все записи)'}</h3>
                <div className="work-order-count">Всего записей: {bookings.length}</div>
              </div>

              <div className="work-order-list">
                {bookings.map((booking, index) => (
                  <div key={booking.id} className="work-order-item">
                    <div className="work-order-number">{index + 1}</div>
                    <div className="work-order-details">
                      <div className="work-order-time">
                        📅 {formatDateShort(booking.service_date)} ⏰ {formatTime(booking.time)} - {formatTime(booking.end_time || booking.time)}
                      </div>
                      <div className="work-order-service">
                        🛠️ {booking.service_name || 'Не указана'}
                      </div>
                      <div className="work-order-client">
                        👤 {booking.client_name || 'Неизвестно'}
                        {booking.client_phone && ` (${booking.client_phone})`}
                      </div>
                      {booking.post_number && (
                        <div className="work-order-post">
                          🏢 Пост №{booking.post_number}
                        </div>
                      )}
                      <div className="work-order-status">
                        📊 Статус: <span className={`status status-${booking.status}`}>{booking.status}</span>
                      </div>
                      {booking.comment && (
                        <div className="work-order-comment">
                          💬 {booking.comment}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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

interface MasterModalProps {
  master?: Master
  onClose: () => void
  onSave: (data: MasterCreateRequest) => void
}

function MasterModal({ master, onClose, onSave }: MasterModalProps) {
  // Определяем начальное значение специализации: если is_universal = true, то "Универсальный мастер"
  const initialSpecialization = master?.is_universal 
    ? 'Универсальный мастер' 
    : (master?.specialization ?? '')

  const [formData, setFormData] = useState<MasterCreateRequest>({
    user_id: master?.user_id || undefined,
    full_name: master?.full_name || '',
    phone: master?.phone || '',
    telegram_id: master?.telegram_id || undefined,
    specialization: initialSpecialization || undefined,
    is_universal: master?.is_universal ?? false,
  })
  const [specializationOptions, setSpecializationOptions] = useState<string[]>([])

  useEffect(() => {
    const loadSpecializations = async () => {
      try {
        const setting = await settingsApi.getSetting('master_specializations')
        const options = setting.value
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean)
        setSpecializationOptions(options)
      } catch (error) {
        console.error('Ошибка загрузки специализаций:', error)
        setSpecializationOptions([])
      }
    }

    loadSpecializations()
  }, [])

  const handleSpecializationChange = (value: string) => {
    const isUniversal = value === 'Универсальный мастер'
    setFormData({ 
      ...formData, 
      specialization: isUniversal ? 'Универсальный мастер' : (value || undefined),
      is_universal: isUniversal
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // При сохранении: если выбрана "Универсальный мастер", то specialization = "Универсальный мастер", is_universal = true
    // Иначе specialization = выбранное значение, is_universal = false
    const finalData = {
      ...formData,
      is_universal: formData.specialization === 'Универсальный мастер'
    }
    onSave(finalData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{master ? 'Редактировать мастера' : 'Создать мастера'}</h2>
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
          
          <div className="form-row">
            <div className="form-group">
              <label>Телефон</label>
              <input
                type="text"
                value={formData.phone || ''}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value || undefined })}
                className="form-input"
                placeholder="+7 (999) 123-45-67"
              />
            </div>
            
            <div className="form-group">
              <label>Telegram ID</label>
              <input
                type="number"
                value={formData.telegram_id || ''}
                onChange={(e) => setFormData({ ...formData, telegram_id: e.target.value ? parseInt(e.target.value) : undefined })}
                className="form-input"
                placeholder="329621295"
              />
            </div>
          </div>
          
          <div className="form-group">
            <label>Специализация</label>
            <select
              value={formData.specialization ?? ''}
              onChange={(e) => handleSpecializationChange(e.target.value)}
              className="form-input"
            >
              <option value="">Не выбрана</option>
              <option value="Универсальный мастер">Универсальный мастер</option>
              {specializationOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
          
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              {master ? 'Сохранить' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Masters
