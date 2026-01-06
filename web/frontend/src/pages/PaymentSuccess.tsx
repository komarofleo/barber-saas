/**
 * Страница успешной оплаты
 * 
 * Отображает сообщение об успешной оплате и предоставляет ссылки:
 * - На дашборд компании
 * - На Telegram бота
 * - На помощь
 */

import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'

interface PaymentStatus {
  payment_id: number
  status: string
  yookassa_payment_status: string
  company_created: boolean
  company_id: number | null
  company_name: string | null
  email: string | null
  subscription_status?: string
  can_create_bookings?: boolean
}

const PaymentSuccess: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  const paymentId = searchParams.get('payment_id')

  useEffect(() => {
    if (!paymentId) {
      setError('ID платежа не указан')
      setLoading(false)
      return
    }

    // Функция для проверки статуса платежа
    const checkPaymentStatus = async () => {
      try {
        setChecking(true)
        const response = await axios.get<PaymentStatus>(
          `/api/public/payments/${paymentId}/status`
        )
        setPaymentStatus(response.data)
        setError(null)

        // Если компания создана, перенаправляем на dashboard через 3 секунды
        if (response.data.company_created && response.data.company_id) {
          setTimeout(() => {
            navigate(`/company/${response.data.company_id}/dashboard`)
          }, 3000)
        } else {
          // Если компания еще не создана, проверяем снова через 2 секунды
          setTimeout(() => {
            checkPaymentStatus()
          }, 2000)
        }
      } catch (err: any) {
        console.error('Ошибка проверки статуса платежа:', err)
        setError(err.response?.data?.detail || 'Ошибка проверки статуса платежа')
        // Повторяем попытку через 3 секунды
        setTimeout(() => {
          checkPaymentStatus()
        }, 3000)
      } finally {
        setChecking(false)
        setLoading(false)
      }
    }

    // Начинаем проверку сразу
    checkPaymentStatus()
  }, [paymentId, navigate])

  if (loading || checking) {
    return (
      <div className="payment-success-page">
        <div className="payment-success-container">
          <div className="success-icon">⏳</div>
          <h1 className="success-title">Обработка платежа...</h1>
          <p className="success-subtitle">
            Пожалуйста, подождите. Мы обрабатываем ваш платеж и создаем аккаунт.
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="payment-success-page">
        <div className="payment-success-container">
          <div className="success-icon">⚠️</div>
          <h1 className="success-title">Ошибка</h1>
          <p className="success-subtitle">{error}</p>
          <div className="action-buttons">
            <button
              className="action-button primary"
              onClick={() => window.location.reload()}
            >
              Обновить страницу
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!paymentStatus) {
    return (
      <div className="payment-success-page">
        <div className="payment-success-container">
          <div className="success-icon">⏳</div>
          <h1 className="success-title">Проверка статуса...</h1>
        </div>
      </div>
    )
  }

  const isCompanyCreated = paymentStatus.company_created

  return (
    <div className="payment-success-page">
      <div className="payment-success-container">
        <div className="success-icon">✓</div>
        
        <h1 className="success-title">
          {isCompanyCreated ? 'Платеж успешен!' : 'Платеж обрабатывается...'}
        </h1>
        
        <p className="success-subtitle">
          {isCompanyCreated 
            ? 'Ваша компания зарегистрирована в AutoService SaaS'
            : 'Мы обрабатываем ваш платеж и создаем аккаунт. Это может занять несколько секунд.'}
        </p>

        {isCompanyCreated ? (
          <div className="success-message">
            <p>🎉 Добро пожаловать!</p>
            <p>
              Ваш аккаунт создан успешно. Вы получите приветственное письмо 
              с данными для входа и инструкциями по настройке.
            </p>
            {paymentStatus.email && (
              <p>
                <strong>Email:</strong> {paymentStatus.email}
              </p>
            )}
          </div>
        ) : (
          <div className="success-message">
            <p>⏳ Ожидание создания компании...</p>
            <p>Пожалуйста, не закрывайте эту страницу.</p>
          </div>
        )}

        <div className="info-cards">
          <div className="info-card">
            <div className="info-card-icon">📧</div>
            <div className="info-card-content">
              <h3>Email отправлен</h3>
              <p>Проверьте почту с данными для входа</p>
            </div>
          </div>

          <div className="info-card">
            <div className="info-card-icon">🤖</div>
            <div className="info-card-content">
              <h3>Telegram бот готов</h3>
              <p>Ваш бот активирован и готов к работе</p>
            </div>
          </div>

          <div className="info-card">
            <div className="info-card-icon">📊</div>
            <div className="info-card-content">
              <h3>Дашборд доступен</h3>
              <p>Управляйте вашим автосервисом онлайн</p>
            </div>
          </div>
        </div>

        {isCompanyCreated && (
          <>
            <div className="action-buttons">
              <button
                className="action-button primary"
                onClick={() => navigate(`/company/${paymentStatus.company_id}/dashboard`)}
              >
                Перейти в дашборд →
              </button>
              
              <button
                className="action-button secondary"
                onClick={() => navigate('/')}
              >
                На главную
              </button>
            </div>

            <div className="help-section">
              <h3>Нужна помощь?</h3>
              <ul className="help-links">
                <li>
                  <a href="mailto:support@autoservice-saas.com" className="help-link">
                    Написать в поддержку
                  </a>
                </li>
                <li>
                  <a href="/docs" className="help-link">
                    Документация
                  </a>
                </li>
                <li>
                  <a href="/faq" className="help-link">
                    FAQ
                  </a>
                </li>
              </ul>
            </div>

            <div className="footer-hint">
              <p>
                💡 Вы будете автоматически перенаправлены на дашборд через 3 секунды
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default PaymentSuccess

