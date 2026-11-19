import { ReactNode, useEffect, useState } from 'react'
import Sidebar from './Sidebar'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
  showMenuToggle?: boolean
}

const SIDEBAR_COLLAPSED_KEY = 'barber_sidebar_collapsed'

function Layout({ children, showMenuToggle = true }: LayoutProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1'
    } catch {
      return false
    }
  })
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? '1' : '0')
    } catch {
      // ignore
    }
  }, [collapsed])

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 768) {
        setMobileOpen(false)
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return (
    <div className={`layout ${collapsed ? 'layout--sidebar-collapsed' : ''} ${mobileOpen ? 'layout--mobile-open' : ''}`}>
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <main className="main-content">
        {showMenuToggle && (
          <button
            type="button"
            className="menu-toggle"
            onClick={() => setMobileOpen((prev) => !prev)}
            aria-label="Открыть меню"
          >
            <span className="menu-icon">☰</span>
          </button>
        )}
        {children}
      </main>
      {mobileOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Закрыть меню"
          onClick={() => setMobileOpen(false)}
        />
      )}
    </div>
  )
}

export default Layout
