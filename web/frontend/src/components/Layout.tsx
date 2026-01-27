import { ReactNode, useState } from 'react'
import Sidebar from './Sidebar'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
  showMenuToggle?: boolean
}

function Layout({ children, showMenuToggle = true }: LayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const handleToggle = () => {
    setIsSidebarOpen((prev) => !prev)
  }

  const handleClose = () => {
    setIsSidebarOpen(false)
  }

  return (
    <div className="layout">
      <Sidebar isOpen={isSidebarOpen} onClose={handleClose} />
      {isSidebarOpen && <div className="sidebar-backdrop" onClick={handleClose}></div>}
      <main className="main-content">
        <button className="menu-toggle" onClick={handleToggle}>
          <span className="menu-icon">☰</span>
        </button>
        {children}
      </main>
    </div>
  )
}

export default Layout









