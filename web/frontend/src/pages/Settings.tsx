import { useState, useEffect } from 'react'
import { settingsApi, Setting } from '../api/settings'
import './Settings.css'

function Settings() {
  const [settings, setSettings] = useState<Setting[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await settingsApi.getSettings()
      setSettings(data)
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
    const setting = settings.find(s => s.key === key)
    return setting?.value || ''
  }

  const handleTimeChange = (key: string, value: string) => {
    handleUpdate(key, value)
  }

  const handleNumberChange = (key: string, value: string) => {
    if (value === '' || /^\d+$/.test(value)) {
      handleUpdate(key, value)
    }
  }

  const handleBooleanChange = (key: string, checked: boolean) => {
    handleUpdate(key, checked.toString())
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1>Настройки</h1>
          </div>
        </div>
        <div className="loading">Загрузка настроек...</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Настройки</h1>
        </div>
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
                onChange={(e) => handleNumberChange('slot_duration', e.target.value)}
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
      </div>
    </div>
  )
}

export default Settings
