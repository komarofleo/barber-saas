import { useState, useEffect, useRef } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Bookings from './pages/Bookings'
import Calendar from './pages/Calendar'
import Users from './pages/Users'
import Services from './pages/Services'
import Masters from './pages/Masters'
import Posts from './pages/Posts'
import Statistics from './pages/Statistics'
import Settings from './pages/Settings'
import Blocks from './pages/Blocks'
import Promocodes from './pages/Promocodes'
import Promotions from './pages/Promotions'
import Clients from './pages/Clients'
import Broadcasts from './pages/Broadcasts'
import Register from './pages/Register'
import Billing from './pages/Billing'
import WorkOrders from './pages/WorkOrders'
import PaymentSuccess from './pages/PaymentSuccess'
import PaymentError from './pages/PaymentError'
import SuperAdminLogin from './pages/SuperAdminLogin'
import SuperAdminDashboard from './pages/SuperAdminDashboard'
import SuperAdminCompanies from './pages/SuperAdminCompanies'
import SuperAdminCompanyDetails from './pages/SuperAdminCompanyDetails'
import SuperAdminCompanyEdit from './pages/SuperAdminCompanyEdit'
import SuperAdminSubscriptions from './pages/SuperAdminSubscriptions'
import SuperAdminPayments from './pages/SuperAdminPayments'
import Layout from './components/Layout'
import SuperAdminLayout from './components/SuperAdminLayout'
import { AuthProvider, useAuth } from './hooks/useAuth'
import SubscriptionBarrier from './components/SubscriptionBarrier'
import './App.css'
import './styles/common.css'

function ProtectedRoute({
  children,
  requireSubscription = false,
  showMenuToggle = true
}: {
  children: React.ReactNode
  requireSubscription?: boolean
  showMenuToggle?: boolean
}) {
  // Не проверяем авторизацию для страниц супер-админа
  const currentPath = window.location.pathname
  if (currentPath.startsWith('/super-admin')) {
    return <>{children}</>
  }
  
  const { isAuthenticated, loading, user, canCreateBookings } = useAuth()
  
  if (loading) {
    return <div className="loading-screen">Загрузка...</div>
  }
  
  // Проверяем токен в localStorage как fallback
  const token = localStorage.getItem('token')
  if (!isAuthenticated && !token) {
    return <Navigate to="/login" replace />
  }
  
  // Если есть токен, но user еще не загружен, ждем
  if (token && !user) {
    return <div className="loading-screen">Загрузка пользователя...</div>
  }
  
  // Если нужна подписка и она неактивна, показываем барьер
  if (requireSubscription && !canCreateBookings) {
    return <SubscriptionBarrier />
  }
  
  return <Layout showMenuToggle={showMenuToggle}>{children}</Layout>
}

function SuperAdminProtectedRoute({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null)
  const hasChecked = useRef(false)
  
  useEffect(() => {
    // Проверяем только один раз
    if (hasChecked.current) {
      return
    }
    hasChecked.current = true
    
    // Проверяем токен супер-админа в localStorage или sessionStorage
    const superAdminToken = localStorage.getItem('super_admin_token') || sessionStorage.getItem('super_admin_token')
    
    if (!superAdminToken) {
      // Если токена нет и мы не на странице логина, перенаправляем
      if (location.pathname !== '/super-admin/login') {
        navigate('/super-admin/login', { replace: true })
      }
      setIsAuthorized(false)
      return
    }
    
    setIsAuthorized(true)
  }, [navigate, location.pathname])
  
  // Показываем загрузку во время проверки
  if (isAuthorized === null) {
    return <div className="loading-screen">Загрузка...</div>
  }
  
  // Если не авторизован, не рендерим ничего (перенаправление уже произошло)
  if (!isAuthorized) {
    return null
  }
  
  return <SuperAdminLayout>{children}</SuperAdminLayout>
}

function AppRoutes() {
  return (
    <Routes>
      {/* Публичные маршруты */}
      <Route path="/login" element={<Login />} />
      <Route path="/company/:id/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/payment/success" element={<PaymentSuccess />} />
      <Route path="/payment/error" element={<PaymentError />} />
      
      {/* Основные маршруты - требуют подписку для создания записей */}
      <Route
        path="/"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bookings"
        element={
          <ProtectedRoute requireSubscription showMenuToggle={false}>
            <Bookings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/calendar"
        element={
          <ProtectedRoute requireSubscription showMenuToggle={false}>
            <Calendar />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Users />
          </ProtectedRoute>
        }
      />
      <Route
        path="/services"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Services />
          </ProtectedRoute>
        }
      />
      <Route
        path="/masters"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Masters />
          </ProtectedRoute>
        }
      />
      <Route
        path="/posts"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Posts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/statistics"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Statistics />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/blocks"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Blocks />
          </ProtectedRoute>
        }
      />
      <Route
        path="/promocodes"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Promocodes />
          </ProtectedRoute>
        }
      />
      <Route
        path="/promotions"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Promotions />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clients"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Clients />
          </ProtectedRoute>
        }
      />
      <Route
        path="/broadcasts"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Broadcasts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/billing"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <Billing />
          </ProtectedRoute>
        }
      />
      <Route
        path="/work-orders"
        element={
          <ProtectedRoute showMenuToggle={false}>
            <WorkOrders />
          </ProtectedRoute>
        }
      />
      
      {/* Супер-администратор */}
      <Route path="/super-admin" element={<Navigate to="/super-admin/login" replace />} />
      <Route path="/super-admin/login" element={<SuperAdminLogin />} />
      <Route
        path="/super-admin/dashboard"
        element={<SuperAdminProtectedRoute><SuperAdminDashboard /></SuperAdminProtectedRoute>}
      />
      <Route
        path="/super-admin/companies"
        element={<SuperAdminProtectedRoute><SuperAdminCompanies /></SuperAdminProtectedRoute>}
      />
      <Route
        path="/super-admin/companies/:id"
        element={<SuperAdminProtectedRoute><SuperAdminCompanyDetails /></SuperAdminProtectedRoute>}
      />
      <Route
        path="/super-admin/companies/:id/edit"
        element={<SuperAdminProtectedRoute><SuperAdminCompanyEdit /></SuperAdminProtectedRoute>}
      />
      <Route
        path="/super-admin/subscriptions"
        element={<SuperAdminProtectedRoute><SuperAdminSubscriptions /></SuperAdminProtectedRoute>}
      />
      <Route
        path="/super-admin/payments"
        element={<SuperAdminProtectedRoute><SuperAdminPayments /></SuperAdminProtectedRoute>}
      />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
