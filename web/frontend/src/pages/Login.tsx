import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/auth'
import './Login.css'

function Login() {
  const { id: companyId } = useParams<{ id: string }>()
  const [loginType, setLoginType] = useState<'telegram' | 'email'>('telegram')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, isAuthenticated, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    // Проверяем токен напрямую, чтобы избежать бесконечного редиректа
    // Редиректим только если есть токен И пользователь авторизован И загрузка завершена
    if (authLoading) {
      return // Ждем завершения загрузки
    }
    
    const token = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    
    if (token && savedUser && isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, authLoading, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // Используем метод login из useAuth, который правильно обновляет контекст
      await login(username, password)
      
      // Проверяем, что пользователь авторизован
      const token = localStorage.getItem('token')
      const savedUser = localStorage.getItem('user')
      
      if (token && savedUser) {
        // Даем время useAuth обновить state из localStorage
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Редирект на главную страницу (Dashboard)
        console.log('Redirecting to dashboard...')
        navigate('/', { replace: true })
      } else {
        setError('Ошибка сохранения данных входа')
      }
    } catch (err: any) {
      console.error('Login error:', err)
      console.error('Error response:', err.response)
      
      // Безопасное извлечение сообщения об ошибке
      let errorMessage = 'Ошибка входа'
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail
      } else if (err.message && typeof err.message === 'string') {
        errorMessage = err.message
      } else if (err.response?.status === 401) {
        errorMessage = 'Неверный логин или пароль'
      } else if (err.response?.status === 403) {
        errorMessage = 'Доступ запрещен'
      } else if (err.response?.status === 404) {
        errorMessage = 'Пользователь не найден'
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleLoginTypeChange = (type: 'telegram' | 'email') => {
    setLoginType(type)
    setUsername('')
    setPassword('')
    setError('')
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>Barber</h1>
        <h2>Вход в админ-панель</h2>
        
        {/* Переключатель типа входа */}
        <div className="login-type-toggle">
          <button
            type="button"
            className={loginType === 'telegram' ? 'active' : ''}
            onClick={() => handleLoginTypeChange('telegram')}
          >
            Через Telegram ID
          </button>
          <button
            type="button"
            className={loginType === 'email' ? 'active' : ''}
            onClick={() => handleLoginTypeChange('email')}
          >
            Через Email
          </button>
        </div>

        {/* Универсальная форма входа */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>{loginType === 'telegram' ? 'Telegram ID:' : 'Email:'}</label>
            <input
              type="text"
              inputMode={loginType === 'telegram' ? 'numeric' : 'email'}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder={loginType === 'telegram' ? '329621295' : 'admin@avtoservis.ru'}
              pattern={loginType === 'telegram' ? '[0-9]*' : undefined}
            />
          </div>
          <div className="form-group">
            <label>Пароль:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Ваш пароль"
            />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
          <p className="hint">
            {loginType === 'telegram' 
              ? 'Используйте ваш Telegram ID как логин и пароль' 
              : 'Используйте email и пароль, полученные при регистрации'
            }
          </p>
        </form>
      </div>
    </div>
  )
}

export default Login

