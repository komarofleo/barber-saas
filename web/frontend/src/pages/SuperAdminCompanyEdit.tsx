/**
 * Страница редактирования компании
 * 
 * Позволяет редактировать:
 * - Основную информацию (название, email, телефон)
 * - Тарифный план
 * - Статус подписки
 * - Разрешение на создание записей
 * - Активность компании
 */

import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Company, CompanyUpdateData, SubscriptionStatus, superAdminApi } from '../api/superAdmin'
import { useSidebar } from '../components/SuperAdminLayout'
import './SuperAdminCompanies.css'

const SuperAdminCompanyEdit: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const companyId = parseInt(id || '0')
  const { sidebarOpen, toggleSidebar } = useSidebar()

  // UI состояния
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Форма редактирования
  const [formData, setFormData] = useState<CompanyUpdateData>({
    name: '',
    email: '',
    phone: '',
    telegram_bot_token: '',
    admin_telegram_id: undefined,
    plan_id: undefined,
    subscription_status: undefined,
    can_create_bookings: true,
    is_active: true,
  })

  // Загрузка данных компании
  useEffect(() => {
    if (companyId) {
      loadCompany()
    }
  }, [companyId])

  const loadCompany = async () => {
    setLoading(true)
    setError(null)
    try {
      const fetchedCompany = await superAdminApi.getCompanyById(companyId)
      setCompany(fetchedCompany)
      setFormData({
        name: fetchedCompany.name,
        email: fetchedCompany.email,
        phone: fetchedCompany.phone || '',
        telegram_bot_token: fetchedCompany.telegram_bot_token || '',
        admin_telegram_id: fetchedCompany.admin_telegram_id || undefined,
        plan_id: fetchedCompany.plan_id || undefined,
        subscription_status: fetchedCompany.subscription_status || undefined,
        can_create_bookings: fetchedCompany.can_create_bookings,
        is_active: fetchedCompany.is_active,
      })
    } catch (err: any) {
      console.error('Ошибка загрузки компании:', err)
      setError(err.response?.data?.detail || 'Не удалось загрузить данные компании')
    } finally {
      setLoading(false)
    }
  }

  // Обработка изменений формы
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked
      setFormData(prev => ({ ...prev, [name]: checked }))
    } else if (name === 'plan_id' || name === 'admin_telegram_id') {
      setFormData(prev => ({ ...prev, [name]: value ? parseInt(value, 10) : undefined }))
    } else if (name === 'subscription_status') {
      setFormData(prev => ({ ...prev, [name]: value ? (value as SubscriptionStatus) : undefined }))
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
    }
  }

  // Сохранение изменений
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      await superAdminApi.updateCompany(companyId, formData)
      setSuccess('Компания успешно обновлена!')
      setTimeout(() => {
        navigate(`/super-admin/companies/${companyId}`)
      }, 1500)
    } catch (err: any) {
      console.error('Ошибка обновления компании:', err)
      setError(err.response?.data?.detail || 'Не удалось обновить компанию')
    } finally {
      setSaving(false)
    }
  }

  // Отмена редактирования
  const handleCancel = () => {
    navigate(`/super-admin/companies/${companyId}`)
  }

  if (loading) {
    return (
      <div className="super-admin-companies-page">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Загрузка данных компании...</p>
        </div>
      </div>
    )
  }

  if (!company) {
    return (
      <div className="super-admin-companies-page">
        <div className="error-state">
          <div className="error-icon">❌</div>
          <p>Компания не найдена</p>
          <button onClick={() => navigate('/super-admin/companies')} className="retry-button">
            Вернуться к списку
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="super-admin-companies-page">
      <div className="companies-container">
        {/* Заголовок страницы */}
        <div className="page-header">
          <button
            className="dashboard-menu-toggle"
            onClick={toggleSidebar}
            title={sidebarOpen ? 'Свернуть меню' : 'Развернуть меню'}
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
          <div className="header-content">
            <h1 className="page-title">✏️ Редактирование компании</h1>
            <p className="page-subtitle">
              Изменение информации о компании "{company.name}"
            </p>
          </div>
        </div>

        {/* Сообщения об ошибках и успехе */}
        {error && (
          <div className="error-state" style={{ marginBottom: '24px' }}>
            <div className="error-icon">❌</div>
            <p>{error}</p>
          </div>
        )}

        {success && (
          <div style={{
            background: '#d4edda',
            border: '1px solid #c3e6cb',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '24px',
            color: '#155724'
          }}>
            ✅ {success}
          </div>
        )}

        {/* Форма редактирования */}
        <form onSubmit={handleSubmit} className="edit-company-form">
          <div className="form-section">
            <h3 className="section-title">Основная информация</h3>
            
            <div className="form-group">
              <label htmlFor="name" className="form-label">
                Название компании *
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className="form-input"
                required
                placeholder="Введите название компании"
              />
            </div>

            <div className="form-group">
              <label htmlFor="email" className="form-label">
                Email *
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="form-input"
                required
                placeholder="email@example.com"
              />
            </div>

            <div className="form-group">
              <label htmlFor="phone" className="form-label">
                Телефон
              </label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                className="form-input"
                placeholder="+7 (999) 123-45-67"
              />
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Telegram бот</h3>
            
            <div className="form-group">
              <label htmlFor="telegram_bot_token" className="form-label">
                Токен Telegram бота
              </label>
              <input
                type="text"
                id="telegram_bot_token"
                name="telegram_bot_token"
                value={formData.telegram_bot_token}
                onChange={handleChange}
                className="form-input"
                placeholder="8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4"
                minLength={30}
                maxLength={500}
              />
              <div className="field-hint" style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>
                Получите токен через @BotFather в Telegram. При изменении токена бот будет перезапущен.
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="admin_telegram_id" className="form-label">
                Telegram ID администратора
              </label>
              <input
                type="number"
                id="admin_telegram_id"
                name="admin_telegram_id"
                value={formData.admin_telegram_id || ''}
                onChange={handleChange}
                className="form-input"
                placeholder="329621295"
                min={1}
              />
              <div className="field-hint" style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>
                Telegram ID владельца для получения уведомлений
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Подписка и тариф</h3>
            
            <div className="form-group">
              <label htmlFor="plan_id" className="form-label">
                Тарифный план
              </label>
              <select
                id="plan_id"
                name="plan_id"
                value={formData.plan_id || ''}
                onChange={handleChange}
                className="form-select"
              >
                <option value="">Не выбран</option>
                <option value="1">Базовый (1,000 ₽/мес)</option>
                <option value="2">Стандарт (2,000 ₽/мес)</option>
                <option value="3">Бизнес (3,000 ₽/мес)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="subscription_status" className="form-label">
                Статус подписки
              </label>
              <select
                id="subscription_status"
                name="subscription_status"
                value={formData.subscription_status || ''}
                onChange={handleChange}
                className="form-select"
              >
                <option value="">Не установлен</option>
                <option value="active">Активна</option>
                <option value="expired">Истекла</option>
                <option value="blocked">Заблокирована</option>
                <option value="pending">В ожидании</option>
              </select>
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Настройки</h3>
            
            <div className="form-group">
              <label className="form-checkbox-label">
                <input
                  type="checkbox"
                  name="can_create_bookings"
                  checked={formData.can_create_bookings}
                  onChange={handleChange}
                  className="form-checkbox"
                />
                <span>Разрешить создание записей</span>
              </label>
            </div>

            <div className="form-group">
              <label className="form-checkbox-label">
                <input
                  type="checkbox"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                  className="form-checkbox"
                />
                <span>Компания активна</span>
              </label>
            </div>
          </div>

          {/* Кнопки действий */}
          <div className="form-actions">
            <button
              type="button"
              onClick={handleCancel}
              className="form-button secondary"
              disabled={saving}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="form-button primary"
              disabled={saving}
            >
              {saving ? 'Сохранение...' : 'Сохранить изменения'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default SuperAdminCompanyEdit

