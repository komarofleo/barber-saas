import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { mastersApi } from '../api/masters'
import { Booking } from '../api/bookings'
import { formatMoney } from '../utils/money'
import './WorkOrders.css'

interface MasterWorkOrder {
  master_id: number
  master_name: string
  bookings: Booking[]
}

function WorkOrders() {
  const { user } = useAuth()
  const [workOrders, setWorkOrders] = useState<MasterWorkOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.is_admin) {
      loadAllWorkOrders()
    } else {
      setError('Только администраторы могут просматривать лист-наряды')
      setLoading(false)
    }
  }, [user, selectedDate])

  const loadAllWorkOrders = async () => {
    try {
      setLoading(true)
      setError(null)

      console.log('🔍 Загрузка лист-нарядов для даты:', selectedDate)
      const data = await mastersApi.getAllWorkOrders(selectedDate)
      console.log('📊 Полученные данные:', data)
      console.log('📊 Количество мастеров:', data.masters?.length || 0)
      
      // Проверяем структуру данных
      if (data && data.masters && Array.isArray(data.masters)) {
        data.masters.forEach((master: any, index: number) => {
          console.log(`👨‍🔧 Мастер ${index + 1}: ${master.master_name}, записей: ${master.bookings?.length || 0}`)
        })
        setWorkOrders(data.masters)
      } else {
        console.error('❌ Неверная структура данных:', data)
        setError('Неверная структура данных от сервера')
      }
    } catch (error: any) {
      console.error('❌ Ошибка загрузки лист-нарядов:', error)
      console.error('Статус ошибки:', error.response?.status)
      console.error('Данные ошибки:', error.response?.data)
      if (error.response?.status === 403) {
        setError('У вас нет доступа к просмотру лист-нарядов')
      } else if (error.response?.status === 404) {
        setError('API endpoint не найден')
      } else {
        setError('Не удалось загрузить лист-наряды')
      }
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (time: string) => {
    return new Date(`2000-01-01T${time}`).toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru-RU', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
  }

  const getStatusLabel = (status: string) => {
    const statusMap: { [key: string]: { label: string; className: string } } = {
      'new': { label: 'Новая', className: 'status-new' },
      'confirmed': { label: 'Подтверждена', className: 'status-confirmed' },
      'completed': { label: 'Завершена', className: 'status-completed' },
      'cancelled': { label: 'Отменена', className: 'status-cancelled' },
    }
    return statusMap[status] || { label: status, className: 'status-default' }
  }

  if (loading) {
    return (
      <div className="work-orders-container">
        <div className="work-orders-header">
          <h1>📋 Лист-наряды</h1>
        </div>
        <div className="loading">Загрузка...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="work-orders-container">
        <div className="work-orders-header">
          <h1>📋 Лист-наряды</h1>
        </div>
        <div className="error-message">{error}</div>
      </div>
    )
  }

  if (!user?.is_admin) {
    return (
      <div className="work-orders-container">
        <div className="work-orders-header">
          <h1>📋 Лист-наряды</h1>
        </div>
        <div className="error-message">
          Только администраторы могут просматривать лист-наряды
        </div>
      </div>
    )
  }

  const totalBookings = workOrders.reduce((sum, master) => sum + master.bookings.length, 0)

  return (
    <div className="work-orders-container">
      <div className="work-orders-header">
        <h1>📋 Лист-наряды</h1>
        <div className="work-orders-summary">
          <span className="summary-text">
            Всего записей: <strong>{totalBookings}</strong> | Мастеров: <strong>{workOrders.length}</strong>
          </span>
        </div>
      </div>

      <div className="work-orders-controls">
        <label htmlFor="date-select">Дата:</label>
        <input
          id="date-select"
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="date-input"
        />
        <button onClick={loadAllWorkOrders} className="refresh-btn">
          🔄 Обновить
        </button>
      </div>

      <div className="work-orders-content">
        <div className="work-orders-date">
          {formatDate(selectedDate)}
        </div>

        {workOrders.length === 0 ? (
          <div className="no-bookings">
            ✅ На {formatDate(selectedDate)} записей нет
          </div>
        ) : (
          <div className="masters-work-orders">
            {workOrders.map((masterWorkOrder) => (
              <div key={masterWorkOrder.master_id} className="master-section">
                <div className="master-section-header">
                  <h2 className="master-name">👨‍🔧 {masterWorkOrder.master_name}</h2>
                  <span className="master-bookings-count">
                    Записей: {masterWorkOrder.bookings.length}
                  </span>
                </div>

                {masterWorkOrder.bookings.length === 0 ? (
                  <div className="no-bookings-master">
                    На этот день записей нет
                  </div>
                ) : (
                  <div className="bookings-list">
                    {masterWorkOrder.bookings.map((booking, index) => {
                      const statusInfo = getStatusLabel(booking.status)
                      return (
                        <div key={booking.id} className="booking-card">
                          <div className="booking-header">
                            <span className="booking-number">#{index + 1}</span>
                            <span className={`booking-status ${statusInfo.className}`}>
                              {statusInfo.label}
                            </span>
                          </div>
                          
                          <div className="booking-time">
                            ⏰ {formatTime(booking.time)} - {formatTime(booking.end_time)}
                          </div>

                          <div className="booking-details">
                            {booking.service_name && (
                              <div className="booking-detail">
                                <span className="detail-label">🛠️ Услуга:</span>
                                <span className="detail-value">{booking.service_name}</span>
                              </div>
                            )}

                            {booking.client_name && (
                              <div className="booking-detail">
                                <span className="detail-label">👤 Клиент:</span>
                                <span className="detail-value">{booking.client_name}</span>
                              </div>
                            )}

                            {booking.client_phone && (
                              <div className="booking-detail">
                                <span className="detail-label">📞 Телефон:</span>
                                <span className="detail-value">{booking.client_phone}</span>
                              </div>
                            )}

                            {booking.post_number && (
                              <div className="booking-detail">
                                <span className="detail-label">🏢 Рабочее место:</span>
                                <span className="detail-value">#{booking.post_number}</span>
                              </div>
                            )}

                            {booking.comment && (
                              <div className="booking-detail">
                                <span className="detail-label">💬 Комментарий:</span>
                                <span className="detail-value">{booking.comment}</span>
                              </div>
                            )}

                            {booking.amount && (
                              <div className="booking-detail">
                                <span className="detail-label">💰 Сумма:</span>
                                <span className="detail-value">{formatMoney(booking.amount)}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default WorkOrders
