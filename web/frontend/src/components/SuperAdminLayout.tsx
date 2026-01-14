/**
 * Layout для супер-администратора
 * 
 * Содержит:
 * - Боковую панель с навигацией
 * - Верхний бар с профилем
 * - Кнопку выхода
 * - Контент страницы
 */

import React, { useState, createContext, useContext } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import './SuperAdminLayout.css'

// Контекст для управления sidebar
interface SidebarContextType {
  sidebarOpen: boolean
  toggleSidebar: () => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export const useSidebar = () => {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error('useSidebar must be used within SuperAdminLayout')
  }
  return context
}

const SuperAdminLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true)
  const [superAdmin, setSuperAdmin] = useState<any>(null)

  // Получаем данные супер-админа из хранилища
  React.useEffect(() => {
    const superAdminData = localStorage.getItem('super_admin') || sessionStorage.getItem('super_admin')
    if (superAdminData) {
      setSuperAdmin(JSON.parse(superAdminData))
    }
  }, [])

  // Выход из системы
  const handleLogout = async () => {
    try {
      const { superAdminApi } = await import('../api/superAdmin')
      await superAdminApi.logout()
      navigate('/super-admin/login')
    } catch (error: any) {
      console.error('Ошибка выхода:', error)
      // Удаляем токены локально даже при ошибке API
      localStorage.removeItem('super_admin_token')
      sessionStorage.removeItem('super_admin_token')
      localStorage.removeItem('super_admin')
      sessionStorage.removeItem('super_admin')
      navigate('/super-admin/login')
    }
  }

  // Переключение sidebar
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  // Навигационные пункты
  const navItems = [
    {
      path: '/super-admin/dashboard',
      icon: '📊',
      label: 'Дашборд',
    },
    {
      path: '/super-admin/companies',
      icon: '🏢',
      label: 'Компании',
    },
    {
      path: '/super-admin/subscriptions',
      icon: '📋',
      label: 'Подписки',
    },
    {
      path: '/super-admin/payments',
      icon: '💰',
      label: 'Платежи',
    },
  ]

  // Проверяем активный пункт
  const isActive = (path: string): boolean => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  return (
    <div className="super-admin-layout">
      {/* Боковая панель */}
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        {/* Логотип */}
        <div className="sidebar-logo">
          <div className="logo-icon">🚀</div>
          <div className="logo-text">Barber</div>
        </div>

        {/* Навигация */}
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
              type="button"
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Информация о пользователе */}
        {superAdmin && (
          <div className="sidebar-user">
            <div className="user-header">
              <div className="user-avatar">
                {superAdmin.username.charAt(0).toUpperCase()}
              </div>
              <div className="user-info">
                <div className="user-name">{superAdmin.username}</div>
                <div className="user-role">Супер-администратор</div>
              </div>
            </div>
            <button
              className="sidebar-logout-button"
              onClick={handleLogout}
              title="Выход"
            >
              <span className="logout-icon">🚪</span>
              <span className="logout-text">Выход</span>
            </button>
          </div>
        )}
      </div>

      {/* Основной контент */}
      <div className="main-content">
        {/* Контент страницы */}
        <main className="page-content">
          <SidebarContext.Provider value={{ sidebarOpen, toggleSidebar }}>
            {children}
          </SidebarContext.Provider>
        </main>

        {/* Footer */}
        <footer className="main-footer">
          <p className="footer-text">
            © 2026 Barber SaaS. Все права защищены.
          </p>
          <p className="footer-links">
            <a href="/docs" className="footer-link">
              Документация
            </a>
            <a href="/support" className="footer-link">
              Поддержка
            </a>
            <a href="mailto:support@barber-saas.com" className="footer-link">
              Связаться
            </a>
          </p>
        </footer>
      </div>
    </div>
  )
}

export default SuperAdminLayout

