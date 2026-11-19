/**
 * Страница управления подписками
 * 
 * Отображает:
 * - Список всех подписок
 * - Фильтры (поиск, статус, план, дата)
 * - Детальную информацию о подписке
 * - Кнопки действий (продление, отмена)
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Company, Subscription, SubscriptionStatus, superAdminApi } from '../api/superAdmin'
import { useSidebar } from '../components/SuperAdminLayout'
import './SuperAdminSubscriptions.css'
import { formatMoney } from '../utils/money'

const SuperAdminSubscriptions: React.FC = () => {
  const navigate = useNavigate()
  const { sidebarOpen, toggleSidebar } = useSidebar()

  // UI состояния
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSubscription, setSelectedSubscription] = useState<Subscription | null>(null)
  const [showModal, setShowModal] = useState<boolean>(false)

  // Фильтры
  const [filters, setFilters] = useState<{
    search: string
    status: SubscriptionStatus | undefined
    plan_id: number | undefined
    start_date: string
    end_date: string
  }>({
    search: '',
    status: undefined,
    plan_id: undefined,
    start_date: '',
    end_date: '',
  })

  // Загрузка подписок
  useEffect(() => {
    fetchSubscriptions()
  }, [filters])

  const fetchSubscriptions = async () => {
    setLoading(true)
    setError(null)

    try {
      // Получаем все компании и их подписки
      const { companies } = await superAdminApi.getCompanies({ page_size: 100 })
      
      // Собираем все подписки
      const allSubscriptions: Subscription[] = []
      for (const company of companies) {
        for (const sub of company.subscriptions) {
          allSubscriptions.push(sub)
        }
      }

      // Фильтруем подписки
      let filtered = allSubscriptions

      if (filters.search) {
        filtered = filtered.filter(sub =>
          sub.plan.name.toLowerCase().includes(filters.search.toLowerCase())
        )
      }

      if (filters.status) {
        filtered = filtered.filter(sub => sub.status === filters.status)
      }

      if (filters.plan_id) {
        filtered = filtered.filter(sub => sub.plan.id === filters.plan_id)
      }

      if (filters.start_date) {
        filtered = filtered.filter(sub => new Date(sub.start_date) >= new Date(filters.start_date))
      }

      if (filters.end_date) {
        filtered = filtered.filter(sub => new Date(sub.end_date) <= new Date(filters.end_date))
      }

      // Сортируем по дате окончания (сначала истекающие)
      filtered.sort((a, b) => new Date(a.end_date).getTime() - new Date(b.end_date).getTime())

      setSubscriptions(filtered)
    } catch (err: any) {
      console.error('Ошибка загрузки подписок:', err)
      setError(err.message || 'Не удалось загрузить подписки')
    } finally {
      setLoading(false)
    }
  }

  // Обработчик просмотра подписки
  const handleViewSubscription = (subscription: Subscription) => {
    setSelectedSubscription(subscription)
    setShowModal(true)
  }

  // Форматирование даты
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  }

  // Получение дней до истечения
  const getDaysRemaining = (endDate: string): number => {
    const now = new Date()
    const end = new Date(endDate)
    const diff = end.getTime() - now.getTime()
    return Math.ceil(diff / (1000 * 60 * 60 * 24))
  }

  // Форматирование дней до истечения
  const formatDaysRemaining = (endDate: string): string => {
    const days = getDaysRemaining(endDate)
    if (days < 0) {
      return `Истекла ${Math.abs(days)} дн. назад`
    } else if (days === 0) {
      return 'Истекает сегодня'
    } else if (days === 1) {
      return 'Истекает завтра'
    } else if (days <= 7) {
      return `Истекает через ${days} дн.`
    } else {
      return `Осталось ${days} дн.`
    }
  }

  // Форматирование статуса подписки
  const getStatusBadge = (status: SubscriptionStatus): string => {
    switch (status) {
      case SubscriptionStatus.ACTIVE:
        return 'status-badge active'
      case SubscriptionStatus.EXPIRED:
        return 'status-badge expired'
      case SubscriptionStatus.BLOCKED:
        return 'status-badge blocked'
      case SubscriptionStatus.PENDING:
        return 'status-badge pending'
      default:
        return 'status-badge'
    }
  }

  // Обработчик закрытия модального окна
  const handleCloseModal = () => {
    setShowModal(false)
    setSelectedSubscription(null)
  }

  return (
    <div className="super-admin-subscriptions-page">
      {/* Заголовок страницы - вынесен наружу */}
      <div className="page-header">
        <button
          className="dashboard-menu-toggle"
          onClick={toggleSidebar}
          title={sidebarOpen ? 'Свернуть меню' : 'Развернуть меню'}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>
        <div className="header-content">
          <h1 className="page-title">📊 Управление подписками</h1>
          <p className="page-subtitle">
            Просмотр и управление всеми подписками компаний
          </p>
        </div>
      </div>

      {/* Spacer для компенсации fixed header */}
      <div className="header-spacer"></div>

      <div className="subscriptions-container">
        {/* Панель фильтров */}
        <div className="filters-panel">
          <div className="filter-group">
            <label htmlFor="search" className="filter-label">
              Поиск по плану
            </label>
            <input
              type="text"
              id="search"
              className="filter-input"
              placeholder="Название тарифного плана"
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="status" className="filter-label">
              Статус
            </label>
            <select
              id="status"
              className="filter-select"
              value={filters.status || ''}
              onChange={(e) => setFilters(prev => ({ 
                ...prev, 
                status: e.target.value ? e.target.value as SubscriptionStatus : undefined 
              }))}
            >
              <option value="">Все статусы</option>
              <option value={SubscriptionStatus.ACTIVE}>Активные</option>
              <option value={SubscriptionStatus.EXPIRED}>Истекшие</option>
              <option value={SubscriptionStatus.BLOCKED}>Заблокированные</option>
              <option value={SubscriptionStatus.PENDING}>Ожидающие</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="plan_id" className="filter-label">
              Тарифный план
            </label>
            <select
              id="plan_id"
              className="filter-select"
              value={filters.plan_id === undefined ? '' : String(filters.plan_id)}
              onChange={(e) => setFilters(prev => ({
                ...prev,
                plan_id: e.target.value ? parseInt(e.target.value) : undefined
              }))}
            >
              <option value="">Все планы</option>
              <option value="1">Starter</option>
              <option value="2">Basic</option>
              <option value="3">Business</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="start_date" className="filter-label">
              Дата начала
            </label>
            <input
              type="date"
              id="start_date"
              className="filter-input"
              value={filters.start_date}
              onChange={(e) => setFilters(prev => ({ ...prev, start_date: e.target.value }))}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="end_date" className="filter-label">
              Дата окончания
            </label>
            <input
              type="date"
              id="end_date"
              className="filter-input"
              value={filters.end_date}
              onChange={(e) => setFilters(prev => ({ ...prev, end_date: e.target.value }))}
            />
          </div>

          <button
            className="filter-reset"
            onClick={() => {
              setFilters({
                search: '',
                status: undefined,
                plan_id: undefined,
                start_date: '',
                end_date: '',
              })
            }}
          >
            🔄 Сбросить фильтры
          </button>
        </div>

        {/* Загрузка */}
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Загрузка подписок...</p>
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <button
              className="retry-button"
              onClick={fetchSubscriptions}
            >
              Попробовать снова
            </button>
          </div>
        )}

        {/* Список подписок */}
        {!loading && !error && subscriptions.length > 0 && (
          <div className="subscriptions-list-wrapper">
            <div className="table-info">
              <p className="table-count">
                Найдено: <strong>{subscriptions.length}</strong> подписок
              </p>
            </div>

            <div className="subscriptions-grid">
              {subscriptions.map((subscription) => (
                <div key={subscription.id} className="subscription-card">
                  <div className="subscription-header">
                    <div className="subscription-plan">
                      <span className="plan-icon">📋</span>
                      <div className="plan-info">
                        <div className="plan-name">{subscription.plan.name}</div>
                        <div className="plan-price">
                          {formatMoney(subscription.plan.price_monthly)}/мес
                        </div>
                      </div>
                    </div>
                    <span className={getStatusBadge(subscription.status)}>
                      {subscription.status}
                    </span>
                  </div>

                  <div className="subscription-dates">
                    <div className="date-row">
                      <span className="date-label">Начало:</span>
                      <span className="date-value">{formatDate(subscription.start_date)}</span>
                    </div>
                    <div className="date-row">
                      <span className="date-label">Окончание:</span>
                      <span className="date-value">{formatDate(subscription.end_date)}</span>
                    </div>
                  </div>

                  <div className="subscription-footer">
                    <div className="days-remaining">
                      {formatDaysRemaining(subscription.end_date)}
                    </div>
                    <button
                      className="view-button"
                      onClick={() => handleViewSubscription(subscription)}
                    >
                      Подробнее
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Пустое состояние */}
        {!loading && !error && subscriptions.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📊</div>
            <h3 className="empty-title">Подписки не найдены</h3>
            <p className="empty-description">
              Попробуйте изменить фильтры или сбросить их
            </p>
          </div>
        )}
      </div>

      {/* Модальное окно с деталями подписки */}
      {showModal && selectedSubscription && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                Детали подписки
              </h2>
              <button
                className="modal-close"
                onClick={handleCloseModal}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="modal-section">
                <h3 className="section-title">Тарифный план</h3>
                <div className="section-content">
                  <div className="plan-detail">
                    <div className="plan-name-large">{selectedSubscription.plan.name}</div>
                    <div className="plan-prices">
                      <div className="price-item">
                        <span className="price-label">Месяц:</span>
                        <span className="price-value">
                          {formatMoney(selectedSubscription.plan.price_monthly)}
                        </span>
                      </div>
                      <div className="price-item">
                        <span className="price-label">Год:</span>
                        <span className="price-value">
                          {formatMoney(selectedSubscription.plan.price_yearly)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Период действия</h3>
                <div className="section-content">
                  <div className="info-row">
                    <span className="info-label">Дата начала:</span>
                    <span className="info-value">{formatDate(selectedSubscription.start_date)}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Дата окончания:</span>
                    <span className="info-value">{formatDate(selectedSubscription.end_date)}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Статус:</span>
                    <span className={getStatusBadge(selectedSubscription.status)}>
                      {selectedSubscription.status}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Дней до окончания:</span>
                    <span className="info-value highlight">
                      {formatDaysRemaining(selectedSubscription.end_date)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Лимиты плана</h3>
                <div className="section-content">
                  <div className="limits-grid">
                    <div className="limit-item">
                      <span className="limit-icon">📅</span>
                      <span className="limit-label">Записи:</span>
                      <span className="limit-value">
                        {selectedSubscription.plan.max_bookings_per_month}/мес
                      </span>
                    </div>
                    <div className="limit-item">
                      <span className="limit-icon">👥</span>
                      <span className="limit-label">Пользователи:</span>
                      <span className="limit-value">
                        {selectedSubscription.plan.max_users}
                      </span>
                    </div>
                    <div className="limit-item">
                      <span className="limit-icon">👨‍🔧</span>
                      <span className="limit-label">Мастера:</span>
                      <span className="limit-value">
                        {selectedSubscription.plan.max_masters}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Действия</h3>
                <div className="section-content">
                  <div className="actions-grid">
                    <button
                      className="action-card"
                      onClick={() => {
                        // Перейти к компании для продления
                        navigate(`/super-admin/companies/${selectedSubscription.company_id}`)
                      }}
                    >
                      <span className="action-icon">🏢</span>
                      <span className="action-label">Перейти к компании</span>
                    </button>
                    <button
                      className="action-card"
                      onClick={() => {
                        // Создать напоминание (mock)
                        alert('Напоминание отправлено!')
                      }}
                    >
                      <span className="action-icon">📧</span>
                      <span className="action-label">Отправить напоминание</span>
                    </button>
                    <button
                      className="action-card"
                      onClick={() => {
                        // Создать отчет (mock)
                        alert('Отчет создан!')
                      }}
                    >
                      <span className="action-icon">📊</span>
                      <span className="action-label">Создать отчет</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="modal-button secondary"
                onClick={handleCloseModal}
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SuperAdminSubscriptions

