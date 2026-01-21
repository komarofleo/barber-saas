/**
 * Улучшенная форма регистрации компании
 * 
 * Включает:
 * - Пошаговый процесс (шаг 1: данные, шаг 2: тариф)
 * - Валидацию на каждом шаге
 * - Автоматическое форматирование телефона
 * - Проверку токена бота
 * - Красивую анимацию переходов
 */

import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { CompanyRegistration, Plan, publicApi } from '../api/public'
import PlanSelection from './PlanSelection'
import './PlanCard.css'
import './PlanSelection.css'

// ==================== Интерфейсы ====================

interface ValidationError {
  field: string
  message: string
}

interface FormStep {
  step: number
  title: string
  description: string
}

// ==================== Компоненты ====================

const FormStepIndicator: React.FC<{
  steps: FormStep[]
  currentStep: number
}> = ({ steps, currentStep }) => {
  return (
    <div className="form-steps-indicator">
      {steps.map((step, index) => (
        <div
          key={index}
          className={`step-item ${index <= currentStep ? 'active' : ''} ${
            index === currentStep ? 'current' : ''
          }`}
        >
          <div className="step-number">{index + 1}</div>
          <div className="step-label">
            <div className="step-title">{step.title}</div>
            <div className="step-desc">{step.description}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

const FormField: React.FC<{
  label: string
  name: string
  type?: string
  placeholder?: string
  value: string | number
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  required?: boolean
  error?: string
  hint?: string
  min?: number
  max?: number
}> = ({
  label,
  name,
  type = 'text',
  placeholder,
  value,
  onChange,
  required = false,
  error,
  hint,
  min,
  max,
}) => {
  return (
    <div className="form-field">
      <label htmlFor={name} className="field-label">
        {label}
        {required && <span className="required-mark">*</span>}
      </label>
      <input
        type={type}
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        min={min}
        max={max}
        className={`field-input ${error ? 'error' : ''}`}
      />
      {error && <div className="field-error">{error}</div>}
      {hint && <div className="field-hint">{hint}</div>}
    </div>
  )
}

const SuccessNotification: React.FC<{
  message: string
  onClose: () => void
}> = ({ message, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className="success-notification">
      <span className="success-icon">✓</span>
      <span className="success-message">{message}</span>
      <button className="success-close" onClick={onClose}>
        ×
      </button>
    </div>
  )
}

// ==================== Основной компонент ====================

const CompanyRegistrationForm: React.FC = () => {
  const navigate = useNavigate()

  // Состояния формы
  const [formData, setFormData] = useState<CompanyRegistration>({
    name: '',
    email: '',
    phone: '+7',
    telegram_bot_token: '',
    admin_telegram_id: 0,
    plan_id: 0,
  })

  // UI состояния
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [errors, setErrors] = useState<ValidationError[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [successMessage, setSuccessMessage] = useState<string>('')
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)

  // Шаги формы
  const steps: FormStep[] = [
    {
      step: 1,
      title: 'Данные компании',
      description: 'Основная информация о вашем салоне красоты',
    },
    {
      step: 2,
      title: 'Телефон и бот',
      description: 'Контактные данные и настройка Telegram бота',
    },
    {
      step: 3,
      title: 'Выбор тарифа',
      description: 'Подберите оптимальный план',
    },
  ]

  // ==================== Валидация ====================

  const validateStep1 = (): ValidationError[] => {
    const newErrors: ValidationError[] = []

    // Валидация названия
    if (!formData.name || formData.name.length < 3) {
      newErrors.push({
        field: 'name',
        message: 'Название салона красоты должно содержать минимум 3 символа',
      })
    } else if (formData.name.length > 255) {
      newErrors.push({
        field: 'name',
        message: 'Название салона красоты не должно превышать 255 символов',
      })
    }

    // Валидация email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!formData.email || !emailRegex.test(formData.email)) {
      newErrors.push({
        field: 'email',
        message: 'Пожалуйста, введите корректный email',
      })
    }

    setErrors(newErrors)
    return newErrors
  }

  const validateStep2 = (): ValidationError[] => {
    const newErrors: ValidationError[] = []

    // Валидация телефона
    const phoneRegex = /^\+?7\d{10}$/
    if (!formData.phone || !phoneRegex.test(formData.phone)) {
      newErrors.push({
        field: 'phone',
        message: 'Телефон должен быть в формате +7XXXXXXXXXX',
      })
    }

    // Валидация токена бота (необязательное поле)
    if (formData.telegram_bot_token && formData.telegram_bot_token.trim().length < 40) {
      newErrors.push({
        field: 'telegram_bot_token',
        message: 'Токен бота должен содержать минимум 40 символов',
      })
    }

    // Валидация Telegram ID
    if (!formData.admin_telegram_id || formData.admin_telegram_id < 1) {
      newErrors.push({
        field: 'admin_telegram_id',
        message: 'Пожалуйста, введите корректный Telegram ID',
      })
    }

    setErrors(newErrors)
    return newErrors
  }

  const validateStep3 = (): ValidationError[] => {
    const newErrors: ValidationError[] = []

    if (!formData.plan_id || formData.plan_id < 1) {
      newErrors.push({
        field: 'plan_id',
        message: 'Пожалуйста, выберите тарифный план',
      })
    }

    setErrors(newErrors)
    return newErrors
  }

  // ==================== Обработчики событий ====================

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, value } = e.target

    // Автоматическое форматирование телефона
    if (name === 'phone') {
      let phone = value.replace(/\D/g, '')
      
      if (phone.length > 11) {
        phone = phone.slice(0, 11)
      }
      
      if (phone.length > 0) {
        phone = '+7' + phone.slice(1)
      }
      
      setFormData({ ...formData, [name]: phone })
      return
    }

    // Конвертация admin_telegram_id в число (разрешаем вставку из буфера)
    if (name === 'admin_telegram_id') {
      const digitsOnly = value.replace(/\D/g, '')
      const numValue = digitsOnly === '' ? 0 : parseInt(digitsOnly, 10)
      setFormData({ ...formData, [name]: numValue })
      return
    }

    setFormData({ ...formData, [name]: value })
  }

  const handleNextStep = () => {
    let validationErrors: ValidationError[] = []

    switch (currentStep) {
      case 0:
        validationErrors = validateStep1()
        break
      case 1:
        validationErrors = validateStep2()
        break
      case 2:
        validationErrors = validateStep3()
        break
    }

    if (validationErrors.length > 0) {
      return
    }

    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handlePlanSelect = (planId: number) => {
    setFormData({ ...formData, plan_id: planId })
    
    // Загружаем детали выбраного плана
    publicApi.getPlanById(planId).then(plan => {
      setSelectedPlan(plan)
    })
  }

  // ==================== Отправка формы ====================

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Валидация всех шагов
    const errors1 = validateStep1()
    const errors2 = validateStep2()
    const errors3 = validateStep3()
    
    const allErrors = [...errors1, ...errors2, ...errors3]
    if (allErrors.length > 0) {
      setErrors(allErrors)
      return
    }

    setSubmitting(true)
    setLoading(true)
    setErrors([])

    try {
      const result = await publicApi.registerCompany(formData)

      if (result.success && result.login_email && result.password) {
        sessionStorage.setItem(
          'registration_credentials',
          JSON.stringify({
            login_email: result.login_email,
            password: result.password,
            company_id: result.company_id || null,
            dashboard_url: result.dashboard_url || null,
          })
        )
        setSuccessMessage('Регистрация успешна! Переходим к данным для входа...')
        setTimeout(() => {
          navigate('/register/success')
        }, 1000)
        return
      }

      // Фолбэк на оплату, если возвращена ссылка
      if (result.confirmation_url) {
        setSuccessMessage('Регистрация успешна! Перенаправление на оплату...')
        setTimeout(() => {
          window.location.href = result.confirmation_url as string
        }, 2000)
        return
      }

      setErrors([{ field: 'general', message: result.message || 'Неизвестная ошибка' }])
    } catch (error: any) {
      console.error('Ошибка регистрации:', error)
      setErrors([{ 
        field: 'general', 
        message: error.message || 'Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.' 
      }])
    } finally {
      setLoading(false)
      setSubmitting(false)
    }
  }

  // ==================== Рендеринг ====================

  const getFieldError = (fieldName: string): string => {
    const error = errors.find(err => err.field === fieldName)
    return error ? error.message : ''
  }

  return (
    <div className="company-registration-form">
      {/* Уведомление об успехе */}
      {successMessage && (
        <SuccessNotification
          message={successMessage}
          onClose={() => setSuccessMessage('')}
        />
      )}

      {/* Общие ошибки */}
      {errors.some(err => err.field === 'general') && (
        <div className="general-error">
          {errors
            .filter(err => err.field === 'general')
            .map((err, index) => (
              <div key={index} className="error-message">
                {err.message}
              </div>
            ))}
        </div>
      )}

      {/* Форма в две колонки */}
      <form onSubmit={handleSubmit} className="registration-form-content">
        {/* Заголовок и описание в две колонки */}
        <div className="form-header-grid">
          <div className="form-header-column">
            <h1 className="registration-title">Регистрация салона красоты</h1>
          </div>
          <div className="form-header-column">
            <p className="registration-subtitle">
              Заполните форму для создания вашей учетной записи в SaaS платформе
            </p>
          </div>
        </div>

        {/* Выбор тарифа - на самый верх */}
        <div className="form-section-full">
          <h3 className="section-heading">
            💰 Выбор тарифа
          </h3>
          <PlanSelection
            selectedPlanId={formData.plan_id}
            onPlanSelect={handlePlanSelect}
          />
          
          {/* Дополнительная форма с полями в два столбца после фразы о тарифах */}
          <div className="additional-form-section">
            <div className="additional-form-grid">
              {/* Левая колонка */}
              <div className="additional-form-column">
                <div className="additional-form-field">
                  <label className="additional-field-label">
                    Название салона красоты<span className="required-mark">*</span>
                  </label>
                  <input
                    type="text"
                    name="name"
                    className={`additional-field-input ${getFieldError('name') ? 'error' : ''}`}
                    placeholder="ООО 'Точка'"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    minLength={3}
                    maxLength={255}
                  />
                  {getFieldError('name') && (
                    <div className="field-error">{getFieldError('name')}</div>
                  )}
                </div>
                <div className="additional-form-field">
                  <label className="additional-field-label">
                    Телефон<span className="required-mark">*</span>
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    className={`additional-field-input ${getFieldError('phone') ? 'error' : ''}`}
                    placeholder="+79001234567"
                    value={formData.phone}
                    onChange={handleInputChange}
                    required
                  />
                  <div className="field-hint">Формат: +7XXXXXXXXXX (10 цифр)</div>
                  {getFieldError('phone') && (
                    <div className="field-error">{getFieldError('phone')}</div>
                  )}
                </div>
              </div>

              {/* Правая колонка */}
              <div className="additional-form-column">
                <div className="additional-form-field">
                  <label className="additional-field-label">
                    Email<span className="required-mark">*</span>
                  </label>
                  <input
                    type="email"
                    name="email"
                    className={`additional-field-input ${getFieldError('email') ? 'error' : ''}`}
                    placeholder="admin@avtoservis.ru"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                  />
                  {getFieldError('email') && (
                    <div className="field-error">{getFieldError('email')}</div>
                  )}
                </div>
                <div className="additional-form-field">
                  <label className="additional-field-label">
                    Токен Telegram бота
                  </label>
                  <input
                    type="text"
                    name="telegram_bot_token"
                    className={`additional-field-input ${getFieldError('telegram_bot_token') ? 'error' : ''}`}
                    placeholder="8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4"
                    value={formData.telegram_bot_token}
                    onChange={handleInputChange}
                    minLength={40}
                    maxLength={500}
                  />
                  <div className="field-hint">
                    Можно указать позже в настройках. Получите токен через @BotFather в Telegram
                  </div>
                  {getFieldError('telegram_bot_token') && (
                    <div className="field-error">{getFieldError('telegram_bot_token')}</div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Telegram ID - на всю ширину */}
            <div className="additional-form-field-full">
              <label className="additional-field-label">
                Telegram ID владельца<span className="required-mark">*</span>
              </label>
              <input
                type="text"
                name="admin_telegram_id"
                className={`additional-field-input ${getFieldError('admin_telegram_id') ? 'error' : ''}`}
                placeholder="329621295"
                value={formData.admin_telegram_id ? String(formData.admin_telegram_id) : ''}
                onChange={handleInputChange}
                required
                inputMode="numeric"
                pattern="[0-9]*"
              />
              <div className="field-hint">Ваш Telegram ID для получения уведомлений</div>
              <div className="field-hint">Узнать ваш Telegram ID: бот @userinfobot, отправьте /start</div>
              {getFieldError('admin_telegram_id') && (
                <div className="field-error">{getFieldError('admin_telegram_id')}</div>
              )}
            </div>
          </div>
        </div>

        {/* Кнопка отправки */}
        <div className="form-navigation">
          <button
            type="submit"
            className="nav-button submit-button"
            disabled={submitting || loading}
            style={{ width: '100%' }}
          >
            {submitting ? 'Регистрация...' : 'Зарегистрироваться и оплатить'}
          </button>
        </div>
      </form>

      {/* Информация внизу */}
      <div className="registration-footer">
        <p className="footer-text">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="footer-link">
            Войти
          </Link>
        </p>
        <p className="footer-small-text">
          Нажимая кнопку «Зарегистрироваться», вы соглашаетесь с{' '}
          <a href="/terms" className="footer-link">
            условиями использования
          </a>{' '}
          и{' '}
          <a href="/privacy" className="footer-link">
            политикой конфиденциальности
          </a>
        </p>
      </div>
    </div>
  )
}

export default CompanyRegistrationForm

