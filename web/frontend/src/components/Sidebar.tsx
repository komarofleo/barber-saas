import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import './Sidebar.css'

function Sidebar() {
  const location = useLocation()
  const { user, logout } = useAuth()

  const menuItems = [
    { path: '/', icon: '📊', label: 'Дашборд' },
    { path: '/bookings', icon: '📋', label: 'Записи' },
    { path: '/calendar', icon: '📅', label: 'Календарь' },
    { path: '/clients', icon: '👤', label: 'Клиенты' },
    { path: '/users', icon: '👥', label: 'Пользователи', adminOnly: true },
    { path: '/services', icon: '🔧', label: 'Услуги' },
    { path: '/masters', icon: '👨‍🔧', label: 'Мастера' },
    { path: '/posts', icon: '🛠️', label: 'Посты' },
    { path: '/blocks', icon: '🚫', label: 'Блокировки' },
    { path: '/promocodes', icon: '🎟️', label: 'Промокоды' },
    { path: '/promotions', icon: '🎁', label: 'Акции' },
    { path: '/broadcasts', icon: '📧', label: 'Рассылки' },
    { path: '/statistics', icon: '📈', label: 'Статистика' },
    { path: '/settings', icon: '⚙️', label: 'Настройки' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>AutoService</h2>
        <div className="user-info">
          <span className="user-name">{user?.first_name || user?.telegram_id}</span>
          {user?.is_admin && <span className="user-role">Администратор</span>}
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <ul className="nav-list">
          {menuItems
            .filter((item) => !item.adminOnly || user?.is_admin)
            .map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </Link>
              </li>
            ))}
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
