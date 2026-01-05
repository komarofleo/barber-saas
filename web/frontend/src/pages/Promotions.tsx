import { useState, useEffect } from 'react'
import { promotionsApi, Promotion, PromotionCreateRequest } from '../api/promotions'
import { servicesApi, Service } from '../api/services'
import './Promotions.css'

function Promotions() {
  const [promotions, setPromotions] = useState<Promotion[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingPromotion, setEditingPromotion] = useState<Promotion | null>(null)
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)
  
  const pageSize = 20

  useEffect(() => {
    loadPromotions()
  }, [page, filterActive])

  const loadPromotions = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await promotionsApi.getPromotions(page, pageSize, filterActive)
      setPromotions(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки акций:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (data: PromotionCreateRequest) => {
    try {
      await promotionsApi.createPromotion(data)
      setShowCreateModal(false)
      loadPromotions()
    } catch (error: any) {
      console.error('Ошибка создания акции:', error)
      alert(error.response?.data?.detail || 'Не удалось создать акцию')
    }
  }

  const handleUpdate = async (promotionId: number, data: Partial<PromotionCreateRequest>) => {
    try {
      await promotionsApi.updatePromotion(promotionId, data)
      setShowEditModal(false)
      setEditingPromotion(null)
      loadPromotions()
    } catch (error: any) {
      console.error('Ошибка обновления акции:', error)
      alert(error.response?.data?.detail || 'Не удалось обновить акцию')
    }
  }

  const handleDelete = async (promotionId: number) => {
    if (!confirm('Вы уверены, что хотите удалить эту акцию?')) {
      return
    }
    
    try {
      await promotionsApi.deletePromotion(promotionId)
      loadPromotions()
    } catch (error: any) {
      console.error('Ошибка удаления акции:', error)
      alert('Не удалось удалить акцию')
    }
  }

  const handleEdit = (promotion: Promotion) => {
    setEditingPromotion(promotion)
    setShowEditModal(true)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Акции</h1>
        </div>
      </div>

      <div className="promotions-controls-bar">
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
          + Добавить акцию
        </button>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : promotions.length === 0 ? (
        <div className="empty-state">
          <p>Акции не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Название</th>
                  <th>Описание</th>
                  <th>Тип скидки</th>
                  <th>Значение</th>
                  <th>Услуга</th>
                  <th>Период</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {promotions.map((promotion) => (
                  <tr key={promotion.id}>
                    <td>{promotion.id}</td>
                    <td><strong>{promotion.name}</strong></td>
                    <td>{promotion.description || '-'}</td>
                    <td>{promotion.discount_type === 'percent' ? 'Процент' : 'Фиксированная'}</td>
                    <td>
                      {promotion.discount_type === 'percent' 
                        ? `${promotion.discount_value}%` 
                        : `${promotion.discount_value} ₽`}
                    </td>
                    <td>{promotion.service_name || 'Все услуги'}</td>
                    <td>
                      {promotion.start_date && promotion.end_date
                        ? `${new Date(promotion.start_date).toLocaleDateString('ru-RU')} - ${new Date(promotion.end_date).toLocaleDateString('ru-RU')}`
                        : promotion.start_date
                        ? `с ${new Date(promotion.start_date).toLocaleDateString('ru-RU')}`
                        : promotion.end_date
                        ? `до ${new Date(promotion.end_date).toLocaleDateString('ru-RU')}`
                        : 'Без ограничений'}
                    </td>
                    <td>
                      <span className={`badge ${promotion.is_active ? 'badge-success' : 'badge-default'}`}>
                        {promotion.is_active ? 'Активна' : 'Неактивна'}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-sm btn-edit" onClick={() => handleEdit(promotion)}>
                          ✏️ Редактировать
                        </button>
                        <button className="btn-sm btn-delete" onClick={() => handleDelete(promotion.id)}>
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
        <PromotionModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {showEditModal && editingPromotion && (
        <PromotionModal
          promotion={editingPromotion}
          onClose={() => {
            setShowEditModal(false)
            setEditingPromotion(null)
          }}
          onSave={(data) => handleUpdate(editingPromotion.id, data)}
        />
      )}
    </div>
  )
}

interface PromotionModalProps {
  promotion?: Promotion
  onClose: () => void
  onSave: (data: PromotionCreateRequest) => void
}

function PromotionModal({ promotion, onClose, onSave }: PromotionModalProps) {
  const [services, setServices] = useState<Service[]>([])
  const [formData, setFormData] = useState<PromotionCreateRequest>({
    name: promotion?.name || '',
    description: promotion?.description || null,
    discount_type: promotion?.discount_type || 'percent',
    discount_value: promotion?.discount_value || 0,
    service_id: promotion?.service_id || null,
    start_date: promotion?.start_date || null,
    end_date: promotion?.end_date || null,
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
          <h2>{promotion ? 'Редактировать акцию' : 'Создать акцию'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Название акции *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="form-input"
              placeholder="Например: Летняя скидка"
            />
          </div>
          
          <div className="form-group">
            <label>Описание</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value || null })}
              className="form-input"
              rows={3}
              placeholder="Описание акции..."
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
          
          {promotion && (
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={promotion.is_active}
                  onChange={(e) => {
                    // Обновляем статус через API
                    promotionsApi.updatePromotion(promotion.id, { is_active: e.target.checked })
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
                <span>Активна</span>
              </label>
            </div>
          )}
          
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              {promotion ? 'Сохранить' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Promotions

