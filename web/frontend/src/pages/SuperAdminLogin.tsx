/**
 * Страница входа супер-администратора.
 * Компактный single-viewport layout под высоту ноутбука.
 */

import React, { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { SuperAdminLoginRequest, superAdminApi } from '../api/superAdmin'
import './SuperAdminLogin.css'

const SuperAdminLogin: React.FC = () => {
  const navigate = useNavigate()
  const isRedirecting = useRef(false)

  const [formData, setFormData] = useState<SuperAdminLoginRequest>({
    username: '',
    password: '',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<boolean>(false)
  const [showPassword, setShowPassword] = useState<boolean>(false)
  const [rememberMe, setRememberMe] = useState<boolean>(false)

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.username || formData.username.length < 3) {
      newErrors.username = 'Минимум 3 символа'
    } else if (formData.username.length > 100) {
      newErrors.username = 'Максимум 100 символов'
    }

    if (!formData.password || formData.password.length < 6) {
      newErrors.password = 'Минимум 6 символов'
    } else if (formData.password.length > 100) {
      newErrors.password = 'Максимум 100 символов'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setErrors((prev) => ({ ...prev, [name]: '' }))
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (loading || !validateForm()) return

    setLoading(true)
    setErrors({})

    try {
      const response = await superAdminApi.login(formData)

      if (rememberMe) {
        localStorage.setItem('super_admin_token', response.access_token)
        localStorage.setItem('super_admin', JSON.stringify(response.super_admin))
      } else {
        sessionStorage.setItem('super_admin_token', response.access_token)
        sessionStorage.setItem('super_admin', JSON.stringify(response.super_admin))
      }

      const savedToken = rememberMe
        ? localStorage.getItem('super_admin_token')
        : sessionStorage.getItem('super_admin_token')

      if (!savedToken) {
        setErrors({ general: 'Ошибка сохранения токена. Попробуйте снова.' })
        setLoading(false)
        return
      }

      if (!isRedirecting.current) {
        isRedirecting.current = true
        navigate('/super-admin/dashboard', { replace: true })
      }
    } catch (error: any) {
      isRedirecting.current = false
      let errorMessage = 'Неверный логин или пароль'

      if (error?.message) {
        if (typeof error.message === 'string') {
          errorMessage = error.message
        } else if (typeof error.message === 'object') {
          errorMessage = String(error.message.message || error.message.detail || errorMessage)
        }
      } else if (error?.response?.data) {
        const data = error.response.data
        errorMessage = String(data.detail || data.message || data.error || errorMessage)
      }

      setErrors({ general: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sa-login">
      <div className="sa-login__orb sa-login__orb--a" aria-hidden />
      <div className="sa-login__orb sa-login__orb--b" aria-hidden />

      <div className="sa-login__card anim-fade-up">
        <header className="sa-login__brand">
          <div className="sa-login__badge">Barber SaaS</div>
          <h1 className="sa-login__title">Супер-админ</h1>
          <p className="sa-login__subtitle">Вход в панель управления платформой</p>
        </header>

        {errors.general && (
          <div className="sa-login__alert" role="alert">
            {errors.general}
          </div>
        )}

        <form onSubmit={handleSubmit} className="sa-login__form">
          <div className="sa-login__field">
            <label htmlFor="username">Имя пользователя</label>
            <div className="sa-login__input-wrap">
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className={errors.username ? 'is-error' : ''}
                placeholder="admin"
                autoComplete="username"
                required
              />
            </div>
            {errors.username && <div className="sa-login__error">{errors.username}</div>}
          </div>

          <div className="sa-login__field">
            <label htmlFor="password">Пароль</label>
            <div className="sa-login__input-wrap">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className={errors.password ? 'is-error' : ''}
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="sa-login__eye"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? 'Скрыть' : 'Показать'}
              </button>
            </div>
            {errors.password && <div className="sa-login__error">{errors.password}</div>}
          </div>

          <div className="sa-login__row">
            <label className="sa-login__remember">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              <span>Запомнить</span>
            </label>
            <a href="/super-admin/forgot-password" className="sa-login__link">
              Забыли пароль?
            </a>
          </div>

          <button type="submit" className="sa-login__submit" disabled={loading}>
            {loading ? (
              <>
                <span className="sa-login__spinner" />
                Вход...
              </>
            ) : (
              'Войти'
            )}
          </button>
        </form>

        <footer className="sa-login__footer">
          <p className="sa-login__secure">Шифрование · токен 24ч · журнал действий</p>
          <div className="sa-login__footer-links">
            <Link to="/">На главную</Link>
            <a href="mailto:support@barber-saas.com">Поддержка</a>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default SuperAdminLogin
