import { useAuth } from '../hooks/useAuth'
import './SubscriptionBarrier.css'

interface SubscriptionBarrierProps {
  children: React.ReactNode
  fallback?: React.ReactNode
  silent?: boolean
}

/**
 * Компонент для блокировки контента при истекшей подписке.
 * Если подписка активна, показывает children.
 * Если подписка истекла, показывает fallback или сообщение об ошибке.
 */
function SubscriptionBarrier({
  children,
  fallback,
  silent = false
}: SubscriptionBarrierProps) {
  const { subscription, subscriptionLoading, canCreateBookings } = useAuth()

  // Загрузка
  if (subscriptionLoading) {
    if (silent) {
      return <>{children}</>
    }
    return (
      <div className="subscription-barrier-loading">
        <div className="loading-spinner"></div>
        <p>Проверка подписки...</p>
      </div>
    )
  }

  // Подписка активна - показываем контент
  if (canCreateBookings) {
    return <>{children}</>
  }

  // Подписка неактивна - показываем fallback или сообщение об ошибке
  if (fallback) {
    return <>{fallback}</>
  }

  return (
    <div className="subscription-barrier">
      <div className="subscription-barrier-content">
        <div className="barrier-icon">🔒</div>
        <h2 className="barrier-title">Подписка неактивна</h2>
        <p className="barrier-description">
          Для выполнения этого действия необходима активная подписка.
        </p>
        
        {subscription && (
          <div className="barrier-info">
            <div className="barrier-info-item">
              <span className="info-label">Текущий план:</span>
              <span className="info-value">{subscription.plan_name}</span>
            </div>
            <div className="barrier-info-item">
              <span className="info-label">Статус:</span>
              <span className="info-value info-status">
                {subscription.status === 'expired' && 'Истекла'}
                {subscription.status === 'blocked' && 'Заблокирована'}
                {subscription.status === 'cancelled' && 'Отменена'}
                {subscription.status === 'active' && 'Активна'}
              </span>
            </div>
            <div className="barrier-info-item">
              <span className="info-label">Дата окончания:</span>
              <span className="info-value">
                {new Date(subscription.end_date).toLocaleDateString('ru-RU', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric'
                })}
              </span>
            </div>
          </div>
        )}
        
        <div className="barrier-actions">
          <a href="/register" className="barrier-btn primary">
            <span>💳</span>
            Продлить подписку
          </a>
          <button
            className="barrier-btn secondary"
            onClick={() => window.history.back()}
          >
            <span>←</span>
            Вернуться назад
          </button>
        </div>
        
        <div className="barrier-support">
          <p>
            Нужна помощь? <a href="mailto:support@autoservice-saas.com">Свяжитесь с нами</a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default SubscriptionBarrier

