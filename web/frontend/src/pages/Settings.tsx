import { useState, useEffect } from 'react'
import {
  settingsApi,
  Setting,
  CompanyCredentials,
  CompanyCredentialsUpdateRequest,
} from '../api/settings'
import './Settings.css'

function Settings() {
  const [settings, setSettings] = useState<Setting[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [formValues, setFormValues] = useState<Record<string, string>>({})
  const [botWelcomeFile, setBotWelcomeFile] = useState<File | null>(null)
  const [botAboutFile, setBotAboutFile] = useState<File | null>(null)
  const [companyCredentials, setCompanyCredentials] = useState<CompanyCredentials | null>(null)
  const [companyCredentialsForm, setCompanyCredentialsForm] = useState({
    email: '',
    name: '',
    admin_telegram_id: '',
    telegram_bot_token: '',
  })

  useEffect(() => {
    loadSettings()
    loadCompanyCredentials()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await settingsApi.getSettings()
      setSettings(data)
      const valuesMap: Record<string, string> = {}
      data.forEach((setting) => {
        valuesMap[setting.key] = setting.value || ''
      })
      setFormValues(valuesMap)
    } catch (error: any) {
      console.error('Ошибка загрузки настроек:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      } else {
        setError('Не удалось загрузить настройки')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadCompanyCredentials = async () => {
    try {
      const data = await settingsApi.getCompanyCredentials()
      setCompanyCredentials(data)
      setCompanyCredentialsForm({
        email: data.email || '',
        name: data.name || '',
        admin_telegram_id: data.admin_telegram_id ? String(data.admin_telegram_id) : '',
        telegram_bot_token: data.telegram_bot_token || '',
      })
    } catch (error: any) {
      console.error('Ошибка загрузки данных компании:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      } else {
        setError(error.response?.data?.detail || 'Не удалось загрузить данные компании')
      }
    }
  }

  const handleUpdate = async (key: string, value: string) => {
    try {
      setSaving(key)
      setError(null)
      await settingsApi.updateSetting(key, { value })
      await loadSettings()
      alert('Настройка успешно обновлена')
    } catch (error: any) {
      console.error('Ошибка обновления настройки:', error)
      setError(error.response?.data?.detail || 'Не удалось обновить настройку')
      alert('Не удалось обновить настройку')
    } finally {
      setSaving(null)
    }
  }

  const getSettingValue = (key: string): string => {
    if (key in formValues) {
      return formValues[key]
    }
    const setting = settings.find(s => s.key === key)
    return setting?.value || ''
  }

  const handleTimeChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleTimeBlur = (key: string) => {
    const value = formValues[key] || ''
    if (/^\d{2}:\d{2}$/.test(value)) {
      handleUpdate(key, value)
    }
  }

  const handleNumberChange = (key: string, value: string) => {
    if (value === '' || /^\d+$/.test(value)) {
      setFormValues((prev) => ({ ...prev, [key]: value }))
    }
  }

  const handleNumberBlur = (key: string) => {
    const value = formValues[key] || ''
    if (value !== '' && /^\d+$/.test(value)) {
      handleUpdate(key, value)
    }
  }

  const handleBooleanChange = (key: string, checked: boolean) => {
    const value = checked.toString()
    setFormValues((prev) => ({ ...prev, [key]: value }))
    handleUpdate(key, value)
  }

  const handleTextChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleTextBlur = (key: string) => {
    const value = formValues[key] ?? ''
    handleUpdate(key, value)
  }

  const companyFields = [
    'company_contact_full_name',
    'company_phone',
    'company_name',
    'company_inn',
    'company_address',
    'company_bank_details',
  ]

  const handleCompanySave = async () => {
    try {
      setSaving('company_form')
      setError(null)
      for (const key of companyFields) {
        const value = formValues[key] ?? ''
        await settingsApi.updateSetting(key, { value })
      }
      await loadSettings()
      alert('Данные компании сохранены')
    } catch (error: any) {
      console.error('Ошибка сохранения данных компании:', error)
      setError(error.response?.data?.detail || 'Не удалось сохранить данные компании')
      alert('Не удалось сохранить данные компании')
    } finally {
      setSaving(null)
    }
  }

  const getFileNameFromPath = (value: string) => {
    if (!value) return ''
    const parts = value.split('/')
    return parts[parts.length - 1]
  }

  const handleBotSave = async () => {
    try {
      setSaving('bot_form')
      setError(null)
      await settingsApi.updateSetting('bot_welcome_text', { value: formValues['bot_welcome_text'] || '' })
      await settingsApi.updateSetting('bot_about_text', { value: formValues['bot_about_text'] || '' })
      if (botWelcomeFile) {
        await settingsApi.uploadSettingFile('bot_welcome_photo', botWelcomeFile)
      }
      if (botAboutFile) {
        await settingsApi.uploadSettingFile('bot_about_photo', botAboutFile)
      }
      await loadSettings()
      setBotWelcomeFile(null)
      setBotAboutFile(null)
      alert('Настройки бота сохранены')
    } catch (error: any) {
      console.error('Ошибка сохранения настроек бота:', error)
      setError(error.response?.data?.detail || 'Не удалось сохранить настройки бота')
      alert('Не удалось сохранить настройки бота')
    } finally {
      setSaving(null)
    }
  }

  const handleMasterSpecializationsSave = async () => {
    try {
      setSaving('master_specializations')
      setError(null)
      const value = formValues['master_specializations'] ?? ''
      await settingsApi.updateSetting('master_specializations', { value })
      await loadSettings()
      alert('Список специализаций сохранен')
    } catch (error: any) {
      console.error('Ошибка сохранения специализаций:', error)
      setError(error.response?.data?.detail || 'Не удалось сохранить специализации')
      alert('Не удалось сохранить специализации')
    } finally {
      setSaving(null)
    }
  }

  const handleCompanyCredentialsSave = async () => {
    try {
      setSaving('company_credentials')
      setError(null)
      const payload: CompanyCredentialsUpdateRequest = {}
      const name = companyCredentialsForm.name.trim()
      if (name && name !== companyCredentials?.name) {
        payload.name = name
      }
      const adminTelegramRaw = companyCredentialsForm.admin_telegram_id.trim()
      if (adminTelegramRaw) {
        const parsed = Number(adminTelegramRaw)
        if (!Number.isFinite(parsed) || parsed <= 0) {
          setError('Некорректный Telegram ID администратора')
          return
        }
        if (!companyCredentials || parsed !== companyCredentials.admin_telegram_id) {
          payload.admin_telegram_id = parsed
        }
      }
      const token = companyCredentialsForm.telegram_bot_token.trim()
      if (token && token !== companyCredentials?.telegram_bot_token) {
        payload.telegram_bot_token = token
      }
      if (Object.keys(payload).length === 0) {
        alert('Нет изменений для сохранения')
        return
      }
      const updated = await settingsApi.updateCompanyCredentials(payload)
      setCompanyCredentials(updated)
      setCompanyCredentialsForm({
        email: updated.email || '',
        name: updated.name || '',
        admin_telegram_id: updated.admin_telegram_id ? String(updated.admin_telegram_id) : '',
        telegram_bot_token: updated.telegram_bot_token || '',
      })
      alert('Данные компании обновлены')
    } catch (error: any) {
      console.error('Ошибка обновления данных компании:', error)
      setError(error.response?.data?.detail || 'Не удалось обновить данные компании')
      alert('Не удалось обновить данные компании')
    } finally {
      setSaving(null)
    }
  }

  const handleSendCredentials = async () => {
    try {
      setSaving('company_credentials_send')
      setError(null)
      const response = await settingsApi.sendCompanyCredentials()
      alert(response.message)
    } catch (error: any) {
      console.error('Ошибка отправки данных доступа:', error)
      setError(error.response?.data?.detail || 'Не удалось отправить данные доступа')
      alert('Не удалось отправить данные доступа')
    } finally {
      setSaving(null)
    }
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header-simple">
          <h1>Настройки</h1>
        </div>
        <div className="loading">Загрузка настроек...</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Настройки</h1>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="settings-content">
        {/* График работы */}
        <div className="settings-section">
          <h2>📅 График работы</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">Время начала работы</span>
                <span className="setting-description">Время начала рабочего дня</span>
              </label>
              <input
                type="time"
                value={getSettingValue('work_start_time')}
                onChange={(e) => handleTimeChange('work_start_time', e.target.value)}
                onBlur={() => handleTimeBlur('work_start_time')}
                className="setting-input"
                disabled={saving === 'work_start_time'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Время окончания работы</span>
                <span className="setting-description">Время окончания рабочего дня</span>
              </label>
              <input
                type="time"
                value={getSettingValue('work_end_time')}
                onChange={(e) => handleTimeChange('work_end_time', e.target.value)}
                onBlur={() => handleTimeBlur('work_end_time')}
                className="setting-input"
                disabled={saving === 'work_end_time'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Длительность слота (минуты)</span>
                <span className="setting-description">Длительность одного временного слота для записи</span>
              </label>
              <select
                value={getSettingValue('slot_duration')}
                onChange={(e) => {
                  handleNumberChange('slot_duration', e.target.value)
                  handleUpdate('slot_duration', e.target.value)
                }}
                className="setting-input"
                disabled={saving === 'slot_duration'}
              >
                <option value="30">30 минут</option>
                <option value="60">60 минут</option>
              </select>
            </div>
          </div>
        </div>

        {/* Уведомления */}
        <div className="settings-section">
          <h2>🔔 Уведомления</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">Время напоминания за день</span>
                <span className="setting-description">Время отправки напоминания клиенту за день до записи</span>
              </label>
              <input
                type="time"
                value={getSettingValue('reminder_day_before_time')}
                onChange={(e) => handleTimeChange('reminder_day_before_time', e.target.value)}
                onBlur={() => handleTimeBlur('reminder_day_before_time')}
                className="setting-input"
                disabled={saving === 'reminder_day_before_time'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Напоминание за час</span>
                <span className="setting-description">Отправлять ли напоминание клиенту за час до записи</span>
              </label>
              <label className="checkbox-setting">
                <input
                  type="checkbox"
                  checked={getSettingValue('reminder_hour_before') === 'true'}
                  onChange={(e) => handleBooleanChange('reminder_hour_before', e.target.checked)}
                  disabled={saving === 'reminder_hour_before'}
                />
                <span>Включено</span>
              </label>
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Задержка уведомления админу (минуты)</span>
                <span className="setting-description">Задержка перед отправкой уведомления администратору о новой записи</span>
              </label>
              <input
                type="number"
                min="0"
                value={getSettingValue('notify_admin_delay_minutes')}
                onChange={(e) => handleNumberChange('notify_admin_delay_minutes', e.target.value)}
                onBlur={() => handleNumberBlur('notify_admin_delay_minutes')}
                className="setting-input"
                disabled={saving === 'notify_admin_delay_minutes'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Время отправки лист-наряда</span>
                <span className="setting-description">Время отправки лист-наряда мастерам на день</span>
              </label>
              <input
                type="time"
                value={getSettingValue('work_order_time')}
                onChange={(e) => handleTimeChange('work_order_time', e.target.value)}
                onBlur={() => handleTimeBlur('work_order_time')}
                className="setting-input"
                disabled={saving === 'work_order_time'}
              />
            </div>
          </div>
        </div>

        {/* Системные настройки */}
        <div className="settings-section">
          <h2>⚙️ Системные настройки</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">Прием заявок</span>
                <span className="setting-description">Глобальная блокировка приема новых заявок</span>
              </label>
              <label className="checkbox-setting">
                <input
                  type="checkbox"
                  checked={getSettingValue('accepting_bookings') === 'true'}
                  onChange={(e) => handleBooleanChange('accepting_bookings', e.target.checked)}
                  disabled={saving === 'accepting_bookings'}
                />
                <span>Включено</span>
              </label>
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Учитывать специализацию мастеров</span>
                <span className="setting-description">Учитывать специализацию мастеров при назначении записей</span>
              </label>
              <label className="checkbox-setting">
                <input
                  type="checkbox"
                  checked={getSettingValue('enable_master_specialization') === 'true'}
                  onChange={(e) => handleBooleanChange('enable_master_specialization', e.target.checked)}
                  disabled={saving === 'enable_master_specialization'}
                />
                <span>Включено</span>
              </label>
            </div>
          </div>
        </div>

        {/* Мастера */}
        <div className="settings-section">
          <h2>👤 Мастера</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">Список специализаций</span>
                <span className="setting-description">По одной специализации в строке</span>
              </label>
              <textarea
                value={getSettingValue('master_specializations')}
                onChange={(e) => handleTextChange('master_specializations', e.target.value)}
                className="setting-input"
                rows={6}
                disabled={saving === 'master_specializations'}
              />
            </div>
          </div>
          <div className="settings-actions">
            <button
              type="button"
              className="primary-button"
              onClick={handleMasterSpecializationsSave}
              disabled={saving === 'master_specializations'}
            >
              {saving === 'master_specializations' ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>

        {/* Настройки бота */}
        <div className="settings-section">
          <h2>🤖 Бот: приветствие и О нас</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">Текст приветствия</span>
                <span className="setting-description">Сообщение при /start</span>
              </label>
              <textarea
                value={getSettingValue('bot_welcome_text')}
                onChange={(e) => handleTextChange('bot_welcome_text', e.target.value)}
                className="setting-input"
                rows={4}
                disabled={saving === 'bot_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Картинка приветствия</span>
                <span className="setting-description">PNG/JPG/WEBP</span>
              </label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => setBotWelcomeFile(e.target.files?.[0] || null)}
                className="setting-input"
                disabled={saving === 'bot_form'}
              />
              {getSettingValue('bot_welcome_photo') && (
                <div className="setting-description">
                  Текущий файл: {getFileNameFromPath(getSettingValue('bot_welcome_photo'))}
                </div>
              )}
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Текст «О нас»</span>
                <span className="setting-description">Сообщение по кнопке «О нас»</span>
              </label>
              <textarea
                value={getSettingValue('bot_about_text')}
                onChange={(e) => handleTextChange('bot_about_text', e.target.value)}
                className="setting-input"
                rows={4}
                disabled={saving === 'bot_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Картинка «О нас»</span>
                <span className="setting-description">PNG/JPG/WEBP</span>
              </label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => setBotAboutFile(e.target.files?.[0] || null)}
                className="setting-input"
                disabled={saving === 'bot_form'}
              />
              {getSettingValue('bot_about_photo') && (
                <div className="setting-description">
                  Текущий файл: {getFileNameFromPath(getSettingValue('bot_about_photo'))}
                </div>
              )}
            </div>
          </div>
          <div className="settings-actions">
            <button
              type="button"
              className="primary-button"
              onClick={handleBotSave}
              disabled={saving === 'bot_form'}
            >
              {saving === 'bot_form' ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>

        {/* Доступ и Telegram */}
        <div className="settings-section">
          <h2>🔑 Доступ и Telegram</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">Логин (Email)</span>
                <span className="setting-description">Email для входа в систему</span>
              </label>
              <input
                type="email"
                value={companyCredentialsForm.email}
                className="setting-input"
                disabled
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Telegram ID администратора</span>
                <span className="setting-description">ID для получения уведомлений</span>
              </label>
              <input
                type="text"
                value={companyCredentialsForm.admin_telegram_id}
                onChange={(e) =>
                  setCompanyCredentialsForm((prev) => ({
                    ...prev,
                    admin_telegram_id: e.target.value,
                  }))
                }
                className="setting-input"
                disabled={saving === 'company_credentials'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">API токен Telegram бота</span>
                <span className="setting-description">Токен из @BotFather</span>
              </label>
              <input
                type="text"
                value={companyCredentialsForm.telegram_bot_token}
                onChange={(e) =>
                  setCompanyCredentialsForm((prev) => ({
                    ...prev,
                    telegram_bot_token: e.target.value,
                  }))
                }
                className="setting-input"
                disabled={saving === 'company_credentials'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Название компании (системное)</span>
                <span className="setting-description">Отображается в системе</span>
              </label>
              <input
                type="text"
                value={companyCredentialsForm.name}
                onChange={(e) =>
                  setCompanyCredentialsForm((prev) => ({
                    ...prev,
                    name: e.target.value,
                  }))
                }
                className="setting-input"
                disabled={saving === 'company_credentials'}
              />
            </div>
          </div>
          <div className="settings-actions">
            <button
              type="button"
              className="primary-button"
              onClick={handleCompanyCredentialsSave}
              disabled={saving === 'company_credentials'}
            >
              {saving === 'company_credentials' ? 'Сохранение...' : 'Сохранить'}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={handleSendCredentials}
              disabled={saving === 'company_credentials_send'}
            >
              {saving === 'company_credentials_send'
                ? 'Отправка...'
                : 'Сбросить пароль и отправить в Telegram'}
            </button>
          </div>
          <div className="settings-hint">
            При нажатии кнопки пароль будет сброшен, а новые данные отправлены в Telegram.
          </div>
        </div>

        {/* Данные компании */}
        <div className="settings-section">
          <h2>🏢 Данные компании</h2>
          <div className="settings-grid">
            <div className="setting-item">
              <label>
                <span className="setting-label">ФИО ответственного лица</span>
                <span className="setting-description">ФИО для договоров и контактов</span>
              </label>
              <input
                type="text"
                value={getSettingValue('company_contact_full_name')}
                onChange={(e) => handleTextChange('company_contact_full_name', e.target.value)}
                className="setting-input"
                disabled={saving === 'company_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Телефон</span>
                <span className="setting-description">Контактный номер компании</span>
              </label>
              <input
                type="tel"
                value={getSettingValue('company_phone')}
                onChange={(e) => handleTextChange('company_phone', e.target.value)}
                className="setting-input"
                disabled={saving === 'company_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Название компании</span>
                <span className="setting-description">Название для договоров и счетов</span>
              </label>
              <input
                type="text"
                value={getSettingValue('company_name')}
                onChange={(e) => handleTextChange('company_name', e.target.value)}
                className="setting-input"
                disabled={saving === 'company_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">ИНН</span>
                <span className="setting-description">ИНН компании</span>
              </label>
              <input
                type="text"
                value={getSettingValue('company_inn')}
                onChange={(e) => handleTextChange('company_inn', e.target.value)}
                className="setting-input"
                disabled={saving === 'company_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Адрес</span>
                <span className="setting-description">Юридический или фактический адрес</span>
              </label>
              <input
                type="text"
                value={getSettingValue('company_address')}
                onChange={(e) => handleTextChange('company_address', e.target.value)}
                className="setting-input"
                disabled={saving === 'company_form'}
              />
            </div>
            <div className="setting-item">
              <label>
                <span className="setting-label">Банковские реквизиты</span>
                <span className="setting-description">Р/с, БИК, банк, к/с и т.д.</span>
              </label>
              <textarea
                value={getSettingValue('company_bank_details')}
                onChange={(e) => handleTextChange('company_bank_details', e.target.value)}
                className="setting-input"
                disabled={saving === 'company_form'}
                rows={4}
              />
            </div>
          </div>
          <div className="settings-actions">
            <button
              type="button"
              className="primary-button"
              onClick={handleCompanySave}
              disabled={saving === 'company_form'}
            >
              {saving === 'company_form' ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
