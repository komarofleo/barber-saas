import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { bookingsApi, Booking, BookingCreateRequest } from '../api/bookings'
import { clientsApi, Client } from '../api/clients'
import { servicesApi, Service } from '../api/services'
import { mastersApi, Master } from '../api/masters'
import { postsApi, Post } from '../api/posts'
import { SuccessNotification } from '../components/SuccessNotification'
import './Bookings.css'

type SortField = 'id' | 'date' | 'master_name' | 'service_name' | 'post_number' | 'status' | null
type SortDirection = 'asc' | 'desc'

function Bookings() {
  const [searchParams, setSearchParams] = useSearchParams()
  
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showViewModal, setShowViewModal] = useState(false)
  const [viewingBooking, setViewingBooking] = useState<Booking | null>(null)
  const [showSuccessNotification, setShowSuccessNotification] = useState(false)
  
  // Фильтры - читаем из URL или используем значения по умолчанию
  const [searchName, setSearchName] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || 'all')
  const [dateCreatedFrom, setDateCreatedFrom] = useState('')
  const [dateCreatedTo, setDateCreatedTo] = useState('')
  const [selectedDates, setSelectedDates] = useState<string[]>([])
  
  // Сортировка - читаем из URL или используем значения по умолчанию
  const urlSortField = searchParams.get('sort') as SortField
  const urlSortDirection = searchParams.get('sortDir') as SortDirection
  const [sortField, setSortField] = useState<SortField>(urlSortField || null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(urlSortDirection || 'asc')

  const [allBookings, setAllBookings] = useState<Booking[]>([])

  // Загружаем данные при изменении фильтров
  useEffect(() => {
    loadBookings()
  }, [statusFilter, dateCreatedFrom, dateCreatedTo, searchName])

  // Применяем фильтрацию по выбранным датам и сортировку
  useEffect(() => {
    console.log('🔄 Применение фильтрации и сортировки:', { 
      selectedDates, 
      allBookingsCount: allBookings.length,
      sortField,
      sortDirection 
    })
    
    // Сначала фильтруем по выбранным датам
    let filtered = allBookings
    if (selectedDates.length > 0) {
      filtered = allBookings.filter(b => {
        // Нормализуем дату записи (может быть строкой или объектом Date)
        const bookingDate = typeof b.date === 'string' 
          ? (b.date.includes('T') ? b.date.split('T')[0] : b.date)
          : b.date
        const isIncluded = selectedDates.includes(bookingDate)
        return isIncluded
      })
      console.log('📅 Отфильтровано по датам:', { 
        selectedDates, 
        filteredCount: filtered.length,
        allCount: allBookings.length 
      })
    }
    
    // Затем применяем сортировку
    if (sortField) {
      const sorted = [...filtered].sort((a, b) => {
        let aValue: any = a[sortField as keyof Booking]
        let bValue: any = b[sortField as keyof Booking]
        
        // Обработка null/undefined
        if (aValue == null || aValue === '') aValue = sortField === 'date' ? new Date(0) : (sortField === 'id' ? 0 : '')
        if (bValue == null || bValue === '') bValue = sortField === 'date' ? new Date(0) : (sortField === 'id' ? 0 : '')
        
        // Для ID - преобразуем в число для сравнения
        if (sortField === 'id') {
          aValue = typeof aValue === 'number' ? aValue : parseInt(aValue) || 0
          bValue = typeof bValue === 'number' ? bValue : parseInt(bValue) || 0
        }
        
        // Для дат - преобразуем в Date для сравнения
        if (sortField === 'date') {
          const aDate = new Date(a.date + 'T' + (a.time || '00:00'))
          const bDate = new Date(b.date + 'T' + (b.time || '00:00'))
          aValue = aDate.getTime()
          bValue = bDate.getTime()
        }
        
        // Для строк - приводим к нижнему регистру для сравнения
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          aValue = aValue.toLowerCase()
          bValue = bValue.toLowerCase()
        }
        
        // Сравнение
        if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
        if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
        return 0
      })
      setBookings(sorted)
    } else {
      setBookings(filtered)
    }
  }, [sortField, sortDirection, allBookings, selectedDates])

  const loadBookings = async () => {
    try {
      setLoading(true)
      const filters: any = {}
      
      if (statusFilter !== 'all') {
        filters.status = statusFilter
      }
      
      if (dateCreatedFrom) {
        filters.start_date = dateCreatedFrom
      }
      
      if (dateCreatedTo) {
        filters.end_date = dateCreatedTo
      }
      
      if (searchName) {
        filters.search = searchName
      }
      
      const data = await bookingsApi.getBookings(1, 1000, filters)
      
      // Сохраняем все загруженные данные (фильтрация по selectedDates будет применена в useEffect)
      setAllBookings(data.items)
    } catch (error: any) {
      console.error('Ошибка загрузки записей:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleView = async (booking: Booking) => {
    try {
      const fullBooking = await bookingsApi.getBooking(booking.id)
      setViewingBooking(fullBooking)
      setShowViewModal(true)
    } catch (error: any) {
      console.error('Ошибка загрузки записи:', error)
      alert('Не удалось загрузить запись')
    }
  }

  const handleStatusChange = async (bookingId: number, newStatus: string) => {
    console.log('🔄 Начало смены статуса:', { bookingId, newStatus })
    try {
      const updatedBooking = await bookingsApi.updateBooking(bookingId, { status: newStatus })
      console.log('✅ Статус обновлен, получен ответ:', updatedBooking)
      
      // Обновляем запись в списке без полной перезагрузки
      setBookings(prevBookings => 
        prevBookings.map(booking => 
          booking.id === bookingId ? { ...booking, ...updatedBooking } : booking
        )
      )
      
      // Обновляем просматриваемую запись
      if (viewingBooking && viewingBooking.id === bookingId) {
        setViewingBooking({ ...viewingBooking, ...updatedBooking })
      }
      
      // Показываем уведомление при смене статуса, если есть telegram_id у клиента
      // Показываем всегда, если задача поставлена в очередь (notification_sent) или есть telegram_id
      const hasTelegramId = updatedBooking.client_telegram_id && updatedBooking.client_telegram_id > 0
      const taskQueued = updatedBooking.notification_sent === true
      const shouldShowNotification = taskQueued || hasTelegramId
      
      console.log('📋 Проверка показа уведомления:', { 
        notification_sent: updatedBooking.notification_sent, 
        client_telegram_id: updatedBooking.client_telegram_id,
        hasTelegramId,
        taskQueued,
        newStatus,
        shouldShowNotification,
        'updatedBooking': updatedBooking
      })
      
      if (shouldShowNotification) {
        console.log('✅ Показываем уведомление об успешной отправке')
        console.log('📌 showSuccessNotification будет установлен в true')
        setShowSuccessNotification(true)
        console.log('📌 showSuccessNotification установлен, проверка через 100ms:', showSuccessNotification)
        // Проверяем через небольшую задержку
        setTimeout(() => {
          console.log('📌 Проверка showSuccessNotification после установки')
        }, 100)
        // Автоматически скрываем через 5 секунд (увеличено для видимости)
        setTimeout(() => {
          console.log('📌 Скрываем уведомление через 5 секунд')
          setShowSuccessNotification(false)
        }, 5000)
      } else {
        console.log('❌ Не показываем уведомление - нет telegram_id и задача не поставлена')
      }
      
      // Обновляем список в фоне (не блокируем UI)
      setTimeout(() => {
        loadBookings()
      }, 500)
    } catch (error: any) {
      console.error('❌ Ошибка изменения статуса:', error)
      alert('Не удалось изменить статус')
    }
  }

  const handleReset = () => {
    setSearchName('')
    setStatusFilter('all')
    setDateCreatedFrom('')
    setDateCreatedTo('')
    setSelectedDates([])
    setSortField(null)
    setSortDirection('asc')
    setAllBookings([])
    loadBookings()
  }
  
  const handleSort = (field: SortField) => {
    const newParams = new URLSearchParams(searchParams)
    let newDirection: SortDirection = 'asc'
    
    if (sortField === field) {
      newDirection = sortDirection === 'asc' ? 'desc' : 'asc'
    }
    
    setSortField(field)
    setSortDirection(newDirection)
    
    // Обновляем URL параметры
    newParams.set('sort', field || '')
    newParams.set('sortDir', newDirection)
    setSearchParams(newParams)
  }
  
  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return '⇅'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  const handleDateToggle = (date: string) => {
    console.log('📅 handleDateToggle вызван с датой:', date)
    setSelectedDates(prev => {
      const normalizedDate = date.includes('T') ? date.split('T')[0] : date
      const newDates = prev.includes(normalizedDate)
        ? prev.filter(d => d !== normalizedDate)
        : [...prev, normalizedDate]
      console.log('📅 Новые выбранные даты:', newDates)
      return newDates
    })
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  const formatDateTime = (dateString: string, timeString: string) => {
    const date = new Date(dateString)
    const [hours, minutes] = timeString.split(':')
    date.setHours(parseInt(hours), parseInt(minutes))
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getEndDateTime = (booking: Booking) => {
    if (booking.date && booking.end_time) {
      return formatDateTime(booking.date, booking.end_time)
    }
    return '-'
  }

  return (
    <div className="bookings-page">
      {showSuccessNotification && (
        <SuccessNotification
          message="Статус отправлен клиенту"
          onClose={() => {
            console.log('📌 Закрываем уведомление')
            setShowSuccessNotification(false)
          }}
          duration={5000}
        />
      )}
      <div className="page-header">
        <div>
          <h1>Записи</h1>
        </div>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          + Новая запись
        </button>
      </div>

      <div className="bookings-filters-panel">
        <div className="filters-row">
          <div className="filter-item">
            <label>Поиск по фамилии</label>
            <input
              type="text"
              placeholder="Введите фамилию..."
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
              className="filter-input"
            />
          </div>

          <div className="filter-item">
            <label>Статус</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                // Обновляем URL параметр
                const newParams = new URLSearchParams(searchParams)
                if (e.target.value === 'all') {
                  newParams.delete('status')
                } else {
                  newParams.set('status', e.target.value)
                }
                setSearchParams(newParams)
              }}
              className="filter-select"
            >
              <option value="all">Все</option>
              <option value="new">Новые</option>
              <option value="confirmed">Подтвержденные</option>
              <option value="completed">Завершенные</option>
              <option value="cancelled">Отмененные</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Дата создания от</label>
            <input
              type="date"
              value={dateCreatedFrom}
              onChange={(e) => setDateCreatedFrom(e.target.value)}
              className="filter-input"
            />
          </div>

          <div className="filter-item">
            <label>Дата создания до</label>
            <input
              type="date"
              value={dateCreatedTo}
              onChange={(e) => setDateCreatedTo(e.target.value)}
              className="filter-input"
            />
          </div>

          <div className="filter-item">
            <label>Выбор даты записи</label>
            <input
              type="date"
              onChange={(e) => {
                if (e.target.value) {
                  handleDateToggle(e.target.value)
                  e.target.value = ''
                }
              }}
              className="filter-input"
            />
            {selectedDates.length > 0 && (
              <div className="selected-dates">
                {selectedDates.map(date => (
                  <span key={date} className="date-tag">
                    {formatDate(date)}
                    <button
                      className="date-tag-remove"
                      onClick={() => handleDateToggle(date)}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="filters-actions">
          <button className="btn-filter" onClick={loadBookings}>
            🔄 Обновить
          </button>
          <button className="btn-filter btn-reset" onClick={handleReset}>
            🗑️ Сброс
          </button>
        </div>
      </div>

      {showCreateModal && (
        <CreateBookingModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            loadBookings()
          }}
        />
      )}

      {showViewModal && viewingBooking && (
        <ViewBookingModal
          booking={viewingBooking}
          onClose={() => {
            setShowViewModal(false)
            setViewingBooking(null)
          }}
          onStatusChange={handleStatusChange}
          onUpdate={loadBookings}
        />
      )}

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : bookings.length === 0 ? (
        <div className="empty-state">
          <p>Записей не найдено</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th 
                  className="sortable" 
                  onClick={() => handleSort('id')}
                  style={{ cursor: 'pointer' }}
                >
                  ID {getSortIcon('id')}
                </th>
                <th>Клиент</th>
                <th>TGID</th>
                <th>Телефон</th>
                <th>Автомобиль</th>
                <th 
                  className="sortable" 
                  onClick={() => handleSort('date')}
                  style={{ cursor: 'pointer' }}
                >
                  Дата заявки {getSortIcon('date')}
                </th>
                <th 
                  className="sortable" 
                  onClick={() => handleSort('service_name')}
                  style={{ cursor: 'pointer' }}
                >
                  Услуга {getSortIcon('service_name')}
                </th>
                <th 
                  className="sortable" 
                  onClick={() => handleSort('master_name')}
                  style={{ cursor: 'pointer' }}
                >
                  Мастер {getSortIcon('master_name')}
                </th>
                <th 
                  className="sortable" 
                  onClick={() => handleSort('post_number')}
                  style={{ cursor: 'pointer' }}
                >
                  Пост {getSortIcon('post_number')}
                </th>
                <th 
                  className="sortable" 
                  onClick={() => handleSort('status')}
                  style={{ cursor: 'pointer' }}
                >
                  Статус {getSortIcon('status')}
                </th>
                <th>Окончание</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((booking) => (
                <tr key={booking.id}>
                  <td>{booking.id}</td>
                  <td>{booking.client_name || `ID: ${booking.client_id}`}</td>
                  <td>{booking.client_telegram_id || '-'}</td>
                  <td>{booking.client_phone || '-'}</td>
                  <td>
                    {booking.client_car_brand || booking.client_car_model 
                      ? `${booking.client_car_brand || ''} ${booking.client_car_model || ''}`.trim() 
                      : '-'}
                  </td>
                  <td>{formatDate(booking.date)} {booking.time}</td>
                  <td>{booking.service_name || '-'}</td>
                  <td>{booking.master_name || '-'}</td>
                  <td>{booking.post_number ? `№${booking.post_number}` : '-'}</td>
                  <td>
                    <span className={`status status-${booking.status}`}>
                      {booking.status}
                    </span>
                  </td>
                  <td>{getEndDateTime(booking)}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn-sm btn-view" onClick={() => handleView(booking)}>
                        👁️ Просмотр
                      </button>
                      <select
                        className="btn-sm btn-status"
                        value={booking.status}
                        onChange={(e) => handleStatusChange(booking.id, e.target.value)}
                      >
                        <option value="new">Новая</option>
                        <option value="confirmed">Подтверждена</option>
                        <option value="completed">Завершена</option>
                        <option value="cancelled">Отменена</option>
                      </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

interface CreateBookingModalProps {
  onClose: () => void
  onSuccess: () => void
}

function CreateBookingModal({ onClose, onSuccess }: CreateBookingModalProps) {
  const [clients, setClients] = useState<Client[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [masters, setMasters] = useState<Master[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [availableSlots, setAvailableSlots] = useState<string[]>([])
  const [occupiedPostIds, setOccupiedPostIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)
  
  const [formData, setFormData] = useState<BookingCreateRequest>({
    client_id: 0,
    service_id: undefined,
    master_id: undefined,
    post_id: undefined,
    date: new Date().toISOString().split('T')[0],
    time: '',
    duration: 30,
    status: 'new',
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (formData.date && formData.service_id) {
      loadAvailableSlots()
    }
  }, [formData.date, formData.service_id, formData.master_id, formData.post_id])

  // Загрузка занятых постов при изменении даты, времени и длительности
  useEffect(() => {
    if (formData.date && formData.time && formData.duration) {
      loadOccupiedPosts()
    } else {
      setOccupiedPostIds(new Set())
    }
  }, [formData.date, formData.time, formData.duration])

  const loadData = async () => {
    try {
      const [clientsData, servicesData, mastersData, postsData] = await Promise.all([
        clientsApi.getClients(1, 100),
        servicesApi.getServices(1, 100, undefined, true),
        mastersApi.getMasters(1, 100),
        postsApi.getPosts(1, 100, undefined, true),
      ])
      setClients(clientsData.items)
      setServices(servicesData.items)
      setMasters(mastersData.items)
      setPosts(postsData.items)
    } catch (error) {
      console.error('Ошибка загрузки данных:', error)
    }
  }

  const loadAvailableSlots = async () => {
    try {
      const slots = await bookingsApi.getAvailableSlots(
        formData.date,
        formData.service_id,
        formData.master_id,
        formData.post_id
      )
      setAvailableSlots(slots)
    } catch (error) {
      console.error('Ошибка загрузки слотов:', error)
      setAvailableSlots([])
    }
  }

  // Функция для загрузки занятых постов на выбранное время
  const loadOccupiedPosts = async () => {
    if (!formData.date || !formData.time || !formData.duration) {
      setOccupiedPostIds(new Set())
      return
    }

    try {
      // Получаем все записи на выбранную дату
      const bookingsData = await bookingsApi.getBookings(1, 1000, {
        start_date: formData.date,
        end_date: formData.date
      })

      // Вычисляем время начала и конца новой записи
      const [hours, minutes] = formData.time.split(':').map(Number)
      const startTime = new Date(`${formData.date}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`)
      const endTime = new Date(startTime.getTime() + (formData.duration || 30) * 60 * 1000)

      // Находим занятые посты
      const occupied = new Set<number>()
      bookingsData.items.forEach(booking => {
        // Пропускаем отмененные и завершенные записи
        if (booking.status === 'cancelled' || booking.status === 'completed') {
          return
        }

        // Проверяем пересечение времени
        const bookingStart = new Date(`${booking.date}T${booking.time}:00`)
        const bookingEnd = new Date(`${booking.date}T${booking.end_time}:00`)

        // Если времена пересекаются
        if (!(endTime <= bookingStart || startTime >= bookingEnd)) {
          if (booking.post_id) {
            occupied.add(booking.post_id)
          }
        }
      })

      setOccupiedPostIds(occupied)
      console.log('🚫 Занятые посты на', formData.date, formData.time, ':', Array.from(occupied))
    } catch (error) {
      console.error('Ошибка загрузки занятых постов:', error)
      setOccupiedPostIds(new Set())
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.client_id || !formData.date || !formData.time) {
      alert('Заполните все обязательные поля')
      return
    }

    try {
      setLoading(true)
      await bookingsApi.createBooking(formData)
      onSuccess()
    } catch (error: any) {
      console.error('Ошибка создания записи:', error)
      alert(error.response?.data?.detail || 'Не удалось создать запись')
    } finally {
      setLoading(false)
    }
  }

  const selectedService = services.find(s => s.id === formData.service_id)
  if (selectedService && formData.duration !== selectedService.duration) {
    setFormData({ ...formData, duration: selectedService.duration })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Создать новую запись</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Клиент *</label>
            <select
              value={formData.client_id || ''}
              onChange={(e) => setFormData({ ...formData, client_id: parseInt(e.target.value) })}
              required
              className="form-input"
            >
              <option value="">Выберите клиента</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>
                  {client.full_name} {client.phone ? `(${client.phone})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Услуга</label>
              <select
                value={formData.service_id || ''}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  service_id: e.target.value ? parseInt(e.target.value) : undefined 
                })}
                className="form-input"
              >
                <option value="">Не выбрана</option>
                {services.map(service => (
                  <option key={service.id} value={service.id}>
                    {service.name} ({service.duration} мин, {service.price} ₽)
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Длительность (мин)</label>
              <input
                type="number"
                min="1"
                value={formData.duration || 30}
                onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) || 30 })}
                className="form-input"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Мастер</label>
              <select
                value={formData.master_id || ''}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  master_id: e.target.value ? parseInt(e.target.value) : undefined 
                })}
                className="form-input"
              >
                <option value="">Не выбран</option>
                {masters.map(master => (
                  <option key={master.id} value={master.id}>
                    {master.full_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Пост</label>
              <select
                value={formData.post_id || ''}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  post_id: e.target.value ? parseInt(e.target.value) : undefined 
                })}
                className="form-input"
              >
                <option value="">Не выбран</option>
                {posts
                  .filter(post => !occupiedPostIds.has(post.id) || post.id === formData.post_id)
                  .map(post => {
                    const isOccupied = occupiedPostIds.has(post.id) && post.id !== formData.post_id
                    return (
                      <option 
                        key={post.id} 
                        value={post.id}
                        disabled={isOccupied}
                        style={isOccupied ? { color: '#999', fontStyle: 'italic' } : {}}
                      >
                        Пост №{post.number} {post.name ? `(${post.name})` : ''} {isOccupied ? ' (Занят на это время)' : ''}
                      </option>
                    )
                  })}
              </select>
              {occupiedPostIds.size > 0 && formData.time && (
                <small style={{ color: '#666', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                  ⚠️ {occupiedPostIds.size} {occupiedPostIds.size === 1 ? 'пост занят' : 'постов занято'} на выбранное время
                </small>
              )}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Дата *</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
                required
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label>Время *</label>
              <select
                value={formData.time}
                onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                required
                className="form-input"
                disabled={!formData.date || availableSlots.length === 0}
              >
                <option value="">Выберите время</option>
                {availableSlots.map(slot => (
                  <option key={slot} value={slot}>
                    {slot}
                  </option>
                ))}
              </select>
              {formData.date && availableSlots.length === 0 && (
                <small className="text-muted">Нет доступных слотов на эту дату</small>
              )}
            </div>
          </div>

          <div className="form-group">
            <label>Комментарий</label>
            <textarea
              value={formData.comment || ''}
              onChange={(e) => setFormData({ ...formData, comment: e.target.value || undefined })}
              className="form-input"
              rows={3}
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface ViewBookingModalProps {
  booking: Booking
  onClose: () => void
  onStatusChange: (bookingId: number, status: string) => void
  onUpdate: () => void
}

function ViewBookingModal({ booking, onClose, onStatusChange, onUpdate }: ViewBookingModalProps) {
  const [masters, setMasters] = useState<Master[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [editingMaster, setEditingMaster] = useState<number | null>(booking.master_id || null)
  const [editingPost, setEditingPost] = useState<number | null>(booking.post_id || null)
  const [editingDate, setEditingDate] = useState<string>(booking.date)
  const [editingTime, setEditingTime] = useState<string>(booking.time.substring(0, 5))
  const [editingAmount, setEditingAmount] = useState<string>(booking.amount ? booking.amount.toString() : '')
  const [editingPaymentMethod, setEditingPaymentMethod] = useState<string>(booking.payment_method || '')
  const [saving, setSaving] = useState(false)
  const [savingPayment, setSavingPayment] = useState(false)
  const [loadingData, setLoadingData] = useState(true)

  const statusOptions = [
    { value: 'new', label: 'Новая' },
    { value: 'confirmed', label: 'Подтверждена' },
    { value: 'completed', label: 'Завершена' },
    { value: 'cancelled', label: 'Отменена' },
  ]

  const statusLabels: { [key: string]: string } = {
    'new': 'Новая',
    'confirmed': 'Подтверждена',
    'completed': 'Завершена',
    'cancelled': 'Отменена',
  }

  const canEdit = booking.status !== 'completed' && booking.status !== 'cancelled'
  const hasChanges = 
    editingMaster !== (booking.master_id || null) || 
    editingPost !== (booking.post_id || null) ||
    editingDate !== booking.date ||
    editingTime !== booking.time.substring(0, 5)

  useEffect(() => {
    loadMastersAndPosts()
  }, [])

  // Обновляем состояние при изменении booking
  useEffect(() => {
    setEditingMaster(booking.master_id || null)
    setEditingPost(booking.post_id || null)
    setEditingDate(booking.date)
    setEditingTime(booking.time.substring(0, 5))
    setEditingAmount(booking.amount ? booking.amount.toString() : '')
    setEditingPaymentMethod(booking.payment_method || '')
  }, [booking.id, booking.master_id, booking.post_id, booking.date, booking.time, booking.amount, booking.payment_method])
  
  // При смене статуса на "completed" и если есть услуга, подставляем цену как подсказку (только если сумма еще не введена)
  useEffect(() => {
    if (booking.status === 'completed' && !booking.amount && booking.service_id && services.length > 0) {
      const service = services.find(s => s.id === booking.service_id)
      if (service && editingAmount === '') {
        setEditingAmount(service.price.toString())
      }
    }
  }, [booking.status, booking.service_id, services, booking.amount])

  const loadMastersAndPosts = async () => {
    try {
      setLoadingData(true)
      const [mastersData, postsData, servicesData] = await Promise.all([
        mastersApi.getMasters(1, 100),
        postsApi.getPosts(1, 100, undefined, true),
        servicesApi.getServices(1, 100, undefined, true)
      ])
      setMasters(mastersData.items)
      setPosts(postsData.items)
      setServices(servicesData.items)
    } catch (error) {
      console.error('Ошибка загрузки мастеров и постов:', error)
    } finally {
      setLoadingData(false)
    }
  }

  const handleSaveChanges = async () => {
    if (!hasChanges) return

    try {
      setSaving(true)
      // Формируем время в формате HH:MM:SS
      const timeStr = editingTime.length === 5 ? `${editingTime}:00` : editingTime
      
      // Подготавливаем данные для отправки
      const updateData: any = {}
      if (editingMaster !== (booking.master_id || null)) {
        updateData.master_id = editingMaster || undefined
      }
      if (editingPost !== (booking.post_id || null)) {
        updateData.post_id = editingPost || undefined
      }
      if (editingDate !== booking.date) {
        updateData.date = editingDate
      }
      if (editingTime !== booking.time.substring(0, 5)) {
        updateData.time = timeStr
      }
      
      console.log('Отправка данных для обновления:', updateData)
      
      const updatedBooking = await bookingsApi.updateBooking(booking.id, updateData)
      
      // Обновляем локальное состояние после успешного сохранения
      setEditingMaster(updatedBooking.master_id || null)
      setEditingPost(updatedBooking.post_id || null)
      setEditingDate(updatedBooking.date)
      setEditingTime(updatedBooking.time.substring(0, 5))
      
      onUpdate() // Обновить список записей
      alert('Изменения сохранены успешно')
    } catch (error: any) {
      console.error('Ошибка сохранения изменений:', error)
      
      // Правильно обрабатываем ошибку
      let errorMessage = 'Не удалось сохранить изменения'
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (Array.isArray(detail)) {
          // Если detail - массив, берем первое сообщение
          errorMessage = detail.map((item: any) => item.msg || JSON.stringify(item)).join(', ')
        } else if (typeof detail === 'string') {
          errorMessage = detail
        } else {
          errorMessage = JSON.stringify(detail)
        }
      } else if (error.message) {
        errorMessage = error.message
      }
      
      alert(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleSavePayment = async () => {
    try {
      setSavingPayment(true)
      
      const updateData: any = {}
      const amountValue = parseFloat(editingAmount)
      
      if (editingAmount && !isNaN(amountValue) && amountValue > 0) {
        updateData.amount = amountValue
        // Автоматически помечаем как оплаченную при вводе суммы
        updateData.is_paid = true
      } else if (editingAmount === '' || amountValue === 0) {
        // Если сумма очищена, сбрасываем оплату
        updateData.amount = null
        updateData.is_paid = false
      }
      
      if (editingPaymentMethod) {
        updateData.payment_method = editingPaymentMethod
      } else {
        updateData.payment_method = null
      }
      
      console.log('Отправка данных для обновления оплаты:', updateData)
      
      const updatedBooking = await bookingsApi.updateBooking(booking.id, updateData)
      
      // Обновляем локальное состояние
      setEditingAmount(updatedBooking.amount ? updatedBooking.amount.toString() : '')
      setEditingPaymentMethod(updatedBooking.payment_method || '')
      
      onUpdate() // Обновить список записей
      alert('Оплата сохранена успешно')
    } catch (error: any) {
      console.error('Ошибка сохранения оплаты:', error)
      
      let errorMessage = 'Не удалось сохранить оплату'
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (Array.isArray(detail)) {
          errorMessage = detail.map((item: any) => item.msg || JSON.stringify(item)).join(', ')
        } else if (typeof detail === 'string') {
          errorMessage = detail
        } else {
          errorMessage = JSON.stringify(detail)
        }
      } else if (error.message) {
        errorMessage = error.message
      }
      
      alert(errorMessage)
    } finally {
      setSavingPayment(false)
    }
  }

  // Получаем цену услуги для подсказки
  const getServicePrice = (): number | null => {
    if (booking.service_id && services.length > 0) {
      const service = services.find(s => s.id === booking.service_id)
      return service ? service.price : null
    }
    return null
  }

  const servicePrice = getServicePrice()
  const hasPaymentChanges = 
    editingAmount !== (booking.amount ? booking.amount.toString() : '') ||
    editingPaymentMethod !== (booking.payment_method || '')

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Запись {booking.booking_number}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        {/* Кнопка сохранения изменений - вверху */}
        {canEdit && hasChanges && (
          <div style={{ 
            padding: '12px 20px', 
            background: '#fff3cd', 
            borderBottom: '1px solid #ffc107',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '12px'
          }}>
            <span style={{ fontSize: '14px', color: '#856404', fontWeight: '500' }}>
              ⚠️ Есть несохраненные изменения
            </span>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSaveChanges}
              disabled={saving}
              style={{ padding: '8px 16px', fontSize: '14px', whiteSpace: 'nowrap' }}
            >
              {saving ? 'Сохранение...' : '💾 Сохранить изменения'}
            </button>
          </div>
        )}
        
        <div className="modal-body">
          <div className="booking-details-grid">
            <div className="booking-detail-section">
              <h3 className="detail-section-title">👤 Информация о клиенте</h3>
              <div className="detail-item">
                <div className="detail-label">ФИО:</div>
                <div className="detail-value">{booking.client_name || `ID: ${booking.client_id}`}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Телефон:</div>
                <div className="detail-value">{booking.client_phone || '-'}</div>
              </div>
              {booking.client_telegram_id && (
                <div className="detail-item">
                  <div className="detail-label">Telegram ID:</div>
                  <div className="detail-value">{booking.client_telegram_id}</div>
                </div>
              )}
            </div>

            <div className="booking-detail-section">
              <h3 className="detail-section-title">📅 Дата и время</h3>
              <div className="detail-item">
                <div className="detail-label">Дата записи:</div>
                {canEdit ? (
                  <input
                    type="date"
                    value={editingDate}
                    onChange={(e) => setEditingDate(e.target.value)}
                    className="form-input"
                    style={{ width: '100%', maxWidth: '300px' }}
                  />
                ) : (
                  <div className="detail-value">{new Date(booking.date).toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    weekday: 'long'
                  })}</div>
                )}
              </div>
              <div className="detail-item">
                <div className="detail-label">Время начала:</div>
                {canEdit ? (
                  <input
                    type="time"
                    value={editingTime}
                    onChange={(e) => setEditingTime(e.target.value)}
                    className="form-input"
                    style={{ width: '100%', maxWidth: '300px' }}
                  />
                ) : (
                  <div className="detail-value">{booking.time}</div>
                )}
              </div>
              <div className="detail-item">
                <div className="detail-label">Время окончания:</div>
                <div className="detail-value">{booking.end_time || '-'}</div>
              </div>
              {booking.duration && (
                <div className="detail-item">
                  <div className="detail-label">Длительность:</div>
                  <div className="detail-value">{booking.duration} минут</div>
                </div>
              )}
            </div>

            <div className="booking-detail-section">
              <h3 className="detail-section-title">🛠️ Услуга и персонал</h3>
              <div className="detail-item">
                <div className="detail-label">Услуга:</div>
                <div className="detail-value detail-value-service">{booking.service_name || 'Не указана'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Мастер:</div>
                {canEdit && !loadingData ? (
                  <select
                    value={editingMaster || ''}
                    onChange={(e) => setEditingMaster(e.target.value ? parseInt(e.target.value) : null)}
                    className="form-input"
                    style={{ width: '100%', maxWidth: '300px' }}
                  >
                    <option value="">Не назначен</option>
                    {masters.map(master => (
                      <option key={master.id} value={master.id}>
                        {master.full_name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="detail-value">{booking.master_name || 'Не назначен'}</div>
                )}
              </div>
              <div className="detail-item">
                <div className="detail-label">Пост:</div>
                {canEdit && !loadingData ? (
                  <select
                    value={editingPost || ''}
                    onChange={(e) => setEditingPost(e.target.value ? parseInt(e.target.value) : null)}
                    className="form-input"
                    style={{ width: '100%', maxWidth: '300px' }}
                  >
                    <option value="">Не назначен</option>
                    {posts.map(post => (
                      <option key={post.id} value={post.id}>
                        Пост №{post.number} {post.name ? `(${post.name})` : ''}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="detail-value">{booking.post_number ? `№${booking.post_number}` : 'Не назначен'}</div>
                )}
              </div>
            </div>

            <div className="booking-detail-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 className="detail-section-title" style={{ margin: 0 }}>📊 Статус и оплата</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', margin: 0 }}>Изменить статус:</label>
                  <select
                    value={booking.status}
                    onChange={(e) => onStatusChange(booking.id, e.target.value)}
                    className="form-input"
                    style={{ minWidth: '180px' }}
                  >
                    {statusOptions.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Статус:</div>
                <div className="detail-value">
                  <span className={`status status-${booking.status}`}>
                    {statusLabels[booking.status] || booking.status}
                  </span>
                </div>
              </div>
              
              {/* Поля для ввода оплаты - показываются только при статусе "completed" */}
              {booking.status === 'completed' ? (
                <>
                  <div className="detail-item">
                    <div className="detail-label">Сумма оплаты:</div>
                    <div className="detail-value">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={editingAmount}
                        onChange={(e) => setEditingAmount(e.target.value)}
                        placeholder={servicePrice ? `Подсказка: ${servicePrice} ₽` : 'Введите сумму'}
                        className="form-input"
                        style={{ width: '100%', maxWidth: '200px' }}
                      />
                      {servicePrice && !editingAmount && (
                        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                          💡 Цена услуги: {servicePrice} ₽
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="detail-item">
                    <div className="detail-label">Способ оплаты:</div>
                    <div className="detail-value">
                      <select
                        value={editingPaymentMethod}
                        onChange={(e) => setEditingPaymentMethod(e.target.value)}
                        className="form-input"
                        style={{ width: '100%', maxWidth: '200px' }}
                      >
                        <option value="">Не указан</option>
                        <option value="cash">Наличные</option>
                        <option value="card">Карта</option>
                        <option value="qr">QR-код</option>
                      </select>
                    </div>
                  </div>
                  {hasPaymentChanges && (
                    <div className="detail-item">
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={handleSavePayment}
                        disabled={savingPayment}
                        style={{ marginTop: '8px' }}
                      >
                        {savingPayment ? 'Сохранение...' : '💾 Сохранить оплату'}
                      </button>
                    </div>
                  )}
                  {booking.amount && (
                    <div className="detail-item">
                      <div className="detail-label">Оплачено:</div>
                      <div className="detail-value">
                        <span className={booking.is_paid ? 'status status-completed' : 'status status-new'}>
                          {booking.is_paid ? 'Да' : 'Нет'}
                        </span>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {booking.amount && (
                    <div className="detail-item">
                      <div className="detail-label">Сумма:</div>
                      <div className="detail-value detail-value-amount">{booking.amount} ₽</div>
                    </div>
                  )}
                  <div className="detail-item">
                    <div className="detail-label">Оплачено:</div>
                    <div className="detail-value">
                      <span className={booking.is_paid ? 'status status-completed' : 'status status-new'}>
                        {booking.is_paid ? 'Да' : 'Нет'}
                      </span>
                    </div>
                  </div>
                  {booking.payment_method && (
                    <div className="detail-item">
                      <div className="detail-label">Способ оплаты:</div>
                      <div className="detail-value">{booking.payment_method}</div>
                    </div>
                  )}
                </>
              )}
            </div>

            {(booking.comment || booking.admin_comment) && (
              <div className="booking-detail-section booking-detail-section-full">
                <h3 className="detail-section-title">💬 Комментарии</h3>
                {booking.comment && (
                  <div className="detail-item">
                    <div className="detail-label">Комментарий клиента:</div>
                    <div className="detail-value detail-value-comment">{booking.comment}</div>
                  </div>
                )}
                {booking.admin_comment && (
                  <div className="detail-item">
                    <div className="detail-label">Комментарий администратора:</div>
                    <div className="detail-value detail-value-comment">{booking.admin_comment}</div>
                  </div>
                )}
              </div>
            )}
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

export default Bookings
