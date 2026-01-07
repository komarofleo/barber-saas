import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
  showMenuToggle?: boolean
}

function Layout({ children, showMenuToggle = true }: LayoutProps) {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        {showMenuToggle && (
          <button className="menu-toggle" onClick={() => alert('Меню')}>
            <span className="menu-icon">☰</span>
          </button>
        )}
        {children}
      </main>
    </div>
  )
}

export default Layout









