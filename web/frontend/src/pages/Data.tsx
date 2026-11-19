import { useState, useEffect } from 'react'
import { statisticsApi, OverviewStats, MastersStatsResponse, TimeStatsResponse, DailyStatsResponse } from '../api/statistics'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import './Statistics.css'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

function Data() {
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [mastersStats, setMastersStats] = useState<MastersStatsResponse | null>(null)
  const [timeStats, setTimeStats] = useState<TimeStatsResponse | null>(null)
  const [dailyStats, setDailyStats] = useState<DailyStatsResponse | null>(null)
  
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  })

  const loadData = async () => {
    try {
      setLoading(true)
      
      const [overviewData, mastersData, timeData, dailyData] = await Promise.all([
        statisticsApi.getOverview(dateRange.start, dateRange.end).catch(() => null),
        statisticsApi.getByMasters(dateRange.start, dateRange.end).catch(() => null),
        statisticsApi.getByTime(dateRange.start, dateRange.end).catch(() => null),
        statisticsApi.getDaily(dateRange.start, dateRange.end).catch(() => null),
      ])
      
      if (overviewData) setOverview(overviewData)
      if (mastersData) setMastersStats(mastersData)
      if (timeData) setTimeStats(timeData)
      if (dailyData) setDailyStats(dailyData)
    } catch (error: any) {
      console.error('Ошибка загрузки данных:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  // Данные для графика статусов
  const statusChartData = overview ? [
    { name: 'Подтвержденные', value: overview.bookings_confirmed, color: '#00C49F' },
    { name: 'Завершенные', value: overview.bookings_completed, color: '#0088FE' },
    { name: 'Отмененные', value: overview.bookings_cancelled, color: '#FF8042' },
    { name: 'Не явились', value: overview.bookings_no_show, color: '#FFBB28' },
  ] : []

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Данные</h1>
        </div>
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
        <div className="filter-actions">
          <button className="btn-filter-compact" onClick={loadData}>
            🔄 Обновить
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Загрузка данных...</div>
      ) : (
        <div className="statistics-content">
          {/* Общая статистика */}
          {overview && (
            <div className="stats-section">
              <h2>Общая статистика</h2>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Всего записей</div>
                  <div className="stat-value">{overview.bookings_count}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Подтвержденные</div>
                  <div className="stat-value stat-confirmed">{overview.bookings_confirmed}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Завершенные</div>
                  <div className="stat-value stat-completed">{overview.bookings_completed}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Отмененные</div>
                  <div className="stat-value stat-cancelled">{overview.bookings_cancelled}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Не явились</div>
                  <div className="stat-value">{overview.bookings_no_show}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Выручка</div>
                  <div className="stat-value">{formatCurrency(overview.revenue)}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Средний чек</div>
                  <div className="stat-value">{formatCurrency(overview.avg_check)}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Конверсия</div>
                  <div className="stat-value">{overview.conversion.toFixed(1)}%</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">% неявок</div>
                  <div className="stat-value">{overview.no_show_percent.toFixed(1)}%</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Новых клиентов</div>
                  <div className="stat-value">{overview.new_clients}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Постоянных клиентов</div>
                  <div className="stat-value">{overview.returning_clients}</div>
                </div>
              </div>

              {/* График статусов */}
              {statusChartData.length > 0 && (
                <div className="chart-container">
                  <h3>Распределение по статусам</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={statusChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {statusChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}

          {/* Статистика по мастерам */}
          {mastersStats && mastersStats.masters.length > 0 && (
            <div className="stats-section">
              <h2>Статистика по мастерам</h2>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={mastersStats.masters}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="master_name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="bookings_count" fill="#0088FE" name="Количество записей" />
                    <Bar dataKey="revenue" fill="#00C49F" name="Выручка" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              
              <div className="stats-table-container">
                <table className="stats-table">
                  <thead>
                    <tr>
                      <th>Мастер</th>
                      <th>Записей</th>
                      <th>Выручка</th>
                      <th>Средний чек</th>
                      <th>Загрузка</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mastersStats.masters.map((master) => (
                      <tr key={master.master_id}>
                        <td>{master.master_name}</td>
                        <td>{master.bookings_count}</td>
                        <td>{formatCurrency(master.revenue)}</td>
                        <td>{formatCurrency(master.avg_check)}</td>
                        <td>{master.load_percentage.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Почасовая статистика */}
          {timeStats && timeStats.hourly_stats.length > 0 && (
            <div className="stats-section">
              <h2>Почасовая статистика (пики загрузки)</h2>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={timeStats.hourly_stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" label={{ value: 'Час', position: 'insideBottom', offset: -5 }} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="bookings_count" fill="#8884d8" name="Количество записей" />
                    <Bar dataKey="load_percentage" fill="#82ca9d" name="Загрузка %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Ежедневная статистика */}
          {dailyStats && dailyStats.daily_stats.length > 0 && (
            <div className="stats-section">
              <h2>Ежедневная статистика</h2>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={dailyStats.daily_stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="date" 
                      tickFormatter={formatDate}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis />
                    <Tooltip labelFormatter={formatDate} />
                    <Legend />
                    <Line type="monotone" dataKey="bookings" stroke="#8884d8" name="Записи" />
                    <Line type="monotone" dataKey="revenue" stroke="#82ca9d" name="Выручка" />
                    <Line type="monotone" dataKey="load_percentage" stroke="#FF8042" name="Загрузка %" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              
              <div className="stats-table-container">
                <table className="stats-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Записи</th>
                      <th>Выручка</th>
                      <th>Неявки</th>
                      <th>Загрузка</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dailyStats.daily_stats.map((day, index) => (
                      <tr key={index}>
                        <td>{formatDate(day.date)}</td>
                        <td>{day.bookings}</td>
                        <td>{formatCurrency(day.revenue)}</td>
                        <td>{day.no_shows}</td>
                        <td>{day.load_percentage.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!overview && !mastersStats && !timeStats && !dailyStats && (
            <div className="empty-state">
              <p>Нет данных для отображения</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Data

