import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useState, useEffect } from 'react'
import './Sidebar.css'

function Sidebar() {
  const location = useLocation()
  const { user, logout, subscription, subscriptionLoading, canCreateBookings } = useAuth()
  const [showSubscriptionWarning, setShowSubscriptionWarning] = useState(false)

  // Показываем предупреждение при истекшей подписке
  useEffect(() => {
    if (subscription && !subscriptionLoading && !canCreateBookings) {
      setShowSubscriptionWarning(true)
    } else {
      setShowSubscriptionWarning(false)
    }
  }, [subscription, subscriptionLoading, canCreateBookings])

  const menuItems = [
    { path: '/', icon: '📊', label: 'Дашборд' },
    { path: '/bookings', icon: '📋', label: 'Записи', requiresSubscription: true },
    { path: '/calendar', icon: '📅', label: 'Календарь', requiresSubscription: true },
    { path: '/clients', icon: '👤', label: 'Клиенты' },
    { path: '/users', icon: '👥', label: 'Пользователи', adminOnly: true },
    { path: '/services', icon: '🔧', label: 'Услуги' },
    { path: '/masters', icon: '👨‍🔧', label: 'Мастера' },
    { path: '/posts', icon: '🛠️', label: 'Посты' },
    { path: '/blocks', icon: '🚫', label: 'Блокировки' },
    { path: '/promocodes', icon: '🎟️', label: 'Промокоды' },
    { path: '/promotions', icon: '🎁', label: 'Акции' },
    { path: '/broadcasts', icon: '📢', label: 'Рассылки' },
    { path: '/statistics', icon: '📈', label: 'Статистика' },
    { path: '/settings', icon: '⚙️', label: 'Настройки' },
  ]

  const getSubscriptionStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#10b981' // green
      case 'expired':
        return '#ef4444' // red
      case 'blocked':
        return '#f59e0b' // orange
      case 'cancelled':
        return '#6b7280' // gray
      default:
        return '#6b7280'
    }
  }

  const getSubscriptionStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return 'Активна'
      case 'expired':
        return 'Истекла'
      case 'blocked':
        return 'Заблокирована'
      case 'cancelled':
        return 'Отменена'
      default:
        return 'Неизвестно'
    }
  }

  const getSubscriptionDateInfo = () => {
    if (!subscription || subscriptionLoading) {
      return null
    }

    const endDate = new Date(subscription.end_date)
    const today = new Date()
    const diffDays = Math.ceil((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

    if (diffDays <= 0) {
      return 'Подписка истекла'
    } else if (diffDays === 1) {
      return 'Завтра истекает'
    } else if (diffDays <= 7) {
      return `Истекает через ${diffDays} дн.`
    } else {
      return `Истекает через ${diffDays} дн.`
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>AutoService</h2>
        <div className="user-info">
          <span className="user-name">{user?.first_name || user?.telegram_id}</span>
          {user?.is_admin && <span className="user-role">Администратор</span>}
        </div>
      </div>

      {/* Информация о подписке */}
      {subscription && !subscriptionLoading && (
        <div className="subscription-info">
          <div className="subscription-header">
            <span className="subscription-label">Подписка</span>
            <span
              className="subscription-status"
              style={{ color: getSubscriptionStatusColor(subscription.status) }}
            >
              {getSubscriptionStatusText(subscription.status)}
            </span>
          </div>
          <div className="subscription-details">
            <div className="subscription-plan">{subscription.plan_name}</div>
            <div className="subscription-date">{getSubscriptionDateInfo()}</div>
          </div>
          {subscription.status === 'expired' && (
            <a href="/register" className="subscription-renew-link">
              Продлить подписку
            </a>
          )}
        </div>
      )}

      {/* Предупреждение об истекшей подписке */}
      {showSubscriptionWarning && (
        <div className="subscription-warning">
          <div className="warning-content">
            <span className="warning-icon">⚠️</span>
            <div className="warning-text">
              <strong>Подписка неактивна</strong>
              <p>Невозможно создавать записи</p>
            </div>
          </div>
          <a href="/register" className="warning-action">
            Продлить подписку
          </a>
        </div>
      )}

      <nav className="sidebar-nav">
        <ul className="nav-list">
          {menuItems
            .filter((item) => !item.adminOnly || user?.is_admin)
            .map((item) => {
              // Блокируем пункты меню, которые требуют активной подписки
              const isBlocked =
                item.requiresSubscription &&
                subscription &&
                !subscriptionLoading &&
                !canCreateBookings

              return (
                <li key={item.path}>
                  {isBlocked ? (
                    <div className="nav-link disabled">
                      <span className="nav-icon">{item.icon}</span>
                      <span className="nav-label">{item.label}</span>
                      <span className="nav-lock">🔒</span>
                    </div>
                  ) : (
                    <Link
                      to={item.path}
                      className={`nav-link ${
                        location.pathname === item.path ? 'active' : ''
                      }`}
                    >
                      <span className="nav-icon">{item.icon}</span>
                      <span className="nav-label">{item.label}</span>
                    </Link>
                  )}
                </li>
              )
            })}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <button onClick={logout} className="logout-btn">
          <span>🚪</span>
          <span>Выход</span>
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
