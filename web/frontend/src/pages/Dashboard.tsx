import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import apiClient from '../api/client'
import { mastersApi, Master } from '../api/masters'
import { bookingsApi, Booking, BookingCreateRequest } from '../api/bookings'
import { postsApi, Post } from '../api/posts'
import { clientsApi, Client, ClientCreateRequest } from '../api/clients'
import { servicesApi, Service } from '../api/services'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import './Dashboard.css'

function Dashboard() {
  const navigate = useNavigate()
  const [bookings, setBookings] = useState<Booking[]>([])
  const [todayBookings, setTodayBookings] = useState<Booking[]>([])
  const [mastersToday, setMastersToday] = useState<Array<{
    master: Master
    bookingsCount: number
    nextBooking: Booking | null
  }>>([])
  const [todayStats, setTodayStats] = useState({
    total: 0,
    new: 0,
    confirmed: 0,
    completed: 0,
    revenue: 0
  })
  const [postsData, setPostsData] = useState<Array<{
    name: string
    count: number
    postId: number
  }>>([])
  const [activePostsCount, setActivePostsCount] = useState(0)
  const [todayBookingsCount, setTodayBookingsCount] = useState(0)
  const [tomorrowBookingsCount, setTomorrowBookingsCount] = useState(0)
  const [todayBookingsTotal, setTodayBookingsTotal] = useState(0)
  const [tomorrowBookingsTotal, setTomorrowBookingsTotal] = useState(0)
  const [todayBookingsList, setTodayBookingsList] = useState<Booking[]>([])
  const [tomorrowBookingsList, setTomorrowBookingsList] = useState<Booking[]>([])
  const [availableSlots, setAvailableSlots] = useState<{
    today: string[]
    tomorrow: string[]
  }>({ today: [], tomorrow: [] })
  const [slotsDate, setSlotsDate] = useState<'today' | 'tomorrow'>('today')
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [showCreateBookingModal, setShowCreateBookingModal] = useState(false)
  const [createBookingDate, setCreateBookingDate] = useState<string>('')
  const [createBookingTime, setCreateBookingTime] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [loadingMasters, setLoadingMasters] = useState(true)

  useEffect(() => {
    loadBookings()
    loadTodayData()
    loadAvailableSlots()
  }, [])

  // Обновляем слоты при фокусе на окно (когда пользователь возвращается на вкладку)
  useEffect(() => {
    const handleFocus = () => {
      loadAvailableSlots()
      loadTodayData() // Обновляем данные о записях
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [])

  // Периодическое обновление слотов каждые 30 секунд
  useEffect(() => {
    const interval = setInterval(() => {
      loadAvailableSlots()
      loadTodayData() // Обновляем данные о записях
    }, 30000) // 30 секунд
    return () => clearInterval(interval)
  }, [])

  const loadBookings = async () => {
    try {
      setLoading(true)
      const data = await bookingsApi.getBookings(1, 20)
      setBookings(data.items || [])
    } catch (error: any) {
      console.error('Ошибка загрузки записей:', error)
      if (error.response?.status === 401) {
        navigate('/login')
      }
      setBookings([])
    } finally {
      setLoading(false)
    }
  }

  const loadTodayData = async () => {
    try {
      setLoadingMasters(true)
      const today = new Date().toISOString().split('T')[0]
      
      // Загружаем записи на сегодня
      try {
        const todayData = await bookingsApi.getBookings(1, 1000, {
          start_date: today,
          end_date: today
        })
        const todayBookingsList = todayData.items || []
        setTodayBookings(todayBookingsList)
        setTodayBookingsList(todayBookingsList) // Сохраняем для расчета доступных записей
        
        // Общее количество всех записей на сегодня (устанавливаем сразу после загрузки)
        setTodayBookingsTotal(todayBookingsList.length)
        console.log('📊 Загружено записей на сегодня:', todayBookingsList.length)
        
        // Подсчитываем статистику на сегодня
        const stats = {
          total: todayBookingsList.length,
          new: todayBookingsList.filter(b => b.status === 'new').length,
          confirmed: todayBookingsList.filter(b => b.status === 'confirmed').length,
          completed: todayBookingsList.filter(b => b.status === 'completed').length,
          revenue: todayBookingsList
            .filter(b => b.status === 'completed' && b.is_paid && b.amount)
            .reduce((sum, b) => sum + (b.amount || 0), 0)
        }
        setTodayStats(stats)
        
        // Подсчитываем количество записей на сегодня (только new и confirmed)
        const todayBookingsActive = todayBookingsList.filter(
          b => b.status === 'new' || b.status === 'confirmed'
        ).length
        setTodayBookingsCount(todayBookingsActive)
      } catch (error) {
        console.error('Ошибка загрузки записей на сегодня:', error)
        // Не сбрасываем значения, если они уже были установлены ранее
      }

      // Загружаем мастеров с их нарядами на сегодня
      try {
        const mastersData = await mastersApi.getMasters(1, 100)
        const today = new Date().toISOString().split('T')[0]
        
        const mastersWithBookings = await Promise.all(
          mastersData.items.map(async (master) => {
            try {
              const schedule = await mastersApi.getMasterSchedule(master.id, today)
              const bookings = schedule.bookings || []
              
              // Находим ближайшую запись
              const now = new Date()
              const nextBooking = bookings
                .filter(b => {
                  const bookingTime = new Date(`${b.service_date}T${b.time}`)
                  return bookingTime > now
                })
                .sort((a, b) => {
                  const timeA = new Date(`${a.service_date}T${a.time}`)
                  const timeB = new Date(`${b.service_date}T${b.time}`)
                  return timeA.getTime() - timeB.getTime()
                })[0] || null
              
              return {
                master,
                bookingsCount: bookings.length,
                nextBooking
              }
            } catch (error) {
              return {
                master,
                bookingsCount: 0,
                nextBooking: null
              }
            }
          })
        )
        
        setMastersToday(mastersWithBookings)
      } catch (error) {
        console.error('Ошибка загрузки мастеров:', error)
      }

      // Загружаем данные о рабочих местах и их загрузке
      try {
        const postsDataList = await postsApi.getPosts(1, 100, undefined, true)
        const activePosts = postsDataList.items.filter(post => post.is_active)
        setActivePostsCount(activePosts.length)
        
        const todayBookingsList = todayBookings || []
        const postsWithBookings = postsDataList.items.map(post => {
          const postBookings = todayBookingsList.filter(b => b.post_id === post.id)
          return {
            name: post.name || `Рабочее место №${post.number}`,
            count: postBookings.length,
            postId: post.id
          }
        }).sort((a, b) => b.count - a.count) // Сортируем по убыванию загрузки
        
        setPostsData(postsWithBookings)
      } catch (error) {
        console.error('Ошибка загрузки рабочих мест:', error)
      }
      
      // Загружаем записи на завтра (отдельный try-catch, чтобы не влиять на данные на сегодня)
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      const tomorrowStr = tomorrow.toISOString().split('T')[0]
      
      try {
        const tomorrowData = await bookingsApi.getBookings(1, 1000, {
          start_date: tomorrowStr,
          end_date: tomorrowStr
        })
        const tomorrowBookingsList = tomorrowData.items || []
        const tomorrowBookingsActive = tomorrowBookingsList.filter(
          b => b.status === 'new' || b.status === 'confirmed'
        ).length
        setTomorrowBookingsCount(tomorrowBookingsActive)
        // Общее количество всех записей на завтра
        setTomorrowBookingsTotal(tomorrowBookingsList.length)
        setTomorrowBookingsList(tomorrowBookingsList) // Сохраняем для расчета доступных записей
        console.log('📊 Загружено записей на завтра:', tomorrowBookingsList.length)
      } catch (error) {
        console.error('Ошибка загрузки записей на завтра:', error)
        // Не сбрасываем значения, если они уже были установлены ранее
        // Только если это первая загрузка и значения еще не установлены
        if (tomorrowBookingsTotal === 0) {
          setTomorrowBookingsCount(0)
          setTomorrowBookingsTotal(0)
          setTomorrowBookingsList([])
        }
      }
    } catch (error: any) {
      console.error('Критическая ошибка загрузки данных:', error)
      // Сбрасываем значения только при критической ошибке
      // Но не сбрасываем, если данные уже были загружены ранее
    } finally {
      setLoadingMasters(false)
    }
  }

  const loadAvailableSlots = async () => {
    try {
      setLoadingSlots(true)
      // Используем локальное время для правильного определения сегодня/завтра
      const now = new Date()
      // Получаем дату в локальном времени, а не UTC
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
      
      const tomorrow = new Date(today)
      tomorrow.setDate(tomorrow.getDate() + 1)
      const tomorrowStr = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`
      
      console.log('🔄 Загрузка слотов для:', { todayStr, tomorrowStr, timestamp: new Date().toISOString() })
      
      // Добавляем timestamp к запросам, чтобы избежать кэширования
      const timestamp = Date.now()
      const [todaySlotsResult, tomorrowSlotsResult] = await Promise.all([
        bookingsApi.getAvailableSlots(todayStr, undefined, undefined, undefined).catch(err => {
          console.error('❌ Ошибка загрузки слотов на сегодня:', err)
          console.error('Response:', err.response?.data)
          console.error('Response detail:', JSON.stringify(err.response?.data))
          console.error('Status:', err.response?.status)
          console.error('URL:', err.config?.url)
          return []
        }),
        bookingsApi.getAvailableSlots(tomorrowStr, undefined, undefined, undefined).catch(err => {
          console.error('❌ Ошибка загрузки слотов на завтра:', err)
          console.error('Response:', err.response?.data)
          console.error('Response detail:', JSON.stringify(err.response?.data))
          console.error('Status:', err.response?.status)
          console.error('URL:', err.config?.url)
          return []
        })
      ])
      
      console.log('✅ Полученные слоты:', { 
        today: todaySlotsResult, 
        todayCount: todaySlotsResult?.length || 0,
        tomorrow: tomorrowSlotsResult,
        tomorrowCount: tomorrowSlotsResult?.length || 0,
        timestamp: new Date().toISOString()
      })
      console.log('ℹ️ ВАЖНО: Количество слотов (временных интервалов) не зависит от количества рабочих мест!')
      console.log('ℹ️ Слоты - это просто время: 9:00, 9:30, 10:00 и т.д.')
      console.log('ℹ️ Количество рабочих мест влияет на то, сколько ЗАПИСЕЙ можно принять на одно время')
      
      // Фильтруем прошедшие слоты для сегодня
      // Создаем текущее время заново для точного сравнения
      const currentTime = new Date()
      const currentDateStr = currentTime.toISOString().split('T')[0]
      
      const todayFiltered = (todaySlotsResult || []).filter(slot => {
        // Если это не сегодня, показываем все слоты
        if (currentDateStr !== todayStr) {
          return true
        }
        
        // Для сегодня фильтруем прошедшие слоты
        const [hours, minutes] = slot.split(':').map(Number)
        const currentHours = currentTime.getHours()
        const currentMinutes = currentTime.getMinutes()
        
        // Сравниваем время: если часы больше или (часы равны и минуты больше/равны), то слот в будущем
        if (hours > currentHours) {
          return true
        }
        if (hours === currentHours && minutes > currentMinutes) {
          return true
        }
        
        // Слот в прошлом
        return false
      })
      
      setAvailableSlots({
        today: todayFiltered, // Показываем все доступные слоты, не ограничиваем
        tomorrow: (tomorrowSlotsResult || [])
      })
    } catch (error: any) {
      console.error('Ошибка загрузки свободных слотов:', error)
      console.error('Детали ошибки:', error.response?.data)
      setAvailableSlots({ today: [], tomorrow: [] })
    } finally {
      setLoadingSlots(false)
    }
  }

  const handleSlotClick = (date: string, time: string) => {
    setCreateBookingDate(date)
    setCreateBookingTime(time)
    setShowCreateBookingModal(true)
  }

  const handleBookingCreated = () => {
    setShowCreateBookingModal(false)
    loadBookings()
    loadTodayData()
    loadAvailableSlots()
  }

  // Функция для расчета доступных записей с учетом занятых рабочих мест по слотам
  const calculateAvailableBookings = (
    slots: string[],
    bookings: Booking[],
    activePostsCount: number,
    date: string
  ): number => {
    if (slots.length === 0 || activePostsCount === 0) {
      return 0
    }

    let totalAvailable = 0

    slots.forEach(slot => {
      // Парсим время слота
      const [hours, minutes] = slot.split(':').map(Number)
      const slotStart = new Date(`${date}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`)
      // Предполагаем стандартную длительность 30 минут (можно сделать настраиваемой)
      const slotEnd = new Date(slotStart.getTime() + 30 * 60 * 1000)

      // Находим записи, которые пересекаются с этим слотом
      const occupiedPosts = new Set<number>()
      let bookingsWithoutPost = 0

      bookings.forEach(booking => {
        // Пропускаем отмененные и завершенные записи
        if (booking.status === 'cancelled' || booking.status === 'completed') {
          return
        }

        // Проверяем пересечение времени
        const bookingStart = new Date(`${booking.service_date}T${booking.time}:00`)
        const bookingEnd = new Date(`${booking.service_date}T${booking.end_time}:00`)

        // Если времена пересекаются
        if (!(slotEnd <= bookingStart || slotStart >= bookingEnd)) {
          if (booking.post_id) {
            occupiedPosts.add(booking.post_id)
          } else {
            // Запись без рабочего места считается как занятое одно рабочее место
            bookingsWithoutPost++
          }
        }
      })

      // Доступных записей на этот слот = активных рабочих мест - занятых рабочих мест
      const availableOnSlot = Math.max(0, activePostsCount - occupiedPosts.size - bookingsWithoutPost)
      totalAvailable += availableOnSlot
    })

    return totalAvailable
  }

  // Расчет доступных записей с учетом занятых рабочих мест по слотам
  const todayDate = new Date().toISOString().split('T')[0]
  const tomorrowDate = new Date()
  tomorrowDate.setDate(tomorrowDate.getDate() + 1)
  const tomorrowDateStr = tomorrowDate.toISOString().split('T')[0]
  
  // Рассчитываем доступные записи только если есть слоты и рабочие места
  const todayAvailableBookings = (availableSlots.today.length > 0 && activePostsCount > 0)
    ? calculateAvailableBookings(
        availableSlots.today,
        todayBookingsList,
        activePostsCount,
        todayDate
      )
    : 0
  
  const tomorrowAvailableBookings = (availableSlots.tomorrow.length > 0 && activePostsCount > 0)
    ? calculateAvailableBookings(
        availableSlots.tomorrow,
        tomorrowBookingsList,
        activePostsCount,
        tomorrowDateStr
      )
    : 0
  
  // Для отображения используем общее количество записей, если расчетное количество = 0
  // но есть записи (это означает, что все слоты заняты или нет свободных слотов)
  const displayTodayAvailable = todayAvailableBookings > 0 
    ? todayAvailableBookings 
    : (todayBookingsTotal > 0 ? todayBookingsTotal : 0)
  
  const displayTomorrowAvailable = tomorrowAvailableBookings > 0
    ? tomorrowAvailableBookings
    : (tomorrowBookingsTotal > 0 ? tomorrowBookingsTotal : 0)

  const totalBookings = bookings.length
  const newBookings = bookings.filter(b => b.status === 'new').length
  const confirmedBookings = bookings.filter(b => b.status === 'confirmed').length
  const completedBookings = bookings.filter(b => b.status === 'completed').length

  // Сортируем ближайшие записи на сегодня
  const upcomingTodayBookings = [...todayBookings]
    .filter(b => {
      const bookingTime = new Date(`${b.service_date}T${b.time}`)
      return bookingTime > new Date() && (b.status === 'confirmed' || b.status === 'new')
    })
    .sort((a, b) => {
      const timeA = new Date(`${a.service_date}T${a.time}`)
      const timeB = new Date(`${b.service_date}T${b.time}`)
      return timeA.getTime() - timeB.getTime()
    })
    .slice(0, 10)

  return (
    <div className="dashboard">
      <div className="page-header-simple">
        <div>
          <h1>Дашборд</h1>
          <p className="dashboard-subtitle">Обзор системы</p>
        </div>
      </div>
      
      <div className="stats-grid">
        <div className="stat-card stat-primary anim-delay-1">
          <div className="stat-icon">📋</div>
          <div className="stat-content">
            <h3>Всего записей</h3>
            <p className="stat-value">{totalBookings}</p>
          </div>
        </div>
        
        <div className="stat-card stat-warning anim-delay-2">
          <div className="stat-icon">🆕</div>
          <div className="stat-content">
            <h3>Новых</h3>
            <p className="stat-value">
              {newBookings}
            </p>
          </div>
        </div>
        
        <div className="stat-card stat-success anim-delay-3">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <h3>Подтвержденных</h3>
            <p className="stat-value">{confirmedBookings}</p>
          </div>
        </div>
        
        <div className="stat-card stat-info anim-delay-4">
          <div className="stat-icon">✔️</div>
          <div className="stat-content">
            <h3>Завершенных</h3>
            <p className="stat-value">{completedBookings}</p>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div 
          className="stat-card stat-primary stat-card-clickable stat-card-with-link anim-delay-1" 
          onClick={() => {
            const today = new Date().toISOString().split('T')[0]
            navigate(`/bookings?start_date=${today}&end_date=${today}`)
          }}
          title="Перейти к записям сегодня"
        >
          <div>
            <div className="stat-icon">📅</div>
            <div className="stat-content">
              <h3>Записей сегодня</h3>
              <p className="stat-value">{todayStats.total}</p>
            </div>
          </div>
          <div className="stat-cta">Перейти к записям →</div>
        </div>
        
        <div 
          className="stat-card stat-warning stat-card-clickable stat-card-with-link anim-delay-2" 
          onClick={() => navigate('/bookings?status=new&sort=date&sortDir=desc')}
          title="Перейти к новым записям"
        >
          <div>
            <div className="stat-icon">🆕</div>
            <div className="stat-content">
              <h3>Новых сегодня</h3>
              <p className="stat-value">{todayStats.new}</p>
            </div>
          </div>
          <div className="stat-cta">Перейти к записям →</div>
        </div>
        
        <div 
          className="stat-card stat-success stat-card-clickable stat-card-with-link anim-delay-3" 
          onClick={() => {
            const today = new Date().toISOString().split('T')[0]
            navigate(`/bookings?status=confirmed&start_date=${today}&end_date=${today}&sort=date&sortDir=desc`)
          }}
          title="Перейти к подтвержденным записям сегодня"
        >
          <div>
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <h3>Подтвержденных сегодня</h3>
              <p className="stat-value">{todayStats.confirmed}</p>
            </div>
          </div>
          <div className="stat-cta">Перейти к записям →</div>
        </div>
        
        <div className="stat-card stat-info anim-delay-4">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <h3>Доход сегодня</h3>
            <p className="stat-value">{todayStats.revenue.toLocaleString('ru-RU')}₽</p>
          </div>
        </div>
      </div>

      {/* Свободные слоты и доступные записи */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Свободные слоты и доступные записи</h2>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button 
              className="btn-sm"
              onClick={loadAvailableSlots}
              disabled={loadingSlots}
              title="Обновить слоты"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              {loadingSlots ? '⏳' : '🔄'}
            </button>
            <div className="date-toggle">
              <button 
                className={`toggle-btn ${slotsDate === 'today' ? 'active' : ''}`}
                onClick={() => setSlotsDate('today')}
              >
                Сегодня
              </button>
              <button 
                className={`toggle-btn ${slotsDate === 'tomorrow' ? 'active' : ''}`}
                onClick={() => setSlotsDate('tomorrow')}
              >
                Завтра
              </button>
            </div>
          </div>
        </div>
        
        {loadingSlots ? (
          <div className="loading">Загрузка слотов...</div>
        ) : (
          <>
            <div className="availability-grid">
              <div className="availability-card today">
                <div className="availability-label">📊 Сегодня</div>
                <div className="availability-value">{displayTodayAvailable}</div>
                <div className="availability-hint">
                  {todayAvailableBookings > 0 ? 'доступных записей' : 'всего записей'}
                </div>
                <div className="availability-meta">
                  • Всего записей: <strong>{todayBookingsTotal}</strong><br/>
                  • Доступных (new/confirmed): {todayBookingsCount}<br/>
                  • Слотов: {availableSlots.today.length}<br/>
                  • Рабочих мест: {activePostsCount}
                </div>
              </div>
              
              <div className="availability-card tomorrow">
                <div className="availability-label">📊 Завтра</div>
                <div className="availability-value">{displayTomorrowAvailable}</div>
                <div className="availability-hint">
                  {tomorrowAvailableBookings > 0 ? 'доступных записей' : 'всего записей'}
                </div>
                <div className="availability-meta">
                  • Всего записей: <strong>{tomorrowBookingsTotal}</strong><br/>
                  • Доступных (new/confirmed): {tomorrowBookingsCount}<br/>
                  • Слотов: {availableSlots.tomorrow.length}<br/>
                  • Рабочих мест: {activePostsCount}
                </div>
              </div>
            </div>
            
            <div className="slots-grid">
              {(slotsDate === 'today' ? availableSlots.today : availableSlots.tomorrow).map((slot) => {
                const selectedDate = slotsDate === 'today' 
                  ? new Date().toISOString().split('T')[0]
                  : new Date(Date.now() + 86400000).toISOString().split('T')[0]
                
                return (
                  <div 
                    key={slot} 
                    className="slot-chip"
                    onClick={() => handleSlotClick(selectedDate, slot)}
                    title="Нажмите для создания записи"
                  >
                    {slot}
                  </div>
                )
              })}
            </div>
            
            {(slotsDate === 'today' ? availableSlots.today : availableSlots.tomorrow).length === 0 && (
              <div className="empty-state">
                <p>Нет свободных слотов на {slotsDate === 'today' ? 'сегодня' : 'завтра'}</p>
              </div>
            )}
            
            {(slotsDate === 'today' ? availableSlots.today : availableSlots.tomorrow).length > 0 && (
              <div className="slots-info">
                Всего свободно: {(slotsDate === 'today' ? availableSlots.today : availableSlots.tomorrow).length} {((slotsDate === 'today' ? availableSlots.today : availableSlots.tomorrow).length === 1 ? 'слот' : (slotsDate === 'today' ? availableSlots.today : availableSlots.tomorrow).length < 5 ? 'слота' : 'слотов')}
              </div>
            )}
          </>
        )}
      </div>

      {loadingMasters ? (
        <div className="dashboard-section">
          <div className="loading">Загрузка данных мастеров...</div>
        </div>
      ) : (
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Мастера с нарядами на сегодня</h2>
          </div>
          
          {mastersToday.length === 0 ? (
            <div className="empty-state">
              <p>Мастеров не найдено</p>
            </div>
          ) : (
            <>
              <div className="masters-grid">
                {mastersToday.map(({ master, bookingsCount, nextBooking }) => {
                  const today = new Date().toISOString().split('T')[0]
                  return (
                  <div 
                    key={master.id} 
                    className="master-card"
                    onClick={() => {
                      navigate('/masters')
                    }}
                    title="Нажмите для просмотра лист-наряда"
                  >
                    <div className="master-card-header">
                      <h3>{master.full_name}</h3>
                      <span className={`master-badge ${bookingsCount === 0 ? 'empty' : bookingsCount > 5 ? 'busy' : 'normal'}`}>
                        {bookingsCount} {bookingsCount === 1 ? 'запись' : bookingsCount < 5 ? 'записи' : 'записей'}
                      </span>
                    </div>
                    {nextBooking ? (
                      <div className="master-card-next">
                        <div className="next-booking-time">
                          ⏰ {nextBooking.time.substring(0, 5)}
                        </div>
                        <div className="next-booking-client">
                          {nextBooking.client_name || 'Клиент'}
                        </div>
                        <div className="next-booking-service">
                          {nextBooking.service_name || 'Услуга'}
                        </div>
                      </div>
                    ) : bookingsCount > 0 ? (
                      <div className="master-card-next">
                        <div className="next-booking-time">✅ Все записи завершены</div>
                      </div>
                    ) : (
                      <div className="master-card-next">
                        <div className="next-booking-time">📭 Нет записей</div>
                      </div>
                    )}
                  </div>
                  )
                })}
              </div>
              <div style={{ marginTop: '20px', textAlign: 'right' }}>
                <Link to="/masters" className="view-all-link">Все мастера →</Link>
              </div>
            </>
          )}
        </div>
      )}

      {postsData.length > 0 && (
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Загрузка рабочих мест на сегодня</h2>
          </div>
          
          <div className="chart-container-compact">
            <ResponsiveContainer width="100%" height={Math.max(200, postsData.length * 40)}>
              <BarChart
                data={postsData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  width={90}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value: number) => [value, 'Записей']}
                  labelStyle={{ fontWeight: 'bold' }}
                />
                <Bar dataKey="count" fill="#4a9eff" radius={[0, 8, 8, 0]}>
                  {postsData.map((entry, index) => {
                    let color = '#4a9eff'
                    if (entry.count === 0) color = '#e9ecef'
                    else if (entry.count > 5) color = '#ffc107'
                    else if (entry.count > 3) color = '#28a745'
                    return <Cell key={`cell-${index}`} fill={color} />
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ marginTop: '20px', textAlign: 'right' }}>
            <Link to="/posts" className="view-all-link">Все рабочие места →</Link>
          </div>
        </div>
      )}

      {upcomingTodayBookings.length > 0 && (
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Ближайшие записи на сегодня</h2>
          </div>
          
          <div className="table-container">
            <table className="bookings-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Клиент</th>
                  <th>Услуга</th>
                  <th>Мастер</th>
                  <th>Рабочее место</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                {upcomingTodayBookings.map((booking) => (
                  <tr 
                    key={booking.id}
                    onClick={() => navigate(`/bookings?booking_id=${booking.id}`)}
                    style={{ cursor: 'pointer' }}
                    title="Нажмите для просмотра деталей записи"
                  >
                    <td>{booking.time.substring(0, 5)}</td>
                    <td>{booking.client_name || '-'}</td>
                    <td>{booking.service_name || '-'}</td>
                    <td>{booking.master_name || '-'}</td>
                    <td>{booking.post_number ? `№${booking.post_number}` : '-'}</td>
                    <td>
                      <span className={`status status-${booking.status}`}>
                        {booking.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '20px', textAlign: 'right' }}>
            <Link 
              to={`/bookings?start_date=${new Date().toISOString().split('T')[0]}&end_date=${new Date().toISOString().split('T')[0]}`} 
              className="view-all-link"
            >
              Все записи сегодня →
            </Link>
          </div>
        </div>
      )}

      <div className="dashboard-section">
        <div className="section-header">
          <h2>Последние записи</h2>
        </div>
        
        {loading ? (
          <div className="loading">Загрузка...</div>
        ) : bookings.length === 0 ? (
          <div className="empty-state">
            <p>Записей пока нет</p>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="bookings-table">
                <thead>
                  <tr>
                    <th>Номер</th>
                    <th>Дата</th>
                    <th>Время</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.slice(0, 10).map((booking) => (
                    <tr 
                      key={booking.id}
                      onClick={() => navigate(`/bookings?booking_id=${booking.id}`)}
                      style={{ cursor: 'pointer' }}
                      title="Нажмите для просмотра деталей записи"
                    >
                      <td>{booking.booking_number}</td>
                      <td>{booking.service_date}</td>
                      <td>{booking.time}</td>
                      <td>
                        <span className={`status status-${booking.status}`}>
                          {booking.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: '20px', textAlign: 'right' }}>
              <Link to="/bookings" className="view-all-link">Посмотреть все →</Link>
            </div>
          </>
        )}
      </div>

      {showCreateBookingModal && (
        <CreateBookingModal
          onClose={() => setShowCreateBookingModal(false)}
          onSuccess={handleBookingCreated}
          initialDate={createBookingDate}
          initialTime={createBookingTime}
        />
      )}
    </div>
  )
}

// Компонент модального окна создания записи
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
      if (initialTime && !formData.time) {
        setFormData(prev => ({ ...prev, time: initialTime }))
      }
    }
  }, [formData.service_date, formData.service_id, formData.master_id, formData.post_id])

  useEffect(() => {
    if (formData.service_id) {
      const selectedService = services.find(s => s.id === formData.service_id)
      if (selectedService && formData.duration !== selectedService.duration) {
        setFormData(prev => ({ ...prev, duration: selectedService.duration }))
      }
    }
  }, [formData.service_id, services])

  // Загрузка занятых рабочих мест при изменении даты, времени, длительности и мастера
  useEffect(() => {
    if (formData.service_date && formData.time && formData.duration) {
      loadOccupiedPosts()
    } else {
      // Если нет времени, очищаем список занятых постов, чтобы все посты были доступны
      setOccupiedPostIds(new Set())
    }
  }, [formData.service_date, formData.time, formData.duration, formData.master_id])

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

  // Функция для загрузки занятых рабочих мест на выбранное время
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

      // Находим занятые рабочие места
      const occupied = new Set<number>()
      bookingsData.items.forEach(booking => {
        // Пропускаем отмененные и завершенные записи
        if (booking.status === 'cancelled' || booking.status === 'completed') {
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
      console.log('🚫 Занятые рабочие места на', formData.service_date, formData.time, ':', Array.from(occupied))
    } catch (error) {
      console.error('Ошибка загрузки занятых рабочих мест:', error)
      setOccupiedPostIds(new Set())
    }
  }

  const handleClientCreated = async (newClient: Client) => {
    await loadData()
    setFormData(prev => ({ ...prev, client_id: newClient.id }))
    setShowCreateClientModal(false)
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
      <div className="modal-content modal-compact" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header modal-header-compact">
          <h2>Создать новую запись</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        {dataLoading ? (
          <div className="modal-body modal-body-compact">
            <div className="loading">Загрузка данных...</div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="modal-body modal-body-compact">
            <div className="form-group form-group-compact">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label className="form-label-compact">Клиент *</label>
                <button
                  type="button"
                  onClick={() => setShowCreateClientModal(true)}
                  className="btn-sm btn-primary"
                  style={{ padding: '3px 10px', fontSize: '11px' }}
                >
                  + Новый
                </button>
              </div>
              <select
                value={formData.client_id || ''}
                onChange={(e) => setFormData({ ...formData, client_id: parseInt(e.target.value) })}
                required
                className="form-input form-input-compact"
                disabled={dataLoading || clients.length === 0}
              >
                <option value="">Выберите клиента</option>
                {clients.map(client => (
                  <option key={client.id} value={client.id}>
                    {client.full_name} {client.phone ? `(${client.phone})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group form-group-compact">
                <label className="form-label-compact">Услуга</label>
                <select
                  value={formData.service_id || ''}
                  onChange={(e) => setFormData({ ...formData, service_id: e.target.value ? parseInt(e.target.value) : undefined })}
                  className="form-input form-input-compact"
                  disabled={dataLoading}
                >
                  <option value="">Выберите услугу</option>
                  {services.map(service => (
                    <option key={service.id} value={service.id}>
                      {service.name} ({service.duration} мин)
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group form-group-compact">
                <label className="form-label-compact">Мастер</label>
                <select
                  value={formData.master_id || ''}
                  onChange={(e) => {
                    const newMasterId = e.target.value ? parseInt(e.target.value) : undefined
                    // Сбрасываем пост при изменении мастера
                    setFormData({ ...formData, master_id: newMasterId, post_id: undefined })
                  }}
                  className="form-input form-input-compact"
                  disabled={dataLoading}
                >
                  <option value="">Выберите мастера</option>
                  {masters.map(master => (
                    <option key={master.id} value={master.id}>
                      {master.full_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group form-group-compact">
              <label className="form-label-compact">Рабочее место</label>
              <select
                value={formData.post_id || ''}
                onChange={(e) => setFormData({ ...formData, post_id: e.target.value ? parseInt(e.target.value) : undefined })}
                className="form-input form-input-compact"
                disabled={dataLoading || posts.length === 0}
              >
                <option value="">Выберите рабочее место</option>
                {posts.length === 0 && !dataLoading ? (
                  <option disabled>Нет доступных рабочих мест</option>
                ) : (
                  posts
                    .filter(post => {
                      // Показываем пост, если:
                      // 1. Он не занят, ИЛИ
                      // 2. Он уже выбран (чтобы не потерять выбор), ИЛИ
                      // 3. Время еще не выбрано (чтобы можно было выбрать пост до выбора времени)
                      return !occupiedPostIds.has(post.id) || 
                             post.id === formData.post_id || 
                             !formData.time
                    })
                    .map(post => {
                      const isOccupied = occupiedPostIds.has(post.id) && 
                                       post.id !== formData.post_id && 
                                       formData.time // Показываем как занятый только если время выбрано
                      return (
                        <option 
                          key={post.id} 
                          value={post.id}
                          disabled={isOccupied}
                          style={isOccupied ? { color: '#999', fontStyle: 'italic' } : {}}
                        >
                          {post.name || `Рабочее место №${post.number}`} {isOccupied ? ' (Занято)' : ''}
                        </option>
                      )
                    })
                )}
              </select>
              {posts.length === 0 && !dataLoading && (
                <small style={{ color: '#999', fontSize: '11px', display: 'block', marginTop: '3px' }}>
                  Нет доступных рабочих мест
                </small>
              )}
              {occupiedPostIds.size > 0 && formData.time && (
                <small style={{ color: '#666', fontSize: '11px', display: 'block', marginTop: '3px' }}>
                  ⚠️ {occupiedPostIds.size} {occupiedPostIds.size === 1 ? 'место занято' : 'мест занято'}
                </small>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <div className="form-group form-group-compact">
                <label className="form-label-compact">Дата *</label>
                <input
                  type="date"
                  value={formData.service_date}
                  onChange={(e) => setFormData({ ...formData, service_date: e.target.value })}
                  required
                  className="form-input form-input-compact"
                  disabled={dataLoading}
                />
              </div>

              <div className="form-group form-group-compact">
                <label className="form-label-compact">Время *</label>
                <select
                  value={formData.time}
                  onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                  required
                  className="form-input form-input-compact"
                  disabled={dataLoading}
                >
                  <option value="">Выберите</option>
                  {availableSlots.map(slot => (
                    <option key={slot} value={slot}>
                      {slot}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group form-group-compact">
                <label className="form-label-compact">Длительность</label>
                <input
                  type="number"
                  value={formData.duration || 30}
                  onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) || 30 })}
                  min="15"
                  step="15"
                  className="form-input form-input-compact"
                  disabled={dataLoading}
                />
              </div>
            </div>

            <div className="form-group form-group-compact">
              <label className="form-label-compact">Комментарий</label>
              <textarea
                value={formData.comment || ''}
                onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
                className="form-input form-input-compact"
                rows={2}
                disabled={dataLoading}
              />
            </div>

            <div className="modal-footer modal-footer-compact">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
                Отмена
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading || dataLoading}>
                {loading ? 'Создание...' : 'Создать запись'}
              </button>
            </div>
          </form>
        )}
      </div>
      {showCreateClientModal && (
        <CreateClientQuickModal
          onClose={() => setShowCreateClientModal(false)}
          onClientCreated={handleClientCreated}
        />
      )}
    </div>
  )
}

// Компонент быстрого создания клиента
interface CreateClientQuickModalProps {
  onClose: () => void
  onClientCreated: (client: Client) => void
}

function CreateClientQuickModal({ onClose, onClientCreated }: CreateClientQuickModalProps) {
  const [formData, setFormData] = useState<ClientCreateRequest>({
    full_name: '',
    phone: '',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.full_name || !formData.phone) {
      alert('Заполните имя и телефон')
      return
    }

    try {
      setLoading(true)
      // Отправляем только необходимые поля
      const clientData = {
        full_name: formData.full_name,
        phone: formData.phone,
      }
      const newClient = await clientsApi.createClient(clientData)
      onClientCreated(newClient)
    } catch (error: any) {
      console.error('Ошибка создания клиента:', error)
      alert(error.response?.data?.detail || 'Не удалось создать клиента')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-compact" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header modal-header-compact">
          <h2>Новый клиент</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body modal-body-compact">
          <div className="form-group form-group-compact">
            <label className="form-label-compact">ФИО *</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              required
              className="form-input form-input-compact"
            />
          </div>
          <div className="form-group form-group-compact">
            <label className="form-label-compact">Телефон *</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              required
              className="form-input form-input-compact"
            />
          </div>
          <div className="modal-footer modal-footer-compact">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Отмена
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Dashboard

