import { useState, useEffect, useMemo } from 'react'
import { useAuth } from '../hooks/useAuth'
import { Plan } from '../api/public'
import { billingApi, BillingPayment, BillingPeriod } from '../api/billing'
import PlanCard from '../components/PlanCard'
import '../components/PlanCard.css'
import './Billing.css'

function Billing() {
  const { subscription, subscriptionLoading, refreshSubscription } = useAuth()
  const [payments, setPayments] = useState<BillingPayment[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly')
  const [paymentLoading, setPaymentLoading] = useState(false)
  const [paymentError, setPaymentError] = useState<string | null>(null)
  const [timeRemaining, setTimeRemaining] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPayments()
    loadPlans()
  }, [])

  const loadPayments = async () => {
    try {
      setLoading(true)
      const response = await billingApi.getPayments()
      setPayments(response)
    } catch (err: any) {
      if (err.response?.status === 404) {
        setPayments([])
        setError(null)
      } else {
        setError(err.message || 'Ошибка загрузки платежей')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadPlans = async () => {
    try {
      const response = await billingApi.getPlans()
      const activePlans = response.filter((plan) => plan.is_active)
      const uniquePlansMap = new Map<string, Plan>()
      activePlans.forEach((plan) => {
        const key = `${plan.name}-${plan.display_order}`
        if (!uniquePlansMap.has(key)) {
          uniquePlansMap.set(key, plan)
        }
      })
      const sortedPlans = Array.from(uniquePlansMap.values()).sort(
        (a, b) => a.display_order - b.display_order
      )
      const limitedPlans = sortedPlans.slice(0, 3)
      setPlans(limitedPlans)
      if (limitedPlans.length > 0 && !selectedPlanId) {
        setSelectedPlanId(limitedPlans[0].id)
      }
    } catch (err: any) {
      setPaymentError(err.message || 'Ошибка загрузки тарифных планов')
    }
  }

  useEffect(() => {
    if (!subscription?.end_date) {
      setTimeRemaining(null)
      return
    }

    const updateTimer = () => {
      const endDate = new Date(subscription.end_date)
      endDate.setHours(23, 59, 59, 999)
      const diffMs = endDate.getTime() - Date.now()

      if (diffMs <= 0) {
        setTimeRemaining('00:00:00')
        return
      }

      const totalSeconds = Math.floor(diffMs / 1000)
      const days = Math.floor(totalSeconds / 86400)
      const hours = Math.floor((totalSeconds % 86400) / 3600)
      const minutes = Math.floor((totalSeconds % 3600) / 60)
      const seconds = totalSeconds % 60

      const formatUnit = (value: number) => value.toString().padStart(2, '0')
      setTimeRemaining(`${days}д ${formatUnit(hours)}:${formatUnit(minutes)}:${formatUnit(seconds)}`)
    }

    updateTimer()
    const interval = window.setInterval(updateTimer, 1000)
    return () => window.clearInterval(interval)
  }, [subscription?.end_date])

  const selectedPlan = useMemo(
    () => plans.find((plan) => plan.id === selectedPlanId) || null,
    [plans, selectedPlanId]
  )

  const handlePayment = async () => {
    if (!selectedPlanId) {
      setPaymentError('Выберите тарифный план')
      return
    }

    try {
      setPaymentLoading(true)
      setPaymentError(null)
      const response = await billingApi.createPayment({
        plan_id: selectedPlanId,
        billing_period: billingPeriod,
      })

      if (response.confirmation_url) {
        window.location.href = response.confirmation_url
        return
      }

      setPaymentError('Не удалось получить ссылку на оплату')
    } catch (err: any) {
      setPaymentError(err.response?.data?.detail || err.message || 'Ошибка создания платежа')
    } finally {
      setPaymentLoading(false)
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
      case 'cancelled':
        return 'Отменено'
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
                <span className="label">Обратный отсчет:</span>
                <span className="value">
                  {timeRemaining || '—'}
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
            <div className="subscription-card-footer subscription-actions">
              <button className="btn-secondary" onClick={refreshSubscription}>
                Обновить статус
              </button>
            </div>
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

      <div className="billing-section">
        <h2>Оплата подписки</h2>
        {plans.length === 0 ? (
          <div className="no-payments">
            <p>Тарифные планы недоступны</p>
            <p className="hint">Попробуйте обновить страницу позже</p>
          </div>
        ) : (
          <div className="billing-plans">
            <div className="plans-grid">
              {plans.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  isSelected={selectedPlanId === plan.id}
                  onSelect={setSelectedPlanId}
                />
              ))}
            </div>
            <div className="billing-controls">
              <div className="billing-period">
                <label className="billing-period-label">Период оплаты</label>
                <div className="billing-period-buttons">
                  <button
                    className={`period-button ${billingPeriod === 'monthly' ? 'active' : ''}`}
                    onClick={() => setBillingPeriod('monthly')}
                  >
                    Ежемесячно
                  </button>
                  <button
                    className={`period-button ${billingPeriod === 'yearly' ? 'active' : ''}`}
                    onClick={() => setBillingPeriod('yearly')}
                  >
                    Ежегодно
                  </button>
                </div>
              </div>
              <div className="billing-summary">
                <div className="summary-row">
                  <span>Тариф:</span>
                  <strong>{selectedPlan?.name || 'Не выбран'}</strong>
                </div>
                <div className="summary-row">
                  <span>Стоимость:</span>
                  <strong>
                    {selectedPlan
                      ? `${(billingPeriod === 'monthly' ? selectedPlan.price_monthly : selectedPlan.price_yearly)
                          .toLocaleString('ru-RU')} ₽`
                      : '—'}
                  </strong>
                </div>
              </div>
              {paymentError && <div className="error">{paymentError}</div>}
              <button className="btn-primary" onClick={handlePayment} disabled={paymentLoading}>
                {paymentLoading ? 'Создаем платеж...' : 'Оплатить подписку'}
              </button>
            </div>
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
                    <td>Юкасса</td>
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
            обратитесь в поддержку: <a href="mailto:support@barber-saas.com">support@barber-saas.com</a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Billing

