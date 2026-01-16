import { useState, useEffect, useCallback } from 'react'
import { bookingsApi } from '../api/bookings'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import './Statistics.css'

interface StatisticsData {
  totalBookings: number
  newBookings: number
  confirmedBookings: number
  completedBookings: number
  cancelledBookings: number
  totalRevenue: number
  paidRevenue: number
  unpaidRevenue: number
  averageBookingAmount: number
  bookingsByDay: Array<{ date: string; count: number }>
  bookingsByService: Array<{ service_name: string; count: number }>
  bookingsByMaster: Array<{ master_name: string; count: number }>
}

function Statistics() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<StatisticsData | null>(null)
  // По умолчанию показываем за все время
  const getDefaultDateRange = () => {
    const futureDate = new Date()
    futureDate.setFullYear(futureDate.getFullYear() + 10) // +10 лет в будущее
    return {
      start: '2020-01-01',
      end: futureDate.toISOString().split('T')[0]
    }
  }
  const [dateRange, setDateRange] = useState(getDefaultDateRange())

  const loadStatistics = useCallback(async () => {
    try {
      setLoading(true)
      console.log('📊 Загрузка статистики для периода:', dateRange.start, '-', dateRange.end)
      // Загружаем все записи постранично
      let allBookings: any[] = []
      let page = 1
      const pageSize = 1000
      let hasMore = true
      
      while (hasMore) {
        console.log(`📥 Загрузка страницы ${page}...`)
        const response = await bookingsApi.getBookings(page, pageSize, {
          start_date: dateRange.start,
          end_date: dateRange.end
        })
        
        console.log(`✅ Страница ${page}: получено ${response.items.length} записей, всего в БД: ${response.total}`)
        
        allBookings = [...allBookings, ...response.items]
        
        if (response.items.length < pageSize || allBookings.length >= response.total) {
          hasMore = false
        } else {
          page++
        }
      }

      const bookings = allBookings
      
      console.log('📊 Загружено записей:', bookings.length)
      console.log('📅 Период:', dateRange.start, '-', dateRange.end)

      // Подсчет статистики
      const totalBookings = bookings.length
      const newBookings = bookings.filter(b => b.status === 'new').length
      const confirmedBookings = bookings.filter(b => b.status === 'confirmed').length
      const completedBookings = bookings.filter(b => b.status === 'completed').length
      const cancelledBookings = bookings.filter(b => b.status === 'cancelled').length

      // Учитываем только завершенные и оплаченные записи
      const completedPaidBookings = bookings.filter(b => b.status === 'completed' && b.is_paid)
      
      // Преобразуем amount в число для корректного подсчета
      const totalRevenue = completedPaidBookings.reduce((sum, b) => {
        const amount = typeof b.amount === 'number' ? b.amount : (typeof b.amount === 'string' ? parseFloat(b.amount) || 0 : 0)
        return sum + amount
      }, 0)
      
      const paidRevenue = totalRevenue // Для завершенных записей paidRevenue = totalRevenue
      const unpaidRevenue = 0 // Неоплаченные завершенные записи не учитываются в статистике
      const averageBookingAmount = completedPaidBookings.length > 0 ? totalRevenue / completedPaidBookings.length : 0
      
      console.log('💰 Выручка:', {
        completedPaidBookings: completedPaidBookings.length,
        totalRevenue,
        paidRevenue,
        unpaidRevenue,
        averageBookingAmount,
        amounts: completedPaidBookings.map(b => ({ id: b.id, amount: b.amount, amountType: typeof b.amount }))
      })

      // Статистика по дням
      const bookingsByDayMap = new Map<string, number>()
      bookings.forEach(b => {
        // b.service_date может быть строкой "YYYY-MM-DD" или объектом Date
        let dateStr: string
        if (typeof b.service_date === 'string') {
          dateStr = b.service_date.includes('T') ? b.service_date.split('T')[0] : b.service_date
        } else {
          dateStr = b.service_date
        }
        bookingsByDayMap.set(dateStr, (bookingsByDayMap.get(dateStr) || 0) + 1)
      })
      const bookingsByDay = Array.from(bookingsByDayMap.entries())
        .map(([date, count]) => ({ date, count }))
        .sort((a, b) => a.date.localeCompare(b.date))

      // Статистика по услугам
      const bookingsByServiceMap = new Map<string, number>()
      bookings.forEach(b => {
        const serviceName = b.service_name || 'Не указана'
        bookingsByServiceMap.set(serviceName, (bookingsByServiceMap.get(serviceName) || 0) + 1)
      })
      const bookingsByService = Array.from(bookingsByServiceMap.entries())
        .map(([service_name, count]) => ({ service_name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10)

      // Статистика по мастерам
      const bookingsByMasterMap = new Map<string, number>()
      bookings.forEach(b => {
        const masterName = b.master_name || 'Не назначен'
        bookingsByMasterMap.set(masterName, (bookingsByMasterMap.get(masterName) || 0) + 1)
      })
      const bookingsByMaster = Array.from(bookingsByMasterMap.entries())
        .map(([master_name, count]) => ({ master_name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10)

      const statisticsData = {
        totalBookings,
        newBookings,
        confirmedBookings,
        completedBookings,
        cancelledBookings,
        totalRevenue,
        paidRevenue,
        unpaidRevenue,
        averageBookingAmount,
        bookingsByDay,
        bookingsByService,
        bookingsByMaster
      }
      
      console.log('✅ Статистика загружена:', statisticsData)
      setStats(statisticsData)
    } catch (error: any) {
      console.error('❌ Ошибка загрузки статистики:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      } else {
        // Устанавливаем пустую статистику при ошибке
        setStats({
          totalBookings: 0,
          newBookings: 0,
          confirmedBookings: 0,
          completedBookings: 0,
          cancelledBookings: 0,
          totalRevenue: 0,
          paidRevenue: 0,
          unpaidRevenue: 0,
          averageBookingAmount: 0,
          bookingsByDay: [],
          bookingsByService: [],
          bookingsByMaster: []
        })
      }
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  useEffect(() => {
    console.log('📅 Период изменился:', dateRange.start, '-', dateRange.end)
    loadStatistics()
  }, [dateRange.start, dateRange.end, loadStatistics])

  const setDateRangeToday = () => {
    const today = new Date().toISOString().split('T')[0]
    const newRange = { start: today, end: today }
    console.log('🔘 Кнопка "Сегодня" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const setDateRangeYesterday = () => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toISOString().split('T')[0]
    const newRange = { start: yesterdayStr, end: yesterdayStr }
    console.log('🔘 Кнопка "Вчера" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const setDateRangeWeek = () => {
    const today = new Date()
    const weekAgo = new Date()
    weekAgo.setDate(weekAgo.getDate() - 7)
    const newRange = {
      start: weekAgo.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    }
    console.log('🔘 Кнопка "Неделя" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const setDateRangeMonth = () => {
    const today = new Date()
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
    const newRange = {
      start: monthStart.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    }
    console.log('🔘 Кнопка "Месяц" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const setDateRange3Months = () => {
    const today = new Date()
    const threeMonthsAgo = new Date()
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3)
    const newRange = {
      start: threeMonthsAgo.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    }
    console.log('🔘 Кнопка "3 месяца" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const setDateRangeYear = () => {
    const today = new Date()
    const yearStart = new Date(today.getFullYear(), 0, 1)
    const newRange = {
      start: yearStart.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    }
    console.log('🔘 Кнопка "Год" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const setDateRangeAll = () => {
    // Устанавливаем очень широкий диапазон для "за все время"
    const futureDate = new Date()
    futureDate.setFullYear(futureDate.getFullYear() + 10) // +10 лет в будущее
    const newRange = {
      start: '2020-01-01',
      end: futureDate.toISOString().split('T')[0]
    }
    console.log('🔘 Кнопка "За все время" нажата, устанавливаем период:', newRange)
    setDateRange(newRange)
  }

  const formatCurrency = (amount: number | null | undefined) => {
    // Проверяем, что amount является валидным числом
    if (amount === null || amount === undefined || isNaN(amount)) {
      return '0 ₽'
    }
    
    // Преобразуем в число, если это строка
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
    
    if (isNaN(numAmount)) {
      return '0 ₽'
    }
    
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0
    }).format(numAmount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  // Данные для круговой диаграммы статусов
  const statusChartData = stats ? [
    { name: 'Новые', value: stats.newBookings, color: '#ffc107' },
    { name: 'Подтвержденные', value: stats.confirmedBookings, color: '#17a2b8' },
    { name: 'Завершенные', value: stats.completedBookings, color: '#28a745' },
    { name: 'Отмененные', value: stats.cancelledBookings, color: '#dc3545' }
  ].filter(item => item.value > 0) : []

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      
      const url = `/api/export/statistics?start_date=${dateRange.start}&end_date=${dateRange.end}`
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error('Ошибка экспорта')
      }
      
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `statistics_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(downloadUrl)
      document.body.removeChild(a)
    } catch (error: any) {
      console.error('Ошибка экспорта:', error)
      alert('Не удалось экспортировать данные')
    }
  }

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Статистика</h1>
      </div>

      <div className="statistics-filters">
        <div className="filter-dates-group">
          <div className="filter-group">
            <label>Период от</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className="filter-input"
            />
          </div>
          <div className="filter-group">
            <label>Период до</label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className="filter-input"
            />
          </div>
        </div>
        <div className="filter-period-buttons">
          <button 
            className="btn-period" 
            onClick={setDateRangeToday}
            title="Сегодня"
          >
            Сегодня
          </button>
          <button 
            className="btn-period" 
            onClick={setDateRangeYesterday}
            title="Вчера"
          >
            Вчера
          </button>
          <button 
            className="btn-period" 
            onClick={setDateRangeMonth}
            title="Месяц"
          >
            Месяц
          </button>
          <button 
            className="btn-period" 
            onClick={setDateRange3Months}
            title="3 месяца"
          >
            3 месяца
          </button>
          <button 
            className="btn-period" 
            onClick={setDateRangeYear}
            title="Год"
          >
            Год
          </button>
        </div>
        <div className="filter-actions">
          <button className="btn-filter-compact" onClick={loadStatistics}>
            🔄 Обновить
          </button>
          <button className="btn-filter-compact" onClick={handleExport}>
            📥 Экспорт CSV
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Загрузка статистики...</div>
      ) : stats ? (
        <div className="statistics-content">
          {/* Основные метрики */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Всего записей</div>
              <div className="stat-value">{stats.totalBookings}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Новые</div>
              <div className="stat-value stat-new">{stats.newBookings}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Подтвержденные</div>
              <div className="stat-value stat-confirmed">{stats.confirmedBookings}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Завершенные</div>
              <div className="stat-value stat-completed">{stats.completedBookings}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Отмененные</div>
              <div className="stat-value stat-cancelled">{stats.cancelledBookings}</div>
            </div>
          </div>

          {/* Финансовые метрики */}
          <div className="stats-grid">
            <div className="stat-card stat-card-revenue">
              <div className="stat-label">Общая выручка</div>
              <div className="stat-value stat-revenue">{formatCurrency(stats.totalRevenue)}</div>
            </div>
            <div className="stat-card stat-card-revenue">
              <div className="stat-label">Оплачено</div>
              <div className="stat-value stat-paid">{formatCurrency(stats.paidRevenue)}</div>
            </div>
            <div className="stat-card stat-card-revenue">
              <div className="stat-label">Не оплачено</div>
              <div className="stat-value stat-unpaid">{formatCurrency(stats.unpaidRevenue)}</div>
            </div>
            <div className="stat-card stat-card-revenue">
              <div className="stat-label">Средний чек</div>
              <div className="stat-value">{formatCurrency(stats.averageBookingAmount)}</div>
            </div>
          </div>

          {/* Статистика по услугам */}
          <div className="stats-section">
            <h2>Топ услуг</h2>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Услуга</th>
                    <th>Количество</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.bookingsByService.length > 0 ? (
                    stats.bookingsByService.map((item, index) => (
                      <tr key={index}>
                        <td>{item.service_name}</td>
                        <td>{item.count}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={2}>Нет данных</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Статистика по мастерам */}
          <div className="stats-section">
            <h2>Топ мастеров</h2>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Мастер</th>
                    <th>Количество записей</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.bookingsByMaster.length > 0 ? (
                    stats.bookingsByMaster.map((item, index) => (
                      <tr key={index}>
                        <td>{item.master_name}</td>
                        <td>{item.count}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={2}>Нет данных</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Статистика по дням */}
          <div className="stats-section">
            <h2>Записи по дням</h2>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Количество записей</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.bookingsByDay.length > 0 ? (
                    stats.bookingsByDay.map((item, index) => (
                      <tr key={index}>
                        <td>{formatDate(item.date)}</td>
                        <td>{item.count}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={2}>Нет данных</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Диаграммы */}
          <div className="charts-container">
            {/* Круговая диаграмма - распределение по статусам */}
            <div className="chart-card">
              <h2>Распределение по статусам</h2>
              {statusChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={statusChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {statusChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state" style={{ padding: '40px 20px' }}>
                  <p>Нет данных для отображения</p>
                </div>
              )}
            </div>

            {/* Столбчатая диаграмма - топ услуг */}
            <div className="chart-card">
              <h2>Топ услуг (количество записей)</h2>
              {stats.bookingsByService.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={stats.bookingsByService.slice(0, 8).map(item => ({
                      name: item.service_name.length > 15 ? item.service_name.substring(0, 15) + '...' : item.service_name,
                      fullName: item.service_name,
                      value: item.count
                    }))}
                    margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      angle={-45} 
                      textAnchor="end" 
                      height={80}
                      interval={0}
                    />
                    <YAxis />
                    <Tooltip 
                      formatter={(value: number) => [value, 'Записей']}
                      labelFormatter={(label) => {
                        const fullItem = stats.bookingsByService.slice(0, 8).find(item => 
                          (item.service_name.length > 15 ? item.service_name.substring(0, 15) + '...' : item.service_name) === label
                        )
                        return fullItem?.service_name || label
                      }}
                    />
                    <Bar dataKey="value" fill="#4a9eff" radius={[8, 8, 0, 0]}>
                      {stats.bookingsByService.slice(0, 8).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill="#4a9eff" />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state" style={{ padding: '40px 20px' }}>
                  <p>Нет данных для отображения</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <p>Нет данных для отображения</p>
        </div>
      )}
    </div>
  )
}

export default Statistics

