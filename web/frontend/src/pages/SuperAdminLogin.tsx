/**
 * Страница входа супер-администратора
 * 
 * Отображает форму входа с валидацией
 * После успешного входа сохраняет токен и перенаправляет на дашборд
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { SuperAdminLoginRequest, superAdminApi } from '../api/superAdmin'
import './SuperAdminLogin.css'

const SuperAdminLogin: React.FC = () => {
  const navigate = useNavigate()

  // Состояния формы
  const [formData, setFormData] = useState<SuperAdminLoginRequest>({
    username: '',
    password: '',
  })

  // UI состояния
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<boolean>(false)
  const [showPassword, setShowPassword] = useState<boolean>(false)
  const [rememberMe, setRememberMe] = useState<boolean>(false)

  // Проверка авторизации при загрузке
  useEffect(() => {
    const token = localStorage.getItem('super_admin_token')
    if (token) {
      navigate('/super-admin/dashboard')
    }
  }, [navigate])

  // Валидация формы
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    // Валидация username
    if (!formData.username || formData.username.length < 3) {
      newErrors.username = 'Имя пользователя должно содержать минимум 3 символа'
    } else if (formData.username.length > 100) {
      newErrors.username = 'Имя пользователя не должно превышать 100 символов'
    }

    // Валидация password
    if (!formData.password || formData.password.length < 6) {
      newErrors.password = 'Пароль должен содержать минимум 6 символов'
    } else if (formData.password.length > 100) {
      newErrors.password = 'Пароль не должен превышать 100 символов'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Обработчик ввода
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    
    // Очищаем ошибку поля при вводе
    setErrors(prev => ({
      ...prev,
      [name]: '',
    }))

    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  // Обработчик отправки формы
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Валидация формы
    if (!validateForm()) {
      return
    }

    setLoading(true)
    setErrors({})

    try {
      const response = await superAdminApi.login(formData)

      // Сохраняем токен
      if (rememberMe) {
        localStorage.setItem('super_admin_token', response.access_token)
      } else {
        sessionStorage.setItem('super_admin_token', response.access_token)
      }

      // Сохраняем данные супер-админа
      const storage = rememberMe ? localStorage : sessionStorage
      storage.setItem('super_admin', JSON.stringify(response.super_admin))

      // Перенаправляем на дашборд
      navigate('/super-admin/dashboard')
    } catch (error: any) {
      console.error('Ошибка входа:', error)
      setErrors({
        general: error.message || 'Неверный логин или пароль',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="super-admin-login-page">
      <div className="login-container">
        {/* Заголовок страницы */}
        <div className="login-header">
          <div className="login-icon">🔐</div>
          <h1 className="login-title">Панель супер-администратора</h1>
          <p className="login-subtitle">
            Введите свои учетные данные для доступа к админ-панели
          </p>
        </div>

        {/* Общие ошибки */}
        {errors.general && (
          <div className="error-alert">
            <div className="error-icon">⚠️</div>
            <div className="error-message">{errors.general}</div>
          </div>
        )}

        {/* Форма входа */}
        <form onSubmit={handleSubmit} className="login-form">
          {/* Поле username */}
          <div className="form-group">
            <label htmlFor="username" className="form-label">
              Имя пользователя
            </label>
            <div className="input-wrapper">
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className={`form-input ${errors.username ? 'error' : ''}`}
                placeholder="Введите имя пользователя"
                autoComplete="username"
                required
              />
              <span className="input-icon">👤</span>
            </div>
            {errors.username && (
              <div className="field-error">{errors.username}</div>
            )}
          </div>

          {/* Поле password */}
          <div className="form-group">
            <label htmlFor="password" className="form-label">
              Пароль
            </label>
            <div className="input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className={`form-input ${errors.password ? 'error' : ''}`}
                placeholder="Введите пароль"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                type="button"
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
            {errors.password && (
              <div className="field-error">{errors.password}</div>
            )}
          </div>

          {/* Checkbox "Запомнить меня" */}
          <div className="form-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                className="checkbox-input"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              <span className="checkbox-text">Запомнить меня</span>
            </label>

            <a href="/super-admin/forgot-password" className="forgot-password">
              Забыли пароль?
            </a>
          </div>

          {/* Кнопка входа */}
          <button
            type="submit"
            className={`submit-button ${loading ? 'loading' : ''}`}
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                Вход в систему...
              </>
            ) : (
              'Войти в панель'
            )}
          </button>

          {/* Ссылка на главную */}
          <div className="back-link">
            <a href="/">
              ← Вернуться на главную
            </a>
          </div>
        </form>

        {/* Информация безопасности */}
        <div className="security-info">
          <h3>🔒 Безопасность</h3>
          <ul>
            <li>✅ Все данные шифруются при передаче</li>
            <li>✅ Токен доступа хранится защищенно</li>
            <li>✅ Автоматический выход через 24 часа</li>
            <li>✅ Логи всех действий сохраняются</li>
          </ul>
        </div>

        {/* Контакты поддержки */}
        <div className="support-info">
          <h3>📞 Нужна помощь?</h3>
          <p className="support-text">
            Если вы забыли пароль или не можете войти, свяжитесь с поддержкой
          </p>
          <div className="support-links">
            <a href="mailto:support@autoservice-saas.com" className="support-link">
              📧 Email поддержка
            </a>
            <a href="https://t.me/autoservice_support" className="support-link">
              🤖 Telegram поддержка
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SuperAdminLogin

