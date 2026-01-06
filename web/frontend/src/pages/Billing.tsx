import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/auth'
import './Billing.css'

interface Payment {
  id: number
  amount: number
  currency: string
  status: string
  payment_method: string
  created_at: string
  yookassa_payment_id: string | null
}

function Billing() {
  const { subscription, subscriptionLoading, refreshSubscription } = useAuth()
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPayments()
  }, [])

  const loadPayments = async () => {
    try {
      setLoading(true)
      // TODO: Загрузить платежи через API
      // const response = await billingApi.getPayments()
      // setPayments(response.payments)
      setPayments([])
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки платежей')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'succeeded':
        return '#10b981'
      case 'pending':
        return '#f59e0b'
      case 'failed':
        return '#ef4444'
      default:
        return '#6b7280'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'succeeded':
        return 'Оплачено'
      case 'pending':
        return 'Ожидает оплаты'
      case 'failed':
        return 'Ошибка оплаты'
      default:
        return status
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (subscriptionLoading) {
    return (
      <div className="billing-container">
        <div className="loading">Загрузка информации о подписке...</div>
      </div>
    )
  }

  return (
    <div className="billing-container">
      <div className="billing-header">
        <h1>💳 Биллинг и подписка</h1>
        <p>Управление подпиской и платежами</p>
      </div>

      {/* Текущая подписка */}
      <div className="billing-section">
        <h2>Текущая подписка</h2>
        {subscription ? (
          <div className="subscription-card">
            <div className="subscription-card-header">
              <div>
                <h3>{subscription.plan_name}</h3>
                <span
                  className="subscription-status-badge"
                  style={{ color: getStatusColor(subscription.status) }}
                >
                  {subscription.status === 'active' ? 'Активна' : 
                   subscription.status === 'expired' ? 'Истекла' :
                   subscription.status === 'blocked' ? 'Заблокирована' : 'Отменена'}
                </span>
              </div>
            </div>
            <div className="subscription-card-body">
              <div className="subscription-info-row">
                <span className="label">Дата начала:</span>
                <span className="value">
                  {new Date(subscription.start_date).toLocaleDateString('ru-RU')}
                </span>
              </div>
              <div className="subscription-info-row">
                <span className="label">Дата окончания:</span>
                <span className="value">
                  {new Date(subscription.end_date).toLocaleDateString('ru-RU')}
                </span>
              </div>
              <div className="subscription-info-row">
                <span className="label">Осталось дней:</span>
                <span className="value">
                  {subscription.days_remaining > 0 ? subscription.days_remaining : 0}
                </span>
              </div>
            </div>
            {subscription.status === 'expired' && (
              <div className="subscription-card-footer">
                <a href="/register" className="btn-primary">
                  Продлить подписку
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="no-subscription">
            <p>У вас нет активной подписки</p>
            <a href="/register" className="btn-primary">
              Оформить подписку
            </a>
          </div>
        )}
      </div>

      {/* История платежей */}
      <div className="billing-section">
        <h2>История платежей</h2>
        {loading ? (
          <div className="loading">Загрузка платежей...</div>
        ) : error ? (
          <div className="error">{error}</div>
        ) : payments.length === 0 ? (
          <div className="no-payments">
            <p>Платежей пока нет</p>
            <p className="hint">После оплаты подписки здесь появится история платежей</p>
          </div>
        ) : (
          <div className="payments-table">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Сумма</th>
                  <th>Способ оплаты</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{formatDate(payment.created_at)}</td>
                    <td>{payment.amount} {payment.currency}</td>
                    <td>{payment.payment_method}</td>
                    <td>
                      <span
                        className="status-badge"
                        style={{ color: getStatusColor(payment.status) }}
                      >
                        {getStatusText(payment.status)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Информация */}
      <div className="billing-section">
        <h2>Информация</h2>
        <div className="info-card">
          <h3>Как продлить подписку?</h3>
          <ol>
            <li>Нажмите кнопку "Продлить подписку"</li>
            <li>Выберите тарифный план</li>
            <li>Оплатите через Юкассу</li>
            <li>Подписка будет автоматически продлена после оплаты</li>
          </ol>
        </div>
        <div className="info-card">
          <h3>Нужна помощь?</h3>
          <p>
            Если у вас возникли вопросы по подписке или платежам, 
            обратитесь в поддержку: <a href="mailto:support@autoservice-saas.com">support@autoservice-saas.com</a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Billing

