import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useState, useEffect } from 'react'
import { settingsApi } from '../api/settings'
import './Sidebar.css'

interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const location = useLocation()
  const { user, logout, subscription, subscriptionLoading, canCreateBookings } = useAuth()
  const [showSubscriptionWarning, setShowSubscriptionWarning] = useState(false)
  const [companyName, setCompanyName] = useState('')

  // Показываем предупреждение при истекшей подписке
  useEffect(() => {
    if (subscription && !subscriptionLoading && !canCreateBookings) {
      setShowSubscriptionWarning(true)
    } else {
      setShowSubscriptionWarning(false)
    }
  }, [subscription, subscriptionLoading, canCreateBookings])

  useEffect(() => {
    const loadCompanyName = async () => {
      try {
        const setting = await settingsApi.getSetting('company_name')
        const value = setting?.value?.trim()
        if (value) {
          setCompanyName(value)
        }
      } catch (error) {
        console.error('Ошибка загрузки названия компании:', error)
      }
    }

    loadCompanyName()
  }, [])

  const menuItems = [
    { path: '/', icon: '📊', label: 'Дашборд' },
    { path: '/bookings', icon: '📋', label: 'Записи', requiresSubscription: true },
    { path: '/calendar', icon: '📅', label: 'Календарь', requiresSubscription: true },
    { path: '/work-orders', icon: '📋', label: 'Лист-наряды', adminOnly: true },
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
    <aside className={`tenant-sidebar ${isOpen ? 'tenant-sidebar--open' : 'tenant-sidebar--closed'}`}>
      <nav className="sidebar-nav">
        <ul className="nav-list">
          <li className="nav-section">
            <div className="sidebar-header">
              <h2>Booking</h2>
              <div className="user-info">
                <span className="user-name">
                  {companyName || user?.first_name || user?.telegram_id}
                </span>
                {user?.is_admin && <span className="user-role">Администратор</span>}
              </div>
            </div>

            {/* Информация о подписке */}
            {subscription && !subscriptionLoading && (
              <div className="subscription-info">
                <div className="subscription-header">
                  <span className="subscription-label">Подписка</span>
                  <div className="subscription-summary">
                    <span
                      className="subscription-status"
                      style={{ color: getSubscriptionStatusColor(subscription.status) }}
                    >
                      {getSubscriptionStatusText(subscription.status)}
                    </span>
                    <div className="subscription-plan">{subscription.plan_name}</div>
                    <div className="subscription-date">{getSubscriptionDateInfo()}</div>
                  </div>
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
          </li>

          {menuItems
            .filter((item) => {
              if (item.adminOnly && !user?.is_admin) return false
              if (item.masterOnly && !user?.is_master) return false
              return true
            })
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
                      onClick={onClose}
                    >
                      <span className="nav-icon">{item.icon}</span>
                      <span className="nav-label">{item.label}</span>
                    </Link>
                  )}
                </li>
              )
            })}
          
          {/* Дополнительные ссылки */}
          <li className="nav-divider"></li>
          
          {/* Биллинг/Подписка */}
          <li>
            <Link
              to="/billing"
              className={`nav-link ${
                location.pathname === '/billing' ? 'active' : ''
              }`}
              onClick={onClose}
            >
              <span className="nav-icon">💳</span>
              <span className="nav-label">Биллинг</span>
            </Link>
          </li>

          <li className="nav-divider"></li>

          <li className="nav-section">
            <button
              onClick={() => {
                logout()
                onClose?.()
              }}
              className="logout-btn"
            >
              <span>🚪</span>
              <span>Выход</span>
            </button>
          </li>
        </ul>
      </nav>
    </aside>
  )
}

export default Sidebar
