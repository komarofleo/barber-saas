/**
 * Страница успешной оплаты
 * 
 * Отображает сообщение об успешной оплате и предоставляет ссылки:
 * - На дашборд компании
 * - На Telegram бота
 * - На помощь
 */

import React, { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

const PaymentSuccess: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    // Автоматический редирект на дашборд через 5 секунд
    const timer = setTimeout(() => {
      navigate('/dashboard')
    }, 5000)

    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <div className="payment-success-page">
      <div className="payment-success-container">
        <div className="success-icon">✓</div>
        
        <h1 className="success-title">Платеж успешен!</h1>
        
        <p className="success-subtitle">
          Ваша компания зарегистрирована в AutoService SaaS
        </p>

        <div className="success-message">
          <p>🎉 Добро пожаловать!</p>
          <p>
            Ваш аккаунт создан успешно. Вы получите приветственное письмо 
            с данными для входа и инструкциями по настройке.
          </p>
        </div>

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

        <div className="action-buttons">
          <button
            className="action-button primary"
            onClick={() => navigate('/dashboard')}
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
            💡 Вы будете автоматически перенаправлены на дашборд через 5 секунд
          </p>
        </div>
      </div>
    </div>
  )
}

export default PaymentSuccess

