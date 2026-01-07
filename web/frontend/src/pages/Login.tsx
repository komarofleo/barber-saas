import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import './Login.css'

function Login() {
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
      await login(username, password)
      // Ждем обновления state и проверяем токен
      await new Promise(resolve => setTimeout(resolve, 200))
      const token = localStorage.getItem('token')
      if (token) {
        navigate('/')
      } else {
        setError('Токен не сохранен')
      }
    } catch (err: any) {
      console.error('Login error:', err)
      console.error('Error response:', err.response)
      console.error('Error status:', err.response?.status)
      console.error('Error data:', err.response?.data)
      console.error('Error detail:', err.response?.data?.detail)
      
      // Извлекаем сообщение об ошибке из ответа
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка входа'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>AutoService</h1>
        <h2>Вход в админ-панель</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Telegram ID:</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="329621295"
            />
          </div>
          <div className="form-group">
            <label>Пароль:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Ваш Telegram ID"
            />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
        <p className="hint">Используйте ваш Telegram ID как логин и пароль</p>
      </div>
    </div>
  )
}

export default Login

