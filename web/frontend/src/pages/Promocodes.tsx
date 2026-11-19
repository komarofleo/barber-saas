import { useState, useEffect } from 'react'
import { promocodesApi, Promocode, PromocodeCreateRequest } from '../api/promocodes'
import { servicesApi, Service } from '../api/services'
import { formatMoney } from '../utils/money'
import './Promocodes.css'

function Promocodes() {
  const [promocodes, setPromocodes] = useState<Promocode[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingPromocode, setEditingPromocode] = useState<Promocode | null>(null)
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)
  
  const pageSize = 20

  useEffect(() => {
    loadPromocodes()
  }, [page, filterActive])

  const loadPromocodes = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await promocodesApi.getPromocodes(page, pageSize, filterActive)
      setPromocodes(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки промокодов:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (data: PromocodeCreateRequest) => {
    try {
      await promocodesApi.createPromocode(data)
      setShowCreateModal(false)
      loadPromocodes()
    } catch (error: any) {
      console.error('Ошибка создания промокода:', error)
      alert(error.response?.data?.detail || 'Не удалось создать промокод')
    }
  }

  const handleUpdate = async (promocodeId: number, data: Partial<PromocodeCreateRequest>) => {
    try {
      await promocodesApi.updatePromocode(promocodeId, data)
      setShowEditModal(false)
      setEditingPromocode(null)
      loadPromocodes()
    } catch (error: any) {
      console.error('Ошибка обновления промокода:', error)
      alert(error.response?.data?.detail || 'Не удалось обновить промокод')
    }
  }

  const handleDelete = async (promocodeId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот промокод?')) {
      return
    }
    
    try {
      await promocodesApi.deletePromocode(promocodeId)
      loadPromocodes()
    } catch (error: any) {
      console.error('Ошибка удаления промокода:', error)
      alert('Не удалось удалить промокод')
    }
  }

  const handleEdit = (promocode: Promocode) => {
    setEditingPromocode(promocode)
    setShowEditModal(true)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Промокоды</h1>
      </div>

      <div className="promocodes-controls-bar">
        <div className="filter-group">
          <button
            className={`filter-btn ${filterActive === undefined ? 'active' : ''}`}
            onClick={() => setFilterActive(undefined)}
          >
            Все
          </button>
          <button
            className={`filter-btn ${filterActive === true ? 'active' : ''}`}
            onClick={() => setFilterActive(true)}
          >
            Активные
          </button>
          <button
            className={`filter-btn ${filterActive === false ? 'active' : ''}`}
            onClick={() => setFilterActive(false)}
          >
            Неактивные
          </button>
        </div>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          + Добавить промокод
        </button>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : promocodes.length === 0 ? (
        <div className="empty-state">
          <p>Промокоды не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Код</th>
                  <th>Тип скидки</th>
                  <th>Значение</th>
                  <th>Услуга</th>
                  <th>Мин. сумма</th>
                  <th>Использований</th>
                  <th>Период</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {promocodes.map((promocode) => (
                  <tr key={promocode.id}>
                    <td>{promocode.id}</td>
                    <td><strong>{promocode.code}</strong></td>
                    <td>{promocode.discount_type === 'percent' ? 'Процент' : 'Фиксированная'}</td>
                    <td>
                      {promocode.discount_type === 'percent' 
                        ? `${promocode.discount_value}%` 
                        : `${formatMoney(promocode.discount_value)}`}
                    </td>
                    <td>{promocode.service_name || 'Все услуги'}</td>
                    <td>{formatMoney(promocode.min_amount)}</td>
                    <td>
                      {promocode.current_uses} / {promocode.max_uses || '∞'}
                    </td>
                    <td>
                      {promocode.start_date && promocode.end_date
                        ? `${new Date(promocode.start_date).toLocaleDateString('ru-RU')} - ${new Date(promocode.end_date).toLocaleDateString('ru-RU')}`
                        : promocode.start_date
                        ? `с ${new Date(promocode.start_date).toLocaleDateString('ru-RU')}`
                        : promocode.end_date
                        ? `до ${new Date(promocode.end_date).toLocaleDateString('ru-RU')}`
                        : 'Без ограничений'}
                    </td>
                    <td>
                      <span className={`badge ${promocode.is_active ? 'badge-success' : 'badge-default'}`}>
                        {promocode.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-sm btn-edit" onClick={() => handleEdit(promocode)}>
                          ✏️ Редактировать
                        </button>
                        <button className="btn-sm btn-delete" onClick={() => handleDelete(promocode.id)}>
                          🗑️ Удалить
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination-btn"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                ‹ Назад
              </button>
              <span className="pagination-info">
                Страница {page} из {totalPages} (всего: {total})
              </span>
              <button
                className="pagination-btn"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Вперед ›
              </button>
            </div>
          )}
        </>
      )}

      {showCreateModal && (
        <PromocodeModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {showEditModal && editingPromocode && (
        <PromocodeModal
          promocode={editingPromocode}
          onClose={() => {
            setShowEditModal(false)
            setEditingPromocode(null)
          }}
          onSave={(data) => handleUpdate(editingPromocode.id, data)}
        />
      )}
    </div>
  )
}

interface PromocodeModalProps {
  promocode?: Promocode
  onClose: () => void
  onSave: (data: PromocodeCreateRequest) => void
}

function PromocodeModal({ promocode, onClose, onSave }: PromocodeModalProps) {
  const [services, setServices] = useState<Service[]>([])
  const [formData, setFormData] = useState<PromocodeCreateRequest>({
    code: promocode?.code || '',
    discount_type: promocode?.discount_type || 'percent',
    discount_value: promocode?.discount_value || 0,
    service_id: promocode?.service_id || null,
    min_amount: promocode?.min_amount || 0,
    max_uses: promocode?.max_uses || null,
    start_date: promocode?.start_date || null,
    end_date: promocode?.end_date || null,
    description: promocode?.description || null,
  })

  useEffect(() => {
    loadServices()
  }, [])

  const loadServices = async () => {
    try {
      const data = await servicesApi.getServices(1, 1000, undefined, true)
      setServices(data.items)
    } catch (error) {
      console.error('Ошибка загрузки услуг:', error)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{promocode ? 'Редактировать промокод' : 'Создать промокод'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Код промокода *</label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              required
              className="form-input"
              disabled={!!promocode}
              placeholder="SUMMER2024"
            />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Тип скидки *</label>
              <select
                value={formData.discount_type}
                onChange={(e) => setFormData({ ...formData, discount_type: e.target.value })}
                required
                className="form-input"
              >
                <option value="percent">Процент (%)</option>
                <option value="fixed">Фиксированная сумма (₽)</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Значение скидки *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.discount_value}
                onChange={(e) => setFormData({ ...formData, discount_value: parseFloat(e.target.value) || 0 })}
                required
                className="form-input"
              />
            </div>
          </div>
          
          <div className="form-group">
            <label>Услуга (оставьте пустым для всех услуг)</label>
            <select
              value={formData.service_id || ''}
              onChange={(e) => setFormData({ ...formData, service_id: e.target.value ? parseInt(e.target.value) : null })}
              className="form-input"
            >
              <option value="">Все услуги</option>
              {services.map(service => (
                <option key={service.id} value={service.id}>{service.name}</option>
              ))}
            </select>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Минимальная сумма (₽)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.min_amount || 0}
                onChange={(e) => setFormData({ ...formData, min_amount: parseFloat(e.target.value) || 0 })}
                className="form-input"
              />
            </div>
            
            <div className="form-group">
              <label>Макс. использований (оставьте пустым для безлимита)</label>
              <input
                type="number"
                min="1"
                value={formData.max_uses || ''}
                onChange={(e) => setFormData({ ...formData, max_uses: e.target.value ? parseInt(e.target.value) : null })}
                className="form-input"
                placeholder="Безлимит"
              />
            </div>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Дата начала</label>
              <input
                type="date"
                value={formData.start_date || ''}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value || null })}
                className="form-input"
              />
            </div>
            
            <div className="form-group">
              <label>Дата окончания</label>
              <input
                type="date"
                value={formData.end_date || ''}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value || null })}
                className="form-input"
              />
            </div>
          </div>
          
          <div className="form-group">
            <label>Описание</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value || null })}
              className="form-input"
              rows={3}
              placeholder="Описание промокода..."
            />
          </div>
          
          {promocode && (
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={promocode.is_active}
                  onChange={(e) => {
                    // Обновляем статус через API
                    promocodesApi.updatePromocode(promocode.id, { is_active: e.target.checked })
                      .then(() => {
                        window.location.reload()
                      })
                      .catch((error) => {
                        console.error('Ошибка обновления статуса:', error)
                        alert('Не удалось обновить статус')
                      })
                  }}
                  className="form-checkbox"
                />
                <span>Активен</span>
              </label>
            </div>
          )}
          
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              {promocode ? 'Сохранить' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Promocodes

