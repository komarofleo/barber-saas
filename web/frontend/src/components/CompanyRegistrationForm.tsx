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
import { useNavigate } from 'react-router-dom'
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
      description: 'Основная информация о вашем автосервисе',
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
        message: 'Название автосервиса должно содержать минимум 3 символа',
      })
    } else if (formData.name.length > 255) {
      newErrors.push({
        field: 'name',
        message: 'Название автосервиса не должно превышать 255 символов',
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

    // Валидация токена бота
    if (!formData.telegram_bot_token || formData.telegram_bot_token.length < 50) {
      newErrors.push({
        field: 'telegram_bot_token',
        message: 'Токен бота должен содержать минимум 50 символов',
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

    // Конвертация admin_telegram_id в число
    if (name === 'admin_telegram_id') {
      const numValue = value === '' ? 0 : parseInt(value, 10)
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

    // Валидация последнего шага
    const validationErrors = validateStep3()
    if (validationErrors.length > 0) {
      return
    }

    setSubmitting(true)
    setLoading(true)
    setErrors([])

    try {
      const result = await publicApi.registerCompany(formData)

      // Успешная регистрация - перенаправление на оплату
      if (result.confirmation_url) {
        setSuccessMessage('Регистрация успешна! Перенаправление на оплату...')
        setTimeout(() => {
          window.location.href = result.confirmation_url
        }, 2000)
      } else {
        setErrors([{ field: 'general', message: result.message || 'Неизвестная ошибка' }])
      }
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
      <div className="registration-header">
        <h1 className="registration-title">Регистрация автосервиса</h1>
        <p className="registration-subtitle">
          Заполните форму для создания вашей учетной записи в SaaS платформе
        </p>
      </div>

      {/* Индикатор шагов */}
      <FormStepIndicator steps={steps} currentStep={currentStep} />

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

      {/* Форма */}
      <form onSubmit={handleSubmit} className="registration-form-content">
        {/* Шаг 1: Данные компании */}
        {currentStep === 0 && (
          <div className="form-step-content">
            <FormField
              label="Название автосервиса"
              name="name"
              type="text"
              placeholder="ООО 'Точка'"
              value={formData.name}
              onChange={handleInputChange}
              required
              error={getFieldError('name')}
              min={3}
              max={255}
            />
            <FormField
              label="Email"
              name="email"
              type="email"
              placeholder="admin@avtoservis.ru"
              value={formData.email}
              onChange={handleInputChange}
              required
              error={getFieldError('email')}
            />
          </div>
        )}

        {/* Шаг 2: Телефон и бот */}
        {currentStep === 1 && (
          <div className="form-step-content">
            <FormField
              label="Телефон"
              name="phone"
              type="tel"
              placeholder="+79001234567"
              value={formData.phone}
              onChange={handleInputChange}
              required
              error={getFieldError('phone')}
              hint="Формат: +7XXXXXXXXXX (10 цифр)"
            />
            <FormField
              label="Токен Telegram бота"
              name="telegram_bot_token"
              type="text"
              placeholder="8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4"
              value={formData.telegram_bot_token}
              onChange={handleInputChange}
              required
              error={getFieldError('telegram_bot_token')}
              hint="Получите токен через @BotFather в Telegram"
              min={50}
              max={500}
            />
            <FormField
              label="Telegram ID владельца"
              name="admin_telegram_id"
              type="number"
              placeholder="329621295"
              value={formData.admin_telegram_id}
              onChange={handleInputChange}
              required
              error={getFieldError('admin_telegram_id')}
              hint="Ваш Telegram ID для получения уведомлений"
              min={1}
            />
          </div>
        )}

        {/* Шаг 3: Выбор тарифа */}
        {currentStep === 2 && (
          <div className="form-step-content">
            <PlanSelection
              selectedPlanId={formData.plan_id}
              onPlanSelect={handlePlanSelect}
            />
          </div>
        )}

        {/* Кнопки навигации */}
        <div className="form-navigation">
          {currentStep > 0 && (
            <button
              type="button"
              className="nav-button prev-button"
              onClick={handlePrevStep}
            >
              ← Назад
            </button>
          )}
          
          {currentStep < steps.length - 1 ? (
            <button
              type="button"
              className="nav-button next-button"
              onClick={handleNextStep}
            >
              Далее →
            </button>
          ) : (
            <button
              type="submit"
              className="nav-button submit-button"
              disabled={submitting || loading}
            >
              {submitting ? 'Регистрация...' : 'Зарегистрироваться и оплатить'}
            </button>
          )}
        </div>
      </form>

      {/* Информация внизу */}
      <div className="registration-footer">
        <p className="footer-text">
          Уже есть аккаунт?{' '}
          <a href="/login" className="footer-link">
            Войти
          </a>
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

