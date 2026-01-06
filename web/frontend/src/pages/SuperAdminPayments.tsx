/**
 * Страница управления платежами
 * 
 * Отображает:
 * - Список всех платежей
 * - Фильтры (статус, дата, компания)
 * - Детальную информацию о платеже
 * - Создание ручного платежа
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Company, Payment, PaymentStatus, superAdminApi, ManualPaymentRequest } from '../api/superAdmin'
import './SuperAdminPayments.css'

const SuperAdminPayments: React.FC = () => {
  const navigate = useNavigate()

  // UI состояния
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null)
  const [showModal, setShowModal] = useState<boolean>(false)
  const [showManualPaymentModal, setShowManualPaymentModal] = useState<boolean>(false)

  // Форма ручного платежа
  const [manualPaymentForm, setManualPaymentForm] = useState<ManualPaymentRequest>({
    company_id: 0,
    plan_id: 1,
    amount: 0,
    description: '',
  })

  // Фильтры
  const [filters, setFilters] = useState<{
    status: PaymentStatus | undefined
    start_date: string
    end_date: string
  }>({
    status: undefined,
    start_date: '',
    end_date: '',
  })

  // Загрузка платежей
  useEffect(() => {
    fetchPayments()
  }, [filters])

  const fetchPayments = async () => {
    setLoading(true)
    setError(null)

    try {
      // Получаем все компании и их платежи
      const { companies } = await superAdminApi.getCompanies({ page_size: 100 })
      
      // Собираем все платежи
      const allPayments: Payment[] = []
      for (const company of companies) {
        for (const payment of company.payments) {
          allPayments.push(payment)
        }
      }

      // Фильтруем платежи
      let filtered = allPayments

      if (filters.status) {
        filtered = filtered.filter(payment => payment.status === filters.status)
      }

      if (filters.start_date) {
        filtered = filtered.filter(payment => new Date(payment.created_at) >= new Date(filters.start_date))
      }

      if (filters.end_date) {
        filtered = filtered.filter(payment => new Date(payment.created_at) <= new Date(filters.end_date))
      }

      // Сортируем по дате создания (сначала новые)
      filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

      setPayments(filtered)
    } catch (err: any) {
      console.error('Ошибка загрузки платежей:', err)
      setError(err.message || 'Не удалось загрузить платежи')
    } finally {
      setLoading(false)
    }
  }

  // Обработчик просмотра платежа
  const handleViewPayment = (payment: Payment) => {
    setSelectedPayment(payment)
    setShowModal(true)
  }

  // Обработчик создания ручного платежа
  const handleCreateManualPayment = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!manualPaymentForm.company_id || manualPaymentForm.amount <= 0) {
      alert('Пожалуйста, заполните все поля')
      return
    }

    try {
      await superAdminApi.createManualPayment(manualPaymentForm)
      alert('Платеж успешно создан!')
      setShowManualPaymentModal(false)
      setManualPaymentForm({
        company_id: 0,
        plan_id: 1,
        amount: 0,
        description: '',
      })
      // Обновляем список платежей
      await fetchPayments()
    } catch (err: any) {
      console.error('Ошибка создания платежа:', err)
      alert(err.message || 'Не удалось создать платеж')
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

  // Форматирование даты и времени
  const formatDateTime = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
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

  // Форматирование статуса платежа
  const getStatusBadge = (status: PaymentStatus): string => {
    switch (status) {
      case PaymentStatus.COMPLETED:
        return 'status-badge completed'
      case PaymentStatus.FAILED:
        return 'status-badge failed'
      case PaymentStatus.PENDING:
        return 'status-badge pending'
      case PaymentStatus.REFUNDED:
        return 'status-badge refunded'
      default:
        return 'status-badge'
    }
  }

  // Обработчик закрытия модального окна
  const handleCloseModal = () => {
    setShowModal(false)
    setSelectedPayment(null)
  }

  // Обработчик закрытия модального окна ручного платежа
  const handleCloseManualPaymentModal = () => {
    setShowManualPaymentModal(false)
    setManualPaymentForm({
      company_id: 0,
      plan_id: 1,
      amount: 0,
      description: '',
    })
  }

  return (
    <div className="super-admin-payments-page">
      <div className="payments-container">
        {/* Заголовок страницы */}
        <div className="page-header">
          <h1 className="page-title">💰 Управление платежами</h1>
          <p className="page-subtitle">
            Просмотр и управление всеми платежами в системе
          </p>
        </div>

        {/* Кнопка создания платежа - перемещена из header внутрь контента */}
        <div className="page-actions">
          <button
            className="create-payment-button"
            onClick={() => setShowManualPaymentModal(true)}
          >
            ➕ Создать ручной платеж
          </button>
        </div>

        {/* Панель фильтров */}
        <div className="filters-panel">
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
                status: e.target.value ? e.target.value as PaymentStatus : undefined 
              }))}
            >
              <option value="">Все статусы</option>
              <option value={PaymentStatus.COMPLETED}>Успешные</option>
              <option value={PaymentStatus.FAILED}>Неудачные</option>
              <option value={PaymentStatus.PENDING}>Ожидающие</option>
              <option value={PaymentStatus.REFUNDED}>Возвращенные</option>
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
                status: undefined,
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
            <p>Загрузка платежей...</p>
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <button
              className="retry-button"
              onClick={fetchPayments}
            >
              Попробовать снова
            </button>
          </div>
        )}

        {/* Таблица платежей */}
        {!loading && !error && payments.length > 0 && (
          <div className="payments-table-wrapper">
            <div className="table-info">
              <p className="table-count">
                Найдено: <strong>{payments.length}</strong> платежей
              </p>
            </div>

            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>ID Юкассы</th>
                  <th>Компания</th>
                  <th>План</th>
                  <th>Сумма</th>
                  <th>Статус</th>
                  <th>Описание</th>
                  <th>Дата создания</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id} className="table-row">
                    <td className="table-cell">
                      <span className="payment-id">#{payment.id}</span>
                    </td>
                    <td className="table-cell">
                      <span className="yookassa-id">
                        {payment.yookassa_payment_id}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="company-id">
                        {payment.company_id ? `#${payment.company_id}` : '—'}
                      </span>
                    </td>
                    <td className="table-cell">
                      #{payment.plan_id}
                    </td>
                    <td className="table-cell">
                      <span className="payment-amount">
                        {formatCurrency(payment.amount)}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className={getStatusBadge(payment.status)}>
                        {payment.status}
                      </span>
                    </td>
                    <td className="table-cell">
                      {payment.description || '—'}
                    </td>
                    <td className="table-cell">
                      {formatDateTime(payment.created_at)}
                    </td>
                    <td className="table-cell actions-cell">
                      <button
                        className="action-button view"
                        onClick={() => handleViewPayment(payment)}
                        title="Просмотр"
                      >
                        👁
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Пустое состояние */}
        {!loading && !error && payments.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">💰</div>
            <h3 className="empty-title">Платежи не найдены</h3>
            <p className="empty-description">
              Попробуйте изменить фильтры или сбросить их
            </p>
          </div>
        )}
      </div>

      {/* Модальное окно с деталями платежа */}
      {showModal && selectedPayment && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                Детали платежа
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
                    <span className="info-label">ID платежа:</span>
                    <span className="info-value">#{selectedPayment.id}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">ID платежа Юкассы:</span>
                    <span className="info-value info-value-code">
                      {selectedPayment.yookassa_payment_id}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Компания:</span>
                    <span className="info-value">
                      {selectedPayment.company_id ? `#${selectedPayment.company_id}` : '—'}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Тарифный план:</span>
                    <span className="info-value">#{selectedPayment.plan_id}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Сумма:</span>
                    <span className="info-value highlight">
                      {formatCurrency(selectedPayment.amount)}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Валюта:</span>
                    <span className="info-value">
                      {selectedPayment.currency}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Статус</h3>
                <div className="section-content">
                  <div className="info-row">
                    <span className="info-label">Статус:</span>
                    <span className={getStatusBadge(selectedPayment.status)}>
                      {selectedPayment.status}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Статус Юкассы:</span>
                    <span className="info-value">
                      {selectedPayment.yookassa_payment_status || '—'}
                    </span>
                  </div>
                  {selectedPayment.webhook_received_at && (
                    <div className="info-row">
                      <span className="info-label">Webhook получен:</span>
                      <span className="info-value">
                        {formatDateTime(selectedPayment.webhook_received_at)}
                      </span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="info-label">Подпись верифицирована:</span>
                    <span className="info-value">
                      {selectedPayment.webhook_signature_verified ? '✓' : '✗'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-section">
                <h3 className="section-title">Дополнительная информация</h3>
                <div className="section-content">
                  <div className="info-row">
                    <span className="info-label">Описание:</span>
                    <span className="info-value">
                      {selectedPayment.description || 'Не указано'}
                    </span>
                  </div>
                  {selectedPayment.yookassa_confirmation_url && (
                    <div className="info-row">
                      <span className="info-label">Ссылка на оплату:</span>
                      <span className="info-value info-value-code">
                        {selectedPayment.yookassa_confirmation_url.substring(0, 50)}...
                      </span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="info-label">Создан:</span>
                    <span className="info-value">
                      {formatDateTime(selectedPayment.created_at)}
                    </span>
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

      {/* Модальное окно создания ручного платежа */}
      {showManualPaymentModal && (
        <div className="modal-overlay" onClick={handleCloseManualPaymentModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                Создать ручной платеж
              </h2>
              <button
                className="modal-close"
                onClick={handleCloseManualPaymentModal}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <form onSubmit={handleCreateManualPayment}>
                <div className="form-group">
                  <label htmlFor="company_id" className="form-label">
                    ID компании *
                  </label>
                  <input
                    type="number"
                    id="company_id"
                    className="form-input"
                    placeholder="1"
                    value={manualPaymentForm.company_id || ''}
                    onChange={(e) => setManualPaymentForm(prev => ({
                      ...prev,
                      company_id: parseInt(e.target.value) || 0
                    }))}
                    required
                  />
                  <p className="form-hint">Введите ID компании</p>
                </div>

                <div className="form-group">
                  <label htmlFor="plan_id" className="form-label">
                    Тарифный план *
                  </label>
                  <select
                    id="plan_id"
                    className="form-select"
                    value={manualPaymentForm.plan_id}
                    onChange={(e) => setManualPaymentForm(prev => ({
                      ...prev,
                      plan_id: parseInt(e.target.value)
                    }))}
                    required
                  >
                    <option value="1">Starter</option>
                    <option value="2">Basic</option>
                    <option value="3">Business</option>
                  </select>
                  <p className="form-hint">Выберите тарифный план</p>
                </div>

                <div className="form-group">
                  <label htmlFor="amount" className="form-label">
                    Сумма (₽) *
                  </label>
                  <input
                    type="number"
                    id="amount"
                    className="form-input"
                    placeholder="5000"
                    min="0"
                    step="100"
                    value={manualPaymentForm.amount || ''}
                    onChange={(e) => setManualPaymentForm(prev => ({
                      ...prev,
                      amount: parseFloat(e.target.value) || 0
                    }))}
                    required
                  />
                  <p className="form-hint">Введите сумму платежа в рублях</p>
                </div>

                <div className="form-group">
                  <label htmlFor="description" className="form-label">
                    Описание *
                  </label>
                  <input
                    type="text"
                    id="description"
                    className="form-input"
                    placeholder="Ручное продление подписки"
                    value={manualPaymentForm.description}
                    onChange={(e) => setManualPaymentForm(prev => ({
                      ...prev,
                      description: e.target.value
                    }))}
                    required
                  />
                  <p className="form-hint">Опишите назначение платежа</p>
                </div>

                <div className="form-actions">
                  <button
                    type="button"
                    className="form-button secondary"
                    onClick={handleCloseManualPaymentModal}
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="form-button primary"
                  >
                    Создать платеж
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SuperAdminPayments

