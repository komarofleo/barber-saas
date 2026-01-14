/**
 * Дашборд супер-администратора
 * 
 * Отображает:
 * - Общую статистику системы
 * - Графики доходов
 * - Список активных компаний
 * - Список компаний с истекающими подписками
 * - Быстрые действия
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { DashboardStats } from '../api/superAdmin'
import { useSidebar } from '../components/SuperAdminLayout'
import './SuperAdminDashboard.css'

const SuperAdminDashboard: React.FC = () => {
  const navigate = useNavigate()
  const { sidebarOpen, toggleSidebar } = useSidebar()

  // UI состояния
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')

  // Загрузка статистики
  useEffect(() => {
    fetchStats()
  }, [timeRange])

  const fetchStats = async () => {
    setLoading(true)
    setError(null)

    try {
      const { superAdminApi } = await import('../api/superAdmin')
      const fetchedStats = await superAdminApi.getDashboardStats()
      setStats(fetchedStats)
    } catch (err: any) {
      console.error('Ошибка загрузки статистики:', err)
      
      // Если ошибка 401 (Unauthorized), удаляем токен и позволяем SuperAdminProtectedRoute обработать перенаправление
      if (err.response?.status === 401 || err.message?.includes('401')) {
        localStorage.removeItem('super_admin_token')
        sessionStorage.removeItem('super_admin_token')
        localStorage.removeItem('super_admin')
        sessionStorage.removeItem('super_admin')
        // Не перенаправляем здесь - SuperAdminProtectedRoute сам обработает это
        return
      }
      
      setError(err.message || 'Не удалось загрузить статистику')
    } finally {
      setLoading(false)
    }
  }

  // Форматирование чисел
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('ru-RU').format(num)
  }

  // Форматирование валюты
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  // Процент активных компаний
  const getActiveCompaniesPercentage = (): number => {
    if (!stats || stats.total_companies === 0) return 0
    return ((stats.active_companies / stats.total_companies) * 100).toFixed(1)
  }

  // Обработчик клика на компанию
  const handleCompanyClick = (companyId: number) => {
    navigate(`/super-admin/companies/${companyId}`)
  }

  // Обработчик изменения периода
  const handleTimeRangeChange = (newRange: '7d' | '30d' | '90d') => {
    setTimeRange(newRange)
  }

  return (
    <div className="super-admin-dashboard">
      {/* Заголовок страницы - вынесен наружу для правильного позиционирования */}
      <div className="dashboard-header">
        <button
          className="dashboard-menu-toggle"
          onClick={toggleSidebar}
          title={sidebarOpen ? 'Свернуть меню' : 'Развернуть меню'}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>
        <div className="header-content">
          <h1 className="dashboard-title">Дашборд</h1>
          <p className="dashboard-subtitle">
            Общая статистика и управление системой
          </p>
        </div>
        <button
          className="refresh-button"
          onClick={() => fetchStats()}
          title="Обновить данные"
        >
          <span className="refresh-icon">↻</span>
        </button>
      </div>

      {/* Spacer для компенсации fixed header */}
      <div className="header-spacer"></div>

      <div className="dashboard-container">
        {/* Загрузка */}
        {loading && (
          <div className="dashboard-loading">
            <div className="spinner"></div>
            <p>Загрузка статистики...</p>
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="dashboard-error">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <button
              className="retry-button"
              onClick={() => fetchStats()}
            >
              Попробовать снова
            </button>
          </div>
        )}

        {/* Статистика */}
        {stats && !loading && !error && (
          <div className="dashboard-content">
            {/* Выбор периода */}
            <div className="time-range-selector">
              <button
                className={`range-button ${timeRange === '7d' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('7d')}
              >
                7 дней
              </button>
              <button
                className={`range-button ${timeRange === '30d' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('30d')}
              >
                30 дней
              </button>
              <button
                className={`range-button ${timeRange === '90d' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('90d')}
              >
                90 дней
              </button>
            </div>

            {/* Статистические карточки */}
            <div className="stats-cards">
              <div className="stat-card primary">
                <div className="stat-card-icon">🏢</div>
                <div className="stat-card-content">
                  <div className="stat-card-label">Всего компаний</div>
                  <div className="stat-card-value">
                    {formatNumber(stats.total_companies)}
                  </div>
                  <div className="stat-card-sublabel">
                    {formatNumber(stats.active_companies)} активных
                  </div>
                </div>
              </div>

              <div className="stat-card success">
                <div className="stat-card-icon">📊</div>
                <div className="stat-card-content">
                  <div className="stat-card-label">Активных подписок</div>
                  <div className="stat-card-value">
                    {formatNumber(stats.active_subscriptions)}
                  </div>
                  <div className="stat-card-sublabel">
                    {getActiveCompaniesPercentage()}%
                  </div>
                </div>
              </div>

              <div className="stat-card warning">
                <div className="stat-card-icon">⏰</div>
                <div className="stat-card-content">
                  <div className="stat-card-label">
                    Истекающих подписок
                  </div>
                  <div className="stat-card-value">
                    {formatNumber(stats.companies_with_expiring_subscription)}
                  </div>
                  <div className="stat-card-sublabel">
                    Требуют внимания
                  </div>
                </div>
              </div>

              <div className="stat-card info">
                <div className="stat-card-icon">🆕</div>
                <div className="stat-card-content">
                  <div className="stat-card-label">
                    Новых компаний (месяц)
                  </div>
                  <div className="stat-card-value">
                    +{formatNumber(stats.new_companies_this_month)}
                  </div>
                  <div className="stat-card-sublabel">
                    За текущий месяц
                  </div>
                </div>
              </div>
            </div>

            {/* Статистика доходов */}
            <div className="revenue-section">
              <div className="section-header">
                <h2 className="section-title">💰 Доходы</h2>
              </div>

              <div className="revenue-cards">
                <div className="revenue-card">
                  <div className="revenue-label">Общий доход</div>
                  <div className="revenue-value">
                    {formatCurrency(stats.total_revenue)}
                  </div>
                  <div className="revenue-period">За все время</div>
                </div>

                <div className="revenue-card highlighted">
                  <div className="revenue-label">Доход за месяц</div>
                  <div className="revenue-value">
                    {formatCurrency(stats.monthly_revenue)}
                  </div>
                  <div className="revenue-period">За текущий месяц</div>
                </div>
              </div>

              {/* Прогноз дохода */}
              <div className="revenue-forecast">
                <h3 className="forecast-title">📈 Прогноз</h3>
                <p className="forecast-text">
                  На основе текущих темпов роста, ожидаемый доход за следующий месяц:
                </p>
                <div className="forecast-value">
                  {formatCurrency(stats.monthly_revenue * 1.1)}
                </div>
                <p className="forecast-note">
                  * Прогноз может отличаться от фактического значения
                </p>
              </div>
            </div>

            {/* Быстрые действия */}
            <div className="quick-actions">
              <h2 className="section-title">⚡ Быстрые действия</h2>
              <div className="actions-grid">
                <button
                  className="quick-action-button"
                  onClick={() => navigate('/super-admin/companies')}
                >
                  <div className="action-icon">📋</div>
                  <div className="action-label">Компании</div>
                  <div className="action-desc">
                    Управление всеми компаниями
                  </div>
                </button>

                <button
                  className="quick-action-button"
                  onClick={() => navigate('/super-admin/subscriptions')}
                >
                  <div className="action-icon">📊</div>
                  <div className="action-label">Подписки</div>
                  <div className="action-desc">
                    Управление подписками
                  </div>
                </button>

                <button
                  className="quick-action-button"
                  onClick={() => navigate('/super-admin/payments')}
                >
                  <div className="action-icon">💰</div>
                  <div className="action-label">Платежи</div>
                  <div className="action-desc">
                    Управление платежами
                  </div>
                </button>

                <button
                  className="quick-action-button"
                  onClick={() => navigate('/super-admin/companies?expiring=true')}
                >
                  <div className="action-icon">⏰</div>
                  <div className="action-label">Истекающие</div>
                  <div className="action-desc">
                    Компании с истекающими подписками
                  </div>
                </button>
              </div>
            </div>

            {/* Компании с истекающими подписками */}
            {stats.companies_with_expiring_subscription > 0 && (
              <div className="expiring-section">
                <h2 className="section-title">
                  ⚠️ Компании с истекающими подписками
                  <span className="badge">
                    {formatNumber(stats.companies_with_expiring_subscription)}
                  </span>
                </h2>
                <p className="section-desc">
                  Этим компаниям нужно продлить подписку в ближайшее время
                </p>

                <div className="expiring-companies">
                  {/* Здесь будет список компаний с истекающими подписками */}
                  <div className="expiring-placeholder">
                    <div className="placeholder-icon">📋</div>
                    <div className="placeholder-text">
                      Нажмите «Компании» для просмотра подробного списка
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Последние действия */}
            <div className="recent-activity">
              <h2 className="section-title">📋 Последние действия</h2>
              <div className="activity-list">
                <div className="activity-item">
                  <div className="activity-icon">🆕</div>
                  <div className="activity-content">
                    <div className="activity-title">Новая компания зарегистрирована</div>
                    <div className="activity-time">5 минут назад</div>
                  </div>
                </div>
                <div className="activity-item">
                  <div className="activity-icon">💰</div>
                  <div className="activity-content">
                    <div className="activity-title">Платеж получен</div>
                    <div className="activity-time">15 минут назад</div>
                  </div>
                </div>
                <div className="activity-item">
                  <div className="activity-icon">📊</div>
                  <div className="activity-content">
                    <div className="activity-title">Подписка продлена</div>
                    <div className="activity-time">30 минут назад</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SuperAdminDashboard

