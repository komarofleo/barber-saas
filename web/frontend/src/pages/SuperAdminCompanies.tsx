/**
 * Страница управления компаниями
 * 
 * Отображает:
 * - Таблицу компаний с пагинацией
 * - Фильтры (поиск, статус подписки, план)
 * - Детальную информацию о компании
 * - Формы редактирования
 * - Действия (активация/деактивация)
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Company, CompanyFilters, superAdminApi, SubscriptionStatus } from '../api/superAdmin'
import './SuperAdminCompanies.css'

const SuperAdminCompanies: React.FC = () => {
  const navigate = useNavigate()

  // UI состояния
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [showModal, setShowModal] = useState<boolean>(false)
  const [total, setTotal] = useState<number>(0)
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize] = useState<number>(20)

  // Фильтры
  const [filters, setFilters] = useState<CompanyFilters>({
    search: '',
    subscription_status: undefined,
    is_active: undefined,
    plan_id: undefined,
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc' as 'asc' | 'desc',
  })

  // Загрузка компаний
  useEffect(() => {
    fetchCompanies()
  }, [filters])

  const fetchCompanies = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await superAdminApi.getCompanies(filters)
      setCompanies(response.companies)
      setTotal(response.total)
    } catch (err: any) {
      console.error('Ошибка загрузки компаний:', err)
      setError(err.message || 'Не удалось загрузить компании')
    } finally {
      setLoading(false)
    }
  }

  // Обработчик поиска
  const handleSearch = (search: string) => {
    setFilters(prev => ({
      ...prev,
      search,
      page: 1,
    }))
  }

  // Обработчик фильтров
  const handleFilter = (key: keyof CompanyFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1,
    }))
  }

  // Обработчик сортировки
  const handleSort = (sortBy: string) => {
    setFilters(prev => ({
      ...prev,
      sort_by: sortBy,
      sort_order: prev.sort_order === 'asc' ? 'desc' : 'asc',
      page: 1,
    }))
  }

  // Обработчик пагинации
  const handlePageChange = (page: number) => {
    setFilters(prev => ({
      ...prev,
      page,
    }))
  }

  // Обработчик просмотра компании
  const handleViewCompany = (companyId: number) => {
    const company = companies.find(c => c.id === companyId)
    if (company) {
      setSelectedCompany(company)
      setShowModal(true)
    }
  }

  // Обработчик деактивации компании
  const handleDeactivate = async (companyId: number) => {
    if (!confirm('Вы уверены, что хотите деактивировать эту компанию?')) {
      return
    }

    try {
      await superAdminApi.deactivateCompany(companyId)
      // Обновляем список компаний
      await fetchCompanies()
    } catch (err: any) {
      console.error('Ошибка деактивации:', err)
      alert(err.message || 'Не удалось деактивировать компанию')
    }
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

  // Форматирование статуса подписки
  const getStatusBadge = (status: SubscriptionStatus | null): string => {
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
    setSelectedCompany(null)
  }

  return (
    <div className="super-admin-companies-page">
      <div className="companies-container">
        {/* Заголовок страницы */}
        <div className="page-header">
          <h1 className="page-title">🏢 Управление компаниями</h1>
          <p className="page-subtitle">
            Просмотр и управление всеми зарегистрированными автосервисами
          </p>
        </div>

        {/* Панель фильтров */}
        <div className="filters-panel">
          <div className="filter-group">
            <label htmlFor="search" className="filter-label">
              Поиск
            </label>
            <input
              type="text"
              id="search"
              className="filter-input"
              placeholder="Название или email компании"
              value={filters.search}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="subscription_status" className="filter-label">
              Статус подписки
            </label>
            <select
              id="subscription_status"
              className="filter-select"
              value={filters.subscription_status || ''}
              onChange={(e) => handleFilter('subscription_status', e.target.value || undefined)}
            >
              <option value="">Все статусы</option>
              <option value={SubscriptionStatus.ACTIVE}>Активные</option>
              <option value={SubscriptionStatus.EXPIRED}>Истекшие</option>
              <option value={SubscriptionStatus.BLOCKED}>Заблокированные</option>
              <option value={SubscriptionStatus.PENDING}>Ожидающие</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="is_active" className="filter-label">
              Активность
            </label>
            <select
              id="is_active"
              className="filter-select"
              value={filters.is_active === undefined ? '' : String(filters.is_active)}
              onChange={(e) => handleFilter('is_active', e.target.value === '' ? undefined : e.target.value === 'true')}
            >
              <option value="">Все</option>
              <option value="true">Активные</option>
              <option value="false">Неактивные</option>
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
              onChange={(e) => handleFilter('plan_id', e.target.value === '' ? undefined : parseInt(e.target.value))}
            >
              <option value="">Все планы</option>
              <option value="1">Starter</option>
              <option value="2">Basic</option>
              <option value="3">Business</option>
            </select>
          </div>

          <button
            className="filter-reset"
            onClick={() => {
              setFilters({
                search: '',
                subscription_status: undefined,
                is_active: undefined,
                plan_id: undefined,
                page: 1,
                page_size: 20,
                sort_by: 'created_at',
                sort_order: 'desc' as 'asc' | 'desc',
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
            <p>Загрузка компаний...</p>
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <button
              className="retry-button"
              onClick={fetchCompanies}
            >
              Попробовать снова
            </button>
          </div>
        )}

        {/* Таблица компаний */}
        {!loading && !error && companies.length > 0 && (
          <div className="companies-table-wrapper">
            <div className="table-info">
              <p className="table-count">
                Найдено: <strong>{total}</strong> компаний
              </p>
              <p className="table-page">
                Страница <strong>{currentPage}</strong> из {Math.ceil(total / pageSize)}
              </p>
            </div>

            <table className="companies-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Компания</th>
                  <th>Email</th>
                  <th>Телефон</th>
                  <th>План</th>
                  <th>Подписка</th>
                  <th>Записи</th>
                  <th>Активность</th>
                  <th>Создана</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((company) => (
                  <tr key={company.id} className="table-row">
                    <td className="table-cell">
                      <span className="company-id">#{company.id}</span>
                    </td>
                    <td className="table-cell company-cell">
                      <div className="company-name">{company.name}</div>
                    </td>
                    <td className="table-cell">
                      <span className="company-email">{company.email}</span>
                    </td>
                    <td className="table-cell">
                      {company.phone || <span className="no-data">—</span>}
                    </td>
                    <td className="table-cell">
                      {company.plan && (
                        <span className="plan-badge">{company.plan.name}</span>
                      )}
                    </td>
                    <td className="table-cell">
                      <span className={getStatusBadge(company.subscription_status)}>
                        {company.subscription_status || 'Нет'}
                      </span>
                    </td>
                    <td className="table-cell">
                      {company.plan && (
                        <span className="bookings-info">
                          {company.plan.max_bookings_per_month}/мес
                        </span>
                      )}
                    </td>
                    <td className="table-cell">
                      <span className={`active-badge ${company.is_active ? 'active' : 'inactive'}`}>
                        {company.is_active ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="table-cell">
                      {formatDate(company.created_at)}
                    </td>
                    <td className="table-cell actions-cell">
                      <button
                        className="action-button view"
                        onClick={() => handleViewCompany(company.id)}
                        title="Просмотр"
                      >
                        👁
                      </button>
                      <button
                        className={`action-button deactivate ${!company.is_active ? 'disabled' : ''}`}
                        onClick={() => handleDeactivate(company.id)}
                        disabled={company.is_active}
                        title="Деактивировать"
                      >
                        🔒
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Пагинация */}
            {total > pageSize && (
              <div className="pagination">
                <button
                  className="pagination-button"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  ← Назад
                </button>

                <span className="pagination-info">
                  Страница {currentPage} из {Math.ceil(total / pageSize)}
                </span>

                <button
                  className="pagination-button"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= Math.ceil(total / pageSize)}
                >
                  Вперед →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Пустое состояние */}
        {!loading && !error && companies.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🏢</div>
            <h3 className="empty-title">Компании не найдены</h3>
            <p className="empty-description">
              Попробуйте изменить фильтры или сбросить их
            </p>
          </div>
        )}
      </div>

      {/* Модальное окно с деталями компании */}
      {showModal && selectedCompany && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {selectedCompany.name}
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
                <h3 className="section-title">Основная информация</h3>
                <div className="section-content">
                  <div className="info-row">
                    <span className="info-label">ID компании:</span>
                    <span className="info-value">#{selectedCompany.id}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Название:</span>
                    <span className="info-value">{selectedCompany.name}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Email:</span>
                    <span className="info-value">{selectedCompany.email}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Телефон:</span>
                    <span className="info-value">
                      {selectedCompany.phone || 'Не указан'}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Токен бота:</span>
                    <span className="info-value info-value-code">
                      {selectedCompany.telegram_bot_token.substring(0, 50)}...
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Подписка</h3>
                <div className="section-content">
                  {selectedCompany.plan && (
                    <>
                      <div className="info-row">
                        <span className="info-label">Тарифный план:</span>
                        <span className="info-value">{selectedCompany.plan.name}</span>
                      </div>
                      <div className="info-row">
                        <span className="info-label">Стоимость:</span>
                        <span className="info-value">
                          {selectedCompany.plan.price_monthly.toLocaleString('ru-RU')} ₽/мес
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="info-label">Лимит записей:</span>
                        <span className="info-value">
                          {selectedCompany.plan.max_bookings_per_month}/мес
                        </span>
                      </div>
                    </>
                  )}
                  <div className="info-row">
                    <span className="info-label">Статус:</span>
                    <span className={getStatusBadge(selectedCompany.subscription_status)}>
                      {selectedCompany.subscription_status || 'Нет'}
                    </span>
                  </div>
                  {selectedCompany.subscription_end_date && (
                    <div className="info-row">
                      <span className="info-label">Истекает:</span>
                      <span className="info-value">
                        {formatDate(selectedCompany.subscription_end_date)}
                      </span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="info-label">Создание записей:</span>
                    <span className="info-value">
                      {selectedCompany.can_create_bookings ? '✓' : '✗'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Telegram</h3>
                <div className="section-content">
                  <div className="info-row">
                    <span className="info-label">ID владельца:</span>
                    <span className="info-value">
                      {selectedCompany.admin_telegram_id || 'Не указан'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Метаданные</h3>
                <div className="section-content">
                  <div className="info-row">
                    <span className="info-label">Создана:</span>
                    <span className="info-value">
                      {formatDate(selectedCompany.created_at)}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Активна:</span>
                    <span className={`info-value ${selectedCompany.is_active ? 'active' : 'inactive'}`}>
                      {selectedCompany.is_active ? 'Да' : 'Нет'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section subscriptions">
                <h3 className="section-title">Подписки</h3>
                <div className="section-content">
                  {selectedCompany.subscriptions && selectedCompany.subscriptions.length > 0 ? (
                    <div className="subscriptions-list">
                      {selectedCompany.subscriptions.map((sub) => (
                        <div key={sub.id} className="subscription-item">
                          <div className="subscription-info">
                            <div className="subscription-period">
                              {formatDate(sub.start_date)} - {formatDate(sub.end_date)}
                            </div>
                            <span className={getStatusBadge(sub.status)}>
                              {sub.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-data">Нет подписок</p>
                  )}
                </div>
              </div>

              <div className="modal-section payments">
                <h3 className="section-title">Последние платежи</h3>
                <div className="section-content">
                  {selectedCompany.payments && selectedCompany.payments.length > 0 ? (
                    <div className="payments-list">
                      {selectedCompany.payments.slice(0, 5).map((payment) => (
                        <div key={payment.id} className="payment-item">
                          <div className="payment-amount">
                            {payment.amount.toLocaleString('ru-RU')} ₽
                          </div>
                          <div className="payment-info">
                            <div className="payment-status">
                              {payment.status}
                            </div>
                            <div className="payment-date">
                              {formatDate(payment.created_at)}
                            </div>
                          </div>
                        </div>
                      ))}
                      {selectedCompany.payments.length > 5 && (
                        <p className="more-data">
                          ... и еще {selectedCompany.payments.length - 5} платежей
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="no-data">Нет платежей</p>
                  )}
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
              <button
                className="modal-button primary"
                onClick={() => {
                  navigate(`/super-admin/companies/${selectedCompany.id}/edit`)
                }}
              >
                Редактировать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SuperAdminCompanies

