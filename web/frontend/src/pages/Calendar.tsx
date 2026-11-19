import { useState, useEffect } from 'react'
import { bookingsApi, Booking, BookingCreateRequest } from '../api/bookings'
import { clientsApi, Client, ClientCreateRequest } from '../api/clients'
import { servicesApi, Service } from '../api/services'
import { mastersApi, Master } from '../api/masters'
import { postsApi, Post } from '../api/posts'
import { SuccessNotification } from '../components/SuccessNotification'
import { formatMoney } from '../utils/money'
import './Calendar.css'

type ViewMode = 'month' | 'week' | 'day'

function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [viewMode, setViewMode] = useState<ViewMode>('month')
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [showViewModal, setShowViewModal] = useState(false)
  const [viewingBooking, setViewingBooking] = useState<Booking | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createModalDate, setCreateModalDate] = useState<string>('')
  const [createModalTime, setCreateModalTime] = useState<string>('')
  const [showSuccessNotification, setShowSuccessNotification] = useState(false)
  
  // Состояния для drag and drop
  const [draggedBooking, setDraggedBooking] = useState<Booking | null>(null)
  const [dragStartTime, setDragStartTime] = useState<number>(0)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    loadBookings()
  }, [currentDate, viewMode])

  const loadBookings = async () => {
    try {
      setLoading(true)
      const startDate = getStartDate()
      const endDate = getEndDate()
      
      const data = await bookingsApi.getBookings(1, 1000, {
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
      })
      setBookings(data.items)
    } catch (error: any) {
      console.error('Ошибка загрузки записей:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const getStartDate = (): Date => {
    const date = new Date(currentDate)
    if (viewMode === 'month') {
      date.setDate(1)
      date.setHours(0, 0, 0, 0)
    } else if (viewMode === 'week') {
      const day = date.getDay()
      const diff = date.getDate() - day + (day === 0 ? -6 : 1) // Понедельник
      date.setDate(diff)
      date.setHours(0, 0, 0, 0)
    } else {
      date.setHours(0, 0, 0, 0)
    }
    return date
  }

  const getEndDate = (): Date => {
    const date = new Date(currentDate)
    if (viewMode === 'month') {
      date.setMonth(date.getMonth() + 1)
      date.setDate(0) // Последний день месяца
      date.setHours(23, 59, 59, 999)
    } else if (viewMode === 'week') {
      const day = date.getDay()
      const diff = date.getDate() - day + (day === 0 ? -6 : 1) + 6 // Воскресенье
      date.setDate(diff)
      date.setHours(23, 59, 59, 999)
    } else {
      date.setHours(23, 59, 59, 999)
    }
    return date
  }

  const navigateDate = (direction: 'prev' | 'next') => {
    const newDate = new Date(currentDate)
    if (viewMode === 'month') {
      newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1))
    } else if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() + (direction === 'next' ? 7 : -7))
    } else {
      newDate.setDate(newDate.getDate() + (direction === 'next' ? 1 : -1))
    }
    setCurrentDate(newDate)
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  const getBookingsForDate = (date: Date): Booking[] => {
    // Форматируем дату в формате YYYY-MM-DD
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    return bookings.filter(b => {
      // b.service_date может быть строкой или объектом Date
      const bookingDate = typeof b.service_date === 'string' ? b.service_date : b.service_date.split('T')[0]
      return bookingDate === dateStr
    })
  }

  const getBookingsForTime = (date: Date, hour: number): Booking[] => {
    // Форматируем дату в формате YYYY-MM-DD
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    return bookings.filter(b => {
      // b.service_date может быть строкой или объектом Date
      const bookingDate = typeof b.service_date === 'string' ? b.service_date : b.service_date.split('T')[0]
      if (bookingDate !== dateStr) return false
      const timeStr = typeof b.time === 'string' ? b.time : b.time.toString()
      const timeHour = parseInt(timeStr.split(':')[0])
      return timeHour === hour
    })
  }

  const handleBookingClick = async (booking: Booking) => {
    try {
      const fullBooking = await bookingsApi.getBooking(booking.id)
      setViewingBooking(fullBooking)
      setShowViewModal(true)
    } catch (error: any) {
      console.error('Ошибка загрузки записи:', error)
      alert('Не удалось загрузить запись')
    }
  }

  // Обработчик начала перетаскивания
  const handleDragStart = (e: React.DragEvent, booking: Booking) => {
    setDraggedBooking(booking)
    setDragStartTime(Date.now())
    setIsDragging(false)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', booking.id.toString())
    e.dataTransfer.setData('application/json', JSON.stringify({ bookingId: booking.id }))
    
    // Создаем полупрозрачный элемент для визуальной обратной связи
    try {
      const dragImage = e.currentTarget.cloneNode(true) as HTMLElement
      dragImage.style.opacity = '0.5'
      document.body.appendChild(dragImage)
      dragImage.style.position = 'absolute'
      dragImage.style.top = '-1000px'
      e.dataTransfer.setDragImage(dragImage, 0, 0)
      setTimeout(() => {
        if (document.body.contains(dragImage)) {
          document.body.removeChild(dragImage)
        }
      }, 0)
    } catch (err) {
      // Игнорируем ошибки при создании drag image
      console.warn('Ошибка создания drag image:', err)
    }
  }

  // Обработчик для определения, что началось перетаскивание
  const handleMouseDown = (e: React.MouseEvent, booking: Booking) => {
    const startX = e.clientX
    const startY = e.clientY
    const startTime = Date.now()
    let moved = false
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = Math.abs(moveEvent.clientX - startX)
      const deltaY = Math.abs(moveEvent.clientY - startY)
      if (deltaX > 5 || deltaY > 5) {
        moved = true
        setIsDragging(true)
      }
    }
    
    const handleMouseUp = () => {
      const endTime = Date.now()
      const wasDrag = moved || (endTime - startTime > 200)
      
      if (!wasDrag) {
        // Это был клик, открываем модальное окно
        setTimeout(() => {
          handleBookingClick(booking)
        }, 50)
      }
      
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      setTimeout(() => {
        setIsDragging(false)
        setDragStartTime(0)
      }, 100)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  // Обработчик для разрешения drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  // Обработчик drop для недельного вида
  const handleDropWeek = (e: React.DragEvent, day: Date, hour: number) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!draggedBooking) return
    
    const year = day.getFullYear()
    const month = String(day.getMonth() + 1).padStart(2, '0')
    const dayNum = String(day.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${dayNum}`
    // Формат времени для FastAPI: HH:MM:SS
    const timeStr = `${String(hour).padStart(2, '0')}:00:00`
    
    handleBookingMove(draggedBooking, dateStr, timeStr)
    setDraggedBooking(null)
  }

  // Обработчик drop для дневного вида
  const handleDropDay = (e: React.DragEvent, hour: number) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!draggedBooking) return
    
    const year = currentDate.getFullYear()
    const month = String(currentDate.getMonth() + 1).padStart(2, '0')
    const day = String(currentDate.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    // Формат времени для FastAPI: HH:MM:SS
    const timeStr = `${String(hour).padStart(2, '0')}:00:00`
    
    handleBookingMove(draggedBooking, dateStr, timeStr)
    setDraggedBooking(null)
  }

  // Функция для перемещения записи
  const handleBookingMove = async (booking: Booking, newDate: string, newTime: string) => {
    try {
      // newTime уже в формате HH:MM:SS из handleDropWeek/handleDropDay
      // Проверяем формат и приводим к нужному виду
      let timeStr = newTime
      if (timeStr.split(':').length === 2) {
        // Если формат HH:MM, добавляем секунды
        timeStr = `${timeStr}:00`
      }
      
      console.log('Перемещение записи:', { bookingId: booking.id, service_date: newDate, time: timeStr })
      console.log('Типы данных:', { dateType: typeof newDate, timeType: typeof timeStr })
      
      // Убеждаемся, что дата в правильном формате YYYY-MM-DD
      const dateParts = newDate.split('-')
      if (dateParts.length !== 3) {
        throw new Error('Неверный формат даты')
      }
      
      // Создаем объект с данными для обновления
      // При перемещении всегда обновляем и дату, и время
      const updateData: any = {}
      
      // Всегда добавляем дату и время при перемещении
      // (при drag and drop мы перемещаем запись на новое место)
      updateData.service_date = newDate
      updateData.time = timeStr
      
      console.log('Данные для отправки:', updateData)
      console.log('Типы данных:', { 
        dateType: typeof updateData.service_date, 
        timeType: typeof updateData.time,
        dateValue: updateData.service_date,
        timeValue: updateData.time
      })
      
      // Логируем детали ошибки перед отправкой
      console.log('Отправляем PATCH запрос на:', `/api/bookings/${booking.id}`)
      console.log('Тело запроса:', JSON.stringify(updateData))
      
      const response = await bookingsApi.updateBooking(booking.id, updateData)
      console.log('Успешный ответ:', response)
      // Обновляем список записей
      await loadBookings()
    } catch (error: any) {
      console.error('Ошибка перемещения записи:', error)
      console.error('Error response:', error.response)
      console.error('Error response data:', error.response?.data)
      console.error('Error response data detail:', error.response?.data?.detail)
      if (Array.isArray(error.response?.data?.detail)) {
        console.error('Детали ошибок валидации (полный объект):', JSON.stringify(error.response.data.detail, null, 2))
        error.response.data.detail.forEach((err: any, index: number) => {
          console.error(`Ошибка валидации ${index + 1}:`, {
            loc: err.loc,
            msg: err.msg,
            type: err.type,
            input: err.input,
            ctx: err.ctx
          })
        })
      }
      
      let errorMessage = 'Не удалось переместить запись'
      
      try {
        if (error.response?.data) {
          const data = error.response.data
          
          // Если это строка
          if (typeof data === 'string') {
            errorMessage = data
          }
          // Если это объект с detail
          else if (data.detail) {
            if (typeof data.detail === 'string') {
              errorMessage = data.detail
            } else if (Array.isArray(data.detail)) {
              // Если detail - массив (ошибки валидации FastAPI)
              errorMessage = data.detail.map((item: any) => {
                if (typeof item === 'string') return item
                if (item.msg) {
                  const loc = item.loc ? item.loc.join('.') : ''
                  return loc ? `${loc}: ${item.msg}` : item.msg
                }
                if (item.message) return item.message
                // Если это объект, пытаемся извлечь полезную информацию
                if (typeof item === 'object') {
                  const parts: string[] = []
                  if (item.loc) parts.push(item.loc.join('.'))
                  if (item.msg) parts.push(item.msg)
                  if (item.type) parts.push(`(${item.type})`)
                  return parts.length > 0 ? parts.join(' ') : JSON.stringify(item)
                }
                return String(item)
              }).join('; ')
            } else {
              errorMessage = String(data.detail)
            }
          }
          // Если это объект с message
          else if (data.message) {
            errorMessage = typeof data.message === 'string' ? data.message : String(data.message)
          }
          // Если это массив
          else if (Array.isArray(data)) {
            errorMessage = data.map((item: any) => {
              if (typeof item === 'string') return item
              if (item.msg) return item.msg
              if (item.message) return item.message
              return String(item)
            }).join(', ')
          }
          // Попытка преобразовать в строку
          else {
            errorMessage = String(data)
          }
        } else if (error.message) {
          errorMessage = error.message
        }
      } catch (parseError) {
        console.error('Ошибка парсинга ошибки:', parseError)
        errorMessage = 'Не удалось переместить запись. Проверьте консоль для деталей.'
      }
      
      alert(`Не удалось переместить запись: ${errorMessage}`)
    }
  }

  const getBookingTooltip = (booking: Booking): string => {
    const parts: string[] = []
    if (booking.client_name) parts.push(`👤 ${booking.client_name}`)
    if (booking.service_name) parts.push(`🛠️ ${booking.service_name}`)
    parts.push(`👨‍🔧 Мастер: ${booking.master_name || '-'}`)
    parts.push(`⏰ ${booking.time}${booking.end_time ? ` - ${booking.end_time}` : ''}`)
    return parts.join('\n')
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'new':
        return '#dc3545' // Красный
      case 'confirmed':
        return '#28a745' // Зеленый
      case 'completed':
        return '#17a2b8' // Синий
      case 'cancelled':
        return '#6c757d' // Серый
      default:
        return '#4a9eff' // Синий по умолчанию
    }
  }

  const handleTimeSlotClick = (date: Date, hour: number) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    const timeStr = `${String(hour).padStart(2, '0')}:00`
    
    setCreateModalDate(dateStr)
    setCreateModalTime(timeStr)
    setShowCreateModal(true)
  }

  const renderMonthView = () => {
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const startDate = new Date(firstDay)
    startDate.setDate(startDate.getDate() - startDate.getDay() + (startDate.getDay() === 0 ? -6 : 1))
    
    const days: Date[] = []
    const current = new Date(startDate)
    for (let i = 0; i < 42; i++) {
      days.push(new Date(current))
      current.setDate(current.getDate() + 1)
    }

    const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                       'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

    return (
      <div className="calendar-month-view">
        <div className="calendar-header-month">
          <h2>{monthNames[month]} {year}</h2>
        </div>
        <div className="calendar-grid">
          {dayNames.map(day => (
            <div key={day} className="calendar-day-header">{day}</div>
          ))}
          {days.map((day, idx) => {
            const isCurrentMonth = day.getMonth() === month
            const isToday = day.toDateString() === new Date().toDateString()
            const dayBookings = getBookingsForDate(day)
            
            return (
              <div
                key={idx}
                className={`calendar-day ${!isCurrentMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}`}
                onClick={(e) => {
                  // Клик на день открывает форму создания записи
                  const target = e.target as HTMLElement
                  // Проверяем, что клик не на элементе записи или кнопке
                  const isBookingItem = target.closest('.calendar-booking-item')
                  const isBookingMore = target.closest('.calendar-booking-more')
                  
                  if (!isBookingItem && !isBookingMore) {
                    const year = day.getFullYear()
                    const month = String(day.getMonth() + 1).padStart(2, '0')
                    const dayNum = String(day.getDate()).padStart(2, '0')
                    const dateStr = `${year}-${month}-${dayNum}`
                    console.log('Открытие модального окна создания записи для даты:', dateStr)
                    setCreateModalDate(dateStr)
                    setCreateModalTime('')
                    setShowCreateModal(true)
                  }
                }}
                style={{ cursor: 'pointer' }}
              >
                <div className="calendar-day-number">{day.getDate()}</div>
                {dayBookings.length > 0 && (
                  <div className="calendar-day-bookings">
                    {dayBookings.slice(0, 3).map(booking => (
                      <div 
                        key={booking.id} 
                        className="calendar-booking-item" 
                        style={{ backgroundColor: getStatusColor(booking.status) }}
                        title={getBookingTooltip(booking)}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleBookingClick(booking)
                        }}
                      >
                        {booking.time} {booking.client_name?.split(' ')[0] || ''}
                      </div>
                    ))}
                    {dayBookings.length > 3 && (
                      <div 
                        className="calendar-booking-more"
                        onClick={(e) => {
                          e.stopPropagation()
                        }}
                      >
                        +{dayBookings.length - 3}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const renderWeekView = () => {
    const startDate = getStartDate()
    const days: Date[] = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(startDate)
      date.setDate(startDate.getDate() + i)
      days.push(date)
    }

    const dayNames = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    const hours = Array.from({ length: 12 }, (_, i) => i + 9) // 9:00 - 20:00

    return (
      <div className="calendar-week-view">
        <div className="calendar-header-week">
          <div className="calendar-time-column"></div>
          {days.map((day, idx) => (
            <div key={idx} className="calendar-week-day-header">
              <div className="week-day-name">{dayNames[day.getDay() === 0 ? 6 : day.getDay() - 1]}</div>
              <div className={`week-day-number ${day.toDateString() === new Date().toDateString() ? 'today' : ''}`}>
                {day.getDate()}
              </div>
            </div>
          ))}
        </div>
        <div className="calendar-week-grid">
          <div className="calendar-time-column">
            {hours.map(hour => (
              <div key={hour} className="calendar-hour-cell">{hour}:00</div>
            ))}
          </div>
          {days.map((day, dayIdx) => (
            <div key={dayIdx} className="calendar-week-day-column">
              {hours.map(hour => {
                const bookings = getBookingsForTime(day, hour)
                return (
                  <div 
                    key={hour} 
                    className="calendar-hour-cell"
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleDragOver(e)
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleDropWeek(e, day, hour)
                    }}
                    onClick={(e) => {
                      if (e.target === e.currentTarget || bookings.length === 0) {
                        handleTimeSlotClick(day, hour)
                      }
                    }}
                    style={{ cursor: bookings.length === 0 ? 'pointer' : 'default' }}
                  >
                    {bookings.map(booking => (
                      <div 
                        key={booking.id} 
                        className="calendar-week-booking draggable-booking" 
                        draggable="true"
                        style={{ backgroundColor: getStatusColor(booking.status) }}
                        title={getBookingTooltip(booking)}
                        onDragStart={(e) => {
                          e.stopPropagation()
                          handleDragStart(e, booking)
                        }}
                        onMouseDown={(e) => handleMouseDown(e, booking)}
                        onClick={(e) => {
                          // Предотвращаем открытие модального окна при drag
                          e.stopPropagation()
                          // Клик обрабатывается в handleMouseDown
                        }}
                      >
                        {booking.time} {booking.client_name?.split(' ')[0] || ''}
                      </div>
                    ))}
                    {bookings.length === 0 && (
                      <div className="calendar-empty-slot" title="Кликните для создания записи">
                        +
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    )
  }

  const renderDayView = () => {
    const hours = Array.from({ length: 12 }, (_, i) => i + 9) // 9:00 - 20:00
    const dayBookings = getBookingsForDate(currentDate)
    const dayNames = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
    const monthNames = ['Января', 'Февраля', 'Марта', 'Апреля', 'Мая', 'Июня', 
                       'Июля', 'Августа', 'Сентября', 'Октября', 'Ноября', 'Декабря']

    return (
      <div className="calendar-day-view">
        <div className="calendar-header-day">
          <h2>
            {dayNames[currentDate.getDay()]}, {currentDate.getDate()} {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
          </h2>
        </div>
        <div className="calendar-day-grid">
          {hours.map(hour => {
            const hourBookings = dayBookings.filter(b => {
              const timeHour = parseInt(b.time.split(':')[0])
              return timeHour === hour
            })
            
            return (
              <div key={hour} className="calendar-day-hour">
                <div className="calendar-hour-label">{hour}:00</div>
                <div 
                  className="calendar-hour-content"
                  onDragOver={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleDragOver(e)
                  }}
                  onDrop={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleDropDay(e, hour)
                  }}
                  onClick={(e) => {
                    if (e.target === e.currentTarget || hourBookings.length === 0) {
                      handleTimeSlotClick(currentDate, hour)
                    }
                  }}
                  style={{ cursor: hourBookings.length === 0 ? 'pointer' : 'default', minHeight: hourBookings.length === 0 ? '60px' : 'auto' }}
                >
                  {hourBookings.map(booking => (
                    <div 
                      key={booking.id} 
                      className="calendar-day-booking draggable-booking"
                      draggable={true}
                      style={{ borderLeftColor: getStatusColor(booking.status) }}
                      title={getBookingTooltip(booking)}
                      onDragStart={(e) => handleDragStart(e, booking)}
                      onMouseDown={(e) => handleMouseDown(e, booking)}
                      onClick={(e) => {
                        // Предотвращаем открытие модального окна при drag
                        e.stopPropagation()
                        // Клик обрабатывается в handleMouseDown
                      }}
                    >
                      <div className="booking-time">{booking.time}</div>
                      <div className="booking-info">
                        <div className="booking-client">{booking.client_name || `ID: ${booking.client_id}`}</div>
                        {booking.service_name && <div className="booking-service">{booking.service_name}</div>}
                        {booking.master_name && <div className="booking-master">Мастер: {booking.master_name}</div>}
                      </div>
                    </div>
                  ))}
                  {hourBookings.length === 0 && (
                    <div className="calendar-empty-slot" title="Кликните для создания записи">
                      + Создать запись
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="calendar-page">
      {showSuccessNotification && (
        <SuccessNotification
          message="✅ Сообщение отправлено клиенту в Telegram"
          onClose={() => {
            console.log('📌 Закрываем уведомление')
            setShowSuccessNotification(false)
          }}
          duration={5000}
        />
      )}
      <div className="page-header-simple">
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <h1>Календарь</h1>
          <div className="calendar-legend">
            <span className="legend-title">Статусы:</span>
            <div className="legend-items">
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#dc3545' }}></span>
                <span className="legend-label">Новая</span>
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#28a745' }}></span>
                <span className="legend-label">Подтверждена</span>
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#17a2b8' }}></span>
                <span className="legend-label">Завершена</span>
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#6c757d' }}></span>
                <span className="legend-label">Отменена</span>
              </div>
            </div>
          </div>
        </div>
        <div className="calendar-controls">
          <div className="view-mode-buttons">
            <button
              className={`view-btn ${viewMode === 'month' ? 'active' : ''}`}
              onClick={() => setViewMode('month')}
            >
              Месяц
            </button>
            <button
              className={`view-btn ${viewMode === 'week' ? 'active' : ''}`}
              onClick={() => setViewMode('week')}
            >
              Неделя
            </button>
            <button
              className={`view-btn ${viewMode === 'day' ? 'active' : ''}`}
              onClick={() => setViewMode('day')}
            >
              День
            </button>
          </div>
          <div className="date-navigation">
            <button className="nav-btn" onClick={() => navigateDate('prev')}>‹</button>
            <button className="nav-btn today-btn" onClick={goToToday}>Сегодня</button>
            <button className="nav-btn" onClick={() => navigateDate('next')}>›</button>
          </div>
        </div>
      </div>

      <div className="calendar-container">
        {loading ? (
          <div className="loading">Загрузка...</div>
        ) : (
          <>
            {viewMode === 'month' && renderMonthView()}
            {viewMode === 'week' && renderWeekView()}
            {viewMode === 'day' && renderDayView()}
          </>
        )}
      </div>

      {showViewModal && viewingBooking && (
        <ViewBookingModal
          booking={viewingBooking}
          onClose={() => {
            setShowViewModal(false)
            setViewingBooking(null)
          }}
          onStatusChange={async (bookingId: number, status: string) => {
            try {
              const updatedBooking = await bookingsApi.updateBooking(bookingId, { status })
              console.log('✅ Статус обновлен, получен ответ:', updatedBooking)
              
              if (viewingBooking && viewingBooking.id === bookingId) {
                setViewingBooking({ ...viewingBooking, ...updatedBooking })
              }
              
              // Показываем уведомление при смене статуса, если уведомление было отправлено
              const notificationSent = updatedBooking.notification_sent === true
              const hasTelegramId = updatedBooking.client_telegram_id && updatedBooking.client_telegram_id > 0
              
              console.log('📋 Проверка показа уведомления:', { 
                notification_sent: updatedBooking.notification_sent, 
                client_telegram_id: updatedBooking.client_telegram_id,
                hasTelegramId,
                notificationSent,
                status
              })
              
              // Показываем уведомление, если оно было отправлено успешно
              if (notificationSent) {
                console.log('✅ Показываем уведомление об успешной отправке')
                setShowSuccessNotification(true)
                // Автоматически скрываем через 5 секунд
                setTimeout(() => {
                  setShowSuccessNotification(false)
                }, 5000)
              } else if (hasTelegramId) {
                // Если есть telegram_id, но уведомление не отправилось - показываем предупреждение
                console.log('⚠️ У клиента есть telegram_id, но уведомление не отправлено')
              } else {
                console.log('ℹ️ У клиента нет telegram_id - уведомление не требуется')
              }
              
              loadBookings()
            } catch (error: any) {
              console.error('Ошибка изменения статуса:', error)
              alert('Не удалось изменить статус')
            }
          }}
          onUpdate={loadBookings}
        />
      )}

      {showCreateModal && (
        <CreateBookingModal
          initialDate={createModalDate}
          initialTime={createModalTime}
          onClose={() => {
            setShowCreateModal(false)
            setCreateModalDate('')
            setCreateModalTime('')
          }}
          onSuccess={() => {
            setShowCreateModal(false)
            setCreateModalDate('')
            setCreateModalTime('')
            loadBookings()
          }}
        />
      )}
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Запись {booking.booking_number}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
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
                <div className="detail-value">{new Date(booking.service_date).toLocaleDateString('ru-RU', {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                  weekday: 'long'
                })}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Время начала:</div>
                <div className="detail-value">{booking.time}</div>
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
                <div className="detail-value">{booking.master_name || 'Не назначен'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Пост:</div>
                <div className="detail-value">{booking.post_number ? `№${booking.post_number}` : 'Не назначен'}</div>
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
              {booking.amount && (
                <div className="detail-item">
                  <div className="detail-label">Сумма:</div>
                  <div className="detail-value detail-value-amount">{formatMoney(booking.amount)}</div>
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

interface CreateBookingModalProps {
  onClose: () => void
  onSuccess: () => void
  initialDate?: string
  initialTime?: string
}

function CreateBookingModal({ onClose, onSuccess, initialDate, initialTime }: CreateBookingModalProps) {
  const [clients, setClients] = useState<Client[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [masters, setMasters] = useState<Master[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [availableSlots, setAvailableSlots] = useState<string[]>([])
  const [occupiedPostIds, setOccupiedPostIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)
  const [dataLoading, setDataLoading] = useState(true)
  const [showCreateClientModal, setShowCreateClientModal] = useState(false)
  
  const [formData, setFormData] = useState<BookingCreateRequest>({
    client_id: 0,
    service_id: undefined,
    master_id: undefined,
    post_id: undefined,
    service_date: initialDate || new Date().toISOString().split('T')[0],
    time: initialTime || '',
    duration: 30,
    status: 'new',
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (formData.service_date) {
      loadAvailableSlots()
      // Если есть начальное время и оно еще не установлено, устанавливаем его
      if (initialTime && !formData.time) {
        setFormData(prev => ({ ...prev, time: initialTime }))
      }
    }
  }, [formData.service_date, formData.service_id, formData.master_id, formData.post_id])

  // Обновляем длительность при выборе услуги
  useEffect(() => {
    if (formData.service_id) {
      const selectedService = services.find(s => s.id === formData.service_id)
      if (selectedService && formData.duration !== selectedService.duration) {
        setFormData(prev => ({ ...prev, duration: selectedService.duration }))
      }
    }
  }, [formData.service_id, services])

  // Загрузка занятых постов при изменении даты, времени и длительности
  useEffect(() => {
    if (formData.service_date && formData.time && formData.duration) {
      loadOccupiedPosts()
    } else {
      setOccupiedPostIds(new Set())
    }
  }, [formData.service_date, formData.time, formData.duration])

  const loadData = async () => {
    try {
      setDataLoading(true)
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
      alert('Ошибка загрузки данных. Проверьте консоль для деталей.')
    } finally {
      setDataLoading(false)
    }
  }

  const handleClientCreated = async (newClient: Client) => {
    // Обновляем список клиентов
    await loadData()
    // Выбираем созданного клиента
    setFormData(prev => ({ ...prev, client_id: newClient.id }))
    setShowCreateClientModal(false)
  }

  const loadAvailableSlots = async () => {
    try {
      const slots = await bookingsApi.getAvailableSlots(
        formData.service_date,
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
    if (!formData.service_date || !formData.time || !formData.duration) {
      setOccupiedPostIds(new Set())
      return
    }

    try {
      // Получаем все записи на выбранную дату
      const bookingsData = await bookingsApi.getBookings(1, 1000, {
        start_date: formData.service_date,
        end_date: formData.service_date
      })

      // Вычисляем время начала и конца новой записи
      const [hours, minutes] = formData.time.split(':').map(Number)
      const startTime = new Date(`${formData.service_date}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`)
      const endTime = new Date(startTime.getTime() + (formData.duration || 30) * 60 * 1000)

      // Находим занятые посты
      const occupied = new Set<number>()
      bookingsData.items.forEach(booking => {
        // Учитываем только активные статусы (new/confirmed). Остальные не блокируют посты.
        if (booking.status !== 'new' && booking.status !== 'confirmed') {
          return
        }

        // Проверяем пересечение времени
        const bookingStart = new Date(`${booking.service_date}T${booking.time}:00`)
        const bookingEnd = new Date(`${booking.service_date}T${booking.end_time}:00`)

        // Если времена пересекаются
        if (!(endTime <= bookingStart || startTime >= bookingEnd)) {
          if (booking.post_id) {
            occupied.add(booking.post_id)
          }
        }
      })

      setOccupiedPostIds(occupied)
      console.log('🚫 Занятые посты на', formData.service_date, formData.time, ':', Array.from(occupied))
    } catch (error) {
      console.error('Ошибка загрузки занятых постов:', error)
      setOccupiedPostIds(new Set())
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.client_id || !formData.service_date || !formData.time) {
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Создать новую запись</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        {dataLoading ? (
          <div className="modal-body">
            <div className="loading">Загрузка данных...</div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="modal-body">
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <label>Клиент *</label>
                <button
                  type="button"
                  onClick={() => setShowCreateClientModal(true)}
                  className="btn-sm btn-primary"
                  style={{ padding: '4px 12px', fontSize: '12px' }}
                >
                  + Новый клиент
                </button>
              </div>
              <select
                value={formData.client_id || ''}
                onChange={(e) => setFormData({ ...formData, client_id: parseInt(e.target.value) })}
                required
                className="form-input"
                disabled={dataLoading || clients.length === 0}
              >
                <option value="">Выберите клиента</option>
                {clients.map(client => (
                  <option key={client.id} value={client.id}>
                    {client.full_name} {client.phone ? `(${client.phone})` : ''}
                  </option>
                ))}
              </select>
              {clients.length === 0 && !dataLoading && (
                <small className="text-muted">Нет доступных клиентов</small>
              )}
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
                disabled={dataLoading || services.length === 0}
              >
                <option value="">Не выбрана</option>
                {services.map(service => (
                  <option key={service.id} value={service.id}>
                    {service.name} ({service.duration} мин, {formatMoney(service.price)})
                  </option>
                ))}
              </select>
              {services.length === 0 && !dataLoading && (
                <small className="text-muted">Нет доступных услуг</small>
              )}
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
                disabled={dataLoading || masters.length === 0}
              >
                <option value="">Не выбран</option>
                {masters.map(master => (
                  <option key={master.id} value={master.id}>
                    {master.full_name}
                  </option>
                ))}
              </select>
              {masters.length === 0 && !dataLoading && (
                <small className="text-muted">Нет доступных мастеров</small>
              )}
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
                disabled={dataLoading || posts.length === 0}
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
              {posts.length === 0 && !dataLoading && (
                <small className="text-muted">Нет доступных постов</small>
              )}
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
                value={formData.service_date}
                onChange={(e) => setFormData({ ...formData, service_date: e.target.value })}
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
                disabled={!formData.service_date || availableSlots.length === 0}
              >
                <option value="">Выберите время</option>
                {availableSlots.map(slot => (
                  <option key={slot} value={slot}>
                    {slot}
                  </option>
                ))}
              </select>
              {formData.service_date && availableSlots.length === 0 && (
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
              <button type="submit" className="btn-primary" disabled={loading || dataLoading}>
                {loading ? 'Создание...' : 'Создать'}
              </button>
            </div>
          </form>
        )}
        {showCreateClientModal && (
          <CreateClientQuickModal
            onClose={() => setShowCreateClientModal(false)}
            onSuccess={handleClientCreated}
          />
        )}
      </div>
    </div>
  )
}

interface CreateClientQuickModalProps {
  onClose: () => void
  onSuccess: (client: Client) => void
}

function CreateClientQuickModal({ onClose, onSuccess }: CreateClientQuickModalProps) {
  const [formData, setFormData] = useState<ClientCreateRequest>({
    full_name: '',
    phone: '',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.full_name.trim() || !formData.phone.trim()) {
      alert('Заполните ФИО и телефон')
      return
    }

    try {
      setLoading(true)
      const newClient = await clientsApi.createClient({
        full_name: formData.full_name.trim(),
        phone: formData.phone.trim(),
      })
      onSuccess(newClient)
    } catch (error: any) {
      console.error('Ошибка создания клиента:', error)
      alert(error.response?.data?.detail || 'Не удалось создать клиента')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 10001 }}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
        <div className="modal-header">
          <h2>Создать нового клиента</h2>
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
              placeholder="Иванов Иван Иванович"
              autoFocus
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
              placeholder="+7 (999) 123-45-67"
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
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

export default Calendar



