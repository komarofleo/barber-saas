/**
 * Страница деталей компании
 * 
 * Отображает:
 * - Информацию о компании
 * - Текущую подписку
 * - Историю подписок
 * - Историю платежей
 * - Управление компанией (активация/деактивация)
 */

import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Company, Subscription, Payment, SubscriptionStatus, PaymentStatus, superAdminApi } from '../api/superAdmin'
import { useSidebar } from '../components/SuperAdminLayout'
import './SuperAdminCompanies.css'

const SuperAdminCompanyDetails: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const companyId = parseInt(id)
  const { sidebarOpen, toggleSidebar } = useSidebar()
  
  // UI состояния
  const [company, setCompany] = useState<Company | null>(null)
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [showActivateModal, setShowActivateModal] = useState(false)
  const [showDeactivateModal, setShowDeactivateModal] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  
  // Загрузка данных компании
  useEffect(() => {
    loadCompanyData()
  }, [companyId])
  
  const loadCompanyData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Загружаем детали компании
      const fetchedCompany = await superAdminApi.getCompanyById(companyId)
      setCompany(fetchedCompany)
      
      // Загружаем подписки
      const fetchedSubscriptions = await superAdminApi.getCompanySubscriptions(companyId)
      setSubscriptions(fetchedSubscriptions)
      
      // Загружаем платежи
      const fetchedPayments = await superAdminApi.getCompanyPayments(companyId)
      setPayments(fetchedPayments)
      
    } catch (err: any) {
      console.error('Ошибка загрузки данных компании:', err)
      setError(err.response?.data?.detail || 'Не удалось загрузить данные компании')
    } finally {
      setLoading(false)
    }
  }
  
  // Форматирование даты
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return dateString
    }
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
  
  // Получение цвета статуса подписки
  const getSubscriptionStatusColor = (status: SubscriptionStatus): string => {
    switch (status) {
      case 'active':
        return '#10b981'
      case 'expired':
        return '#ef4444'
      case 'blocked':
        return '#dc2626'
      case 'pending':
        return '#f59e0b'
      default:
        return '#6b7280'
    }
  }
  
  // Получение цвета статуса платежа
  const getPaymentStatusColor = (status: PaymentStatus): string => {
    switch (status) {
      case 'pending':
        return '#f59e0b'
      case 'succeeded':
        return '#10b981'
      case 'failed':
        return '#ef4444'
      case 'cancelled':
        return '#dc2626'
      case 'refunded':
        return '#6b7280'
      default:
        return '#6b7280'
    }
  }
  
  // Получение статуса подписки текстом
  const getSubscriptionStatusText = (status: SubscriptionStatus): string => {
    switch (status) {
      case 'active':
        return '✅ Активна'
      case 'expired':
        return '❌ Истекла'
      case 'blocked':
        return '🚫 Заблокирована'
      case 'pending':
        return '⏳ В ожидании'
      default:
        return '❓ Неизвестно'
    }
  }
  
  // Получение статуса платежа текстом
  const getPaymentStatusText = (status: PaymentStatus): string => {
    switch (status) {
      case 'pending':
        return '⏳ Ожидает'
      case 'succeeded':
        return '✅ Успешен'
      case 'failed':
        return '❌ Неуспешен'
      case 'cancelled':
        return '🚫 Отменен'
      case 'refunded':
        return '↩️ Возврат'
      default:
        return '❓ Неизвестно'
    }
  }
  
  // Обработчик активации компании
  const handleActivate = async () => {
    setActionLoading(true)
    try {
      await superAdminApi.activateCompany(companyId)
      await loadCompanyData()
      setShowActivateModal(false)
    } catch (err: any) {
      console.error('Ошибка активации компании:', err)
      alert('Не удалось активировать компанию')
    } finally {
      setActionLoading(false)
    }
  }
  
  // Обработчик деактивации компании
  const handleDeactivate = async () => {
    setActionLoading(true)
    try {
      await superAdminApi.deactivateCompany(companyId)
      await loadCompanyData()
      setShowDeactivateModal(false)
    } catch (err: any) {
      console.error('Ошибка деактивации компании:', err)
      alert('Не удалось деактивировать компанию')
    } finally {
      setActionLoading(false)
    }
  }
  
  // Обработчик перезапуска бота
  const handleRestartBot = async () => {
    setActionLoading(true)
    try {
      await fetch(`http://localhost:8000/api/bot-manager/restart/${companyId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('super_admin_token')}`,
        },
      })
      alert('Бот перезапущен')
    } catch (err: any) {
      console.error('Ошибка перезапуска бота:', err)
      alert('Не удалось перезапустить бота')
    } finally {
      setActionLoading(false)
    }
  }
  
  if (loading) {
    return (
      <div className="super-admin-companies">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Загрузка данных...</p>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="super-admin-companies">
        <div className="error-container">
          <h2>❌ Ошибка</h2>
          <p>{error}</p>
          <button onClick={() => loadCompanyData()} className="retry-button">
            🔄 Попробовать снова
          </button>
        </div>
      </div>
    )
  }
  
  if (!company) {
    return null
  }
  
  const currentSubscription = subscriptions[0] // Текущая подписка (первая)
  const daysUntilExpiration = currentSubscription?.end_date
    ? Math.ceil((new Date(currentSubscription.end_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
    : null
  
  return (
    <div className="super-admin-companies">
      {/* Кнопка возврата */}
      <div className="back-navigation">
        <button onClick={() => navigate('/super-admin/companies')} className="back-button">
          ← Вернуться к списку компаний
        </button>
      </div>
      
      {/* Заголовок страницы */}
      <div className="company-details-header">
        <button
          className="dashboard-menu-toggle"
          onClick={toggleSidebar}
          title={sidebarOpen ? 'Свернуть меню' : 'Развернуть меню'}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>
        <div className="header-content">
          <h1 className="page-title">
            🏢 {company.name}
          </h1>
        </div>
        <p className="company-email">{company.email}</p>
        <p className="company-phone">
          {company.phone || 'Телефон не указан'}
        </p>
      </div>
      
      {/* Карточки информации */}
      <div className="company-info-cards">
        {/* Карточка компании */}
        <div className="info-card">
          <h3 className="info-card-title">📊 Информация о компании</h3>
          <div className="info-card-content">
            <div className="info-row">
              <span className="info-label">ID:</span>
              <span className="info-value">{company.id}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Статус:</span>
              <span className={`info-value ${company.is_active ? 'active' : 'inactive'}`}>
                {company.is_active ? '✅ Активна' : '❌ Неактивна'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">Дата создания:</span>
              <span className="info-value">{formatDate(company.created_at)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Telegram ID админа:</span>
              <span className="info-value">{company.admin_telegram_id || 'Не указан'}</span>
            </div>
          </div>
        </div>
        
        {/* Карточка подписки */}
        {currentSubscription && (
          <div className="info-card">
            <h3 className="info-card-title">📋 Текущая подписка</h3>
            <div className="info-card-content">
              <div className="info-row">
                <span className="info-label">Статус:</span>
                <span
                  className="info-value"
                  style={{ color: getSubscriptionStatusColor(currentSubscription.status) }}
                >
                  {getSubscriptionStatusText(currentSubscription.status)}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Тариф:</span>
                <span className="info-value">{currentSubscription.plan?.name || 'Неизвестно'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Цена:</span>
                <span className="info-value">{formatCurrency(currentSubscription.plan?.price_monthly || 0)}/мес</span>
              </div>
              <div className="info-row">
                <span className="info-label">Начало:</span>
                <span className="info-value">{formatDate(currentSubscription.start_date)}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Окончание:</span>
                <span className="info-value">{formatDate(currentSubscription.end_date)}</span>
              </div>
              {daysUntilExpiration !== null && (
                <div className="info-row">
                  <span className="info-label">Дней до окончания:</span>
                  <span
                    className={`info-value ${daysUntilExpiration <= 7 ? 'warning' : ''}`}
                  >
                    {daysUntilExpiration} дней
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Карточка бота */}
        <div className="info-card">
          <h3 className="info-card-title">🤖 Бот</h3>
          <div className="info-card-content">
            <div className="info-row">
              <span className="info-label">Статус:</span>
              <span className={`info-value ${company.is_active ? 'active' : 'inactive'}`}>
                {company.is_active ? '✅ Работает' : '❌ Остановлен'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">Создание записей:</span>
              <span className={`info-value ${company.can_create_bookings ? 'enabled' : 'disabled'}`}>
                {company.can_create_bookings ? '✅ Разрешено' : '❌ Заблокировано'}
              </span>
            </div>
            {company.is_active && (
              <button
                onClick={handleRestartBot}
                disabled={actionLoading}
                className="action-button"
              >
                🔄 Перезапустить бота
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Кнопки управления */}
      <div className="company-actions">
        {company.is_active ? (
          <button
            onClick={() => setShowDeactivateModal(true)}
            disabled={actionLoading}
            className="action-button danger"
          >
            🚫 Деактивировать компанию
          </button>
        ) : (
          <button
            onClick={() => setShowActivateModal(true)}
            disabled={actionLoading}
            className="action-button success"
          >
            ✅ Активировать компанию
          </button>
        )}
      </div>
      
      {/* История подписок */}
      <div className="subscriptions-section">
        <h2 className="section-title">📋 История подписок</h2>
        {subscriptions.length === 0 ? (
          <p className="no-data">Нет подписок</p>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Тариф</th>
                  <th>Статус</th>
                  <th>Начало</th>
                  <th>Окончание</th>
                </tr>
              </thead>
              <tbody>
                {subscriptions.map((sub) => (
                  <tr key={sub.id}>
                    <td>{sub.id}</td>
                    <td>{sub.plan?.name || '-'}</td>
                    <td>
                      <span
                        style={{ color: getSubscriptionStatusColor(sub.status as SubscriptionStatus) }}
                      >
                        {getSubscriptionStatusText(sub.status as SubscriptionStatus)}
                      </span>
                    </td>
                    <td>{formatDate(sub.start_date)}</td>
                    <td>{formatDate(sub.end_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* История платежей */}
      <div className="payments-section">
        <h2 className="section-title">💰 История платежей</h2>
        {payments.length === 0 ? (
          <p className="no-data">Нет платежей</p>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Тариф</th>
                  <th>Сумма</th>
                  <th>Статус</th>
                  <th>Дата</th>
                  <th>Описание</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{payment.id}</td>
                    <td>{payment.plan_id}</td>
                    <td>{formatCurrency(payment.amount)}</td>
                    <td>
                      <span
                        style={{ color: getPaymentStatusColor(payment.status as PaymentStatus) }}
                      >
                        {getPaymentStatusText(payment.status as PaymentStatus)}
                      </span>
                    </td>
                    <td>{formatDate(payment.created_at)}</td>
                    <td>{payment.description || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* Модальное окно активации */}
      {showActivateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Подтверждение активации</h2>
            <p>Вы уверены, что хотите активировать компанию "{company.name}"?</p>
            <div className="modal-actions">
              <button
                onClick={handleActivate}
                disabled={actionLoading}
                className="modal-button success"
              >
                ✅ Активировать
              </button>
              <button
                onClick={() => setShowActivateModal(false)}
                className="modal-button secondary"
                disabled={actionLoading}
              >
                ❌ Отмена
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Модальное окно деактивации */}
      {showDeactivateModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Подтверждение деактивации</h2>
            <p>Вы уверены, что хотите деактивировать компанию "{company.name}"?</p>
            <p className="warning-text">⚠️ После деактивации компания перестанет работать и создавать записи!</p>
            <div className="modal-actions">
              <button
                onClick={handleDeactivate}
                disabled={actionLoading}
                className="modal-button danger"
              >
                🚫 Деактивировать
              </button>
              <button
                onClick={() => setShowDeactivateModal(false)}
                className="modal-button secondary"
                disabled={actionLoading}
              >
                ❌ Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SuperAdminCompanyDetails

