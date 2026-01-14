/**
 * Страница неуспешной оплаты
 * 
 * Отображает сообщение об ошибке оплаты и предоставляет:
 * - Попытку оплаты снова
 * - Переход на главную
 * - Связь с поддержкой
 */

import React from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

type ErrorType = 'payment_failed' | 'payment_cancelled' | 'payment_expired' | 'unknown'

const PaymentError: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  
  const errorType = (searchParams.get('type') as ErrorType) || 'unknown'
  const paymentId = searchParams.get('payment_id') || ''

  // Сообщения об ошибках
  const errorMessages: Record<ErrorType, { title: string; message: string; icon: string }> = {
    payment_failed: {
      title: 'Платеж не прошел',
      message: 'К сожалению, при проведении платежа возникла ошибка. Пожалуйста, попробуйте снова или выберите другой способ оплаты.',
      icon: '❌',
    },
    payment_cancelled: {
      title: 'Платеж отменен',
      message: 'Вы отменили платеж. Вы можете вернуться и попробовать оплатить снова в любое время.',
      icon: '🚫',
    },
    payment_expired: {
      title: 'Время платежа истекло',
      message: 'Время ожидания платежа истекло. Пожалуйста, начните процесс оплаты заново.',
      icon: '⏰',
    },
    unknown: {
      title: 'Неизвестная ошибка',
      message: 'Произошла неизвестная ошибка. Пожалуйста, попробуйте снова или свяжитесь с поддержкой.',
      icon: '⚠️',
    },
  }

  const error = errorMessages[errorType]

  const handleRetryPayment = () => {
    // Возвращаемся на страницу регистрации
    navigate('/register')
  }

  const handleContactSupport = () => {
    // Открываем email клиента
    window.location.href = 'mailto:support@barber-saas.com'
  }

  return (
    <div className="payment-error-page">
      <div className="payment-error-container">
        <div className="error-icon">{error.icon}</div>

        <h1 className="error-title">{error.title}</h1>

        <div className="error-message">
          <p>{error.message}</p>
          {paymentId && (
            <p className="error-details">
              ID платежа: <code>{paymentId}</code>
            </p>
          )}
        </div>

        <div className="error-suggestions">
          <h3>Что можно сделать?</h3>
          <ul className="suggestions-list">
            <li>🔄 Попробовать оплатить снова</li>
            <li>💳 Проверить баланс карты</li>
            <li>🌐 Убедиться, что интернет работает</li>
            <li>📧 Связаться с поддержкой</li>
          </ul>
        </div>

        <div className="action-buttons">
          <button
            className="action-button primary"
            onClick={handleRetryPayment}
          >
            🔄 Попробовать снова
          </button>

          <button
            className="action-button secondary"
            onClick={handleContactSupport}
          >
            📧 Связаться с поддержкой
          </button>

          <button
            className="action-button tertiary"
            onClick={() => navigate('/')}
          >
            🏠 На главную
          </button>
        </div>

        <div className="help-section">
          <h3>Нужна помощь?</h3>
          <div className="help-options">
            <div className="help-option">
              <div className="help-option-icon">📖</div>
              <div className="help-option-content">
                <h4>Документация</h4>
                <p>Изучите инструкции по оплате</p>
                <a href="/docs/payment" className="help-link">
                  Перейти →
                </a>
              </div>
            </div>

            <div className="help-option">
              <div className="help-option-icon">💬</div>
              <div className="help-option-content">
                <h4>FAQ</h4>
                <p>Частые вопросы об оплате</p>
                <a href="/faq/payment" className="help-link">
                  Перейти →
                </a>
              </div>
            </div>

            <div className="help-option">
              <div className="help-option-icon">📱</div>
              <div className="help-option-content">
                <h4>Telegram поддержка</h4>
                <p>Напишите нам в Telegram</p>
                <a href="https://t.me/autoservice_support" className="help-link">
                  Перейти →
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="error-footer">
          <p className="footer-text">
            💡 Если проблема сохраняется, сделайте скриншот ошибки и отправьте его в поддержку
          </p>
          <p className="footer-small">
            Код ошибки: {errorType.toUpperCase()}
          </p>
        </div>
      </div>
    </div>
  )
}

export default PaymentError

