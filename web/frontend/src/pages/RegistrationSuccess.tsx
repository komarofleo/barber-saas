import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './PaymentSuccess.css'

interface RegistrationCredentials {
  login_email: string
  password: string
  company_id?: number | null
  dashboard_url?: string | null
}

const RegistrationSuccess = () => {
  const navigate = useNavigate()
  const [credentials, setCredentials] = useState<RegistrationCredentials | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const raw = sessionStorage.getItem('registration_credentials')
    if (!raw) {
      setError('Данные для входа не найдены. Пожалуйста, попробуйте войти в систему.')
      return
    }

    try {
      const parsed = JSON.parse(raw) as RegistrationCredentials
      if (!parsed.login_email || !parsed.password) {
        setError('Данные для входа не найдены. Пожалуйста, попробуйте войти в систему.')
        return
      }
      setCredentials(parsed)
    } catch {
      setError('Не удалось прочитать данные регистрации. Попробуйте войти в систему.')
    }
  }, [])

  return (
    <div className="payment-success-page">
      <div className="payment-success-container">
        <div className="success-icon">✓</div>
        <h1 className="success-title">Регистрация завершена</h1>
        <p className="success-subtitle">
          Данные для входа в систему готовы
        </p>

        {error && (
          <div className="success-message">
            <p>⚠️ {error}</p>
          </div>
        )}

        {credentials && (
          <div className="success-message">
            <div className="credentials-box">
              <p><strong>Логин (Email):</strong> {credentials.login_email}</p>
              <p><strong>Пароль:</strong> {credentials.password}</p>
              <p className="credentials-hint">Сохраните данные и смените пароль после входа.</p>
            </div>
          </div>
        )}

        <div className="action-buttons">
          <button
            className="action-button primary"
            onClick={() => navigate('/login')}
          >
            Войти в систему
          </button>
          {credentials?.company_id && (
            <button
              className="action-button secondary"
              onClick={() => navigate(`/company/${credentials.company_id}/dashboard`)}
            >
              Перейти в дашборд →
            </button>
          )}
          <button
            className="action-button secondary"
            onClick={() => navigate('/')}
          >
            На главную
          </button>
        </div>
      </div>
    </div>
  )
}

export default RegistrationSuccess
