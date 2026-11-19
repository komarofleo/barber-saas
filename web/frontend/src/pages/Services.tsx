import { useState, useEffect } from 'react'
import { servicesApi, Service, ServiceCreateRequest } from '../api/services'
import { formatMoney } from '../utils/money'
import './Services.css'

function Services() {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingService, setEditingService] = useState<Service | null>(null)
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)
  
  const pageSize = 20

  useEffect(() => {
    loadServices()
  }, [page, filterActive])

  const loadServices = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await servicesApi.getServices(page, pageSize, search || undefined, filterActive)
      setServices(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки услуг:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadServices()
  }

  const handleCreate = async (data: ServiceCreateRequest) => {
    try {
      await servicesApi.createService(data)
      setShowCreateModal(false)
      loadServices()
    } catch (error: any) {
      console.error('Ошибка создания услуги:', error)
      alert('Не удалось создать услугу')
    }
  }

  const handleUpdate = async (serviceId: number, data: Partial<ServiceCreateRequest>) => {
    try {
      await servicesApi.updateService(serviceId, data)
      setShowEditModal(false)
      setEditingService(null)
      loadServices()
    } catch (error: any) {
      console.error('Ошибка обновления услуги:', error)
      alert('Не удалось обновить услугу')
    }
  }

  const handleDelete = async (serviceId: number) => {
    if (!confirm('Вы уверены, что хотите удалить эту услугу?')) {
      return
    }
    
    try {
      await servicesApi.deleteService(serviceId)
      loadServices()
    } catch (error: any) {
      console.error('Ошибка удаления услуги:', error)
      alert('Не удалось удалить услугу')
    }
  }

  const handleEdit = (service: Service) => {
    setEditingService(service)
    setShowEditModal(true)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Услуги</h1>
      </div>

      <div className="services-controls-bar">
        <div className="view-mode-buttons">
          <button
            className={`view-btn ${filterActive === undefined ? 'active' : ''}`}
            onClick={() => setFilterActive(undefined)}
          >
            Все
          </button>
          <button
            className={`view-btn ${filterActive === true ? 'active' : ''}`}
            onClick={() => setFilterActive(true)}
          >
            Активные
          </button>
          <button
            className={`view-btn ${filterActive === false ? 'active' : ''}`}
            onClick={() => setFilterActive(false)}
          >
            Неактивные
          </button>
        </div>
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Поиск по названию..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn-search">🔍 Поиск</button>
        </form>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          + Добавить услугу
        </button>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : services.length === 0 ? (
        <div className="empty-state">
          <p>Услуги не найдены</p>
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
                  <th>Цена</th>
                  <th>Длительность (мин)</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service) => (
                  <tr key={service.id}>
                    <td>{service.id}</td>
                    <td>{service.name}</td>
                    <td>{service.description || '-'}</td>
                    <td>{formatMoney(service.price)}</td>
                    <td>{service.duration}</td>
                    <td>
                      <span className={`badge ${service.is_active ? 'badge-success' : 'badge-default'}`}>
                        {service.is_active ? 'Активна' : 'Неактивна'}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-sm btn-edit" onClick={() => handleEdit(service)}>
                          ✏️ Редактировать
                        </button>
                        <button className="btn-sm btn-delete" onClick={() => handleDelete(service.id)}>
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
        <ServiceModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {showEditModal && editingService && (
        <ServiceModal
          service={editingService}
          onClose={() => {
            setShowEditModal(false)
            setEditingService(null)
          }}
          onSave={(data) => handleUpdate(editingService.id, data)}
        />
      )}
    </div>
  )
}

interface ServiceModalProps {
  service?: Service
  onClose: () => void
  onSave: (data: ServiceCreateRequest) => void
}

function ServiceModal({ service, onClose, onSave }: ServiceModalProps) {
  const [formData, setFormData] = useState<ServiceCreateRequest>({
    name: service?.name || '',
    description: service?.description || '',
    price: service?.price || 0,
    duration: service?.duration || 30,
    is_active: service?.is_active ?? true,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{service ? 'Редактировать услугу' : 'Создать услугу'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Название *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <label>Описание</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="form-input"
              rows={3}
            />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Цена (₽) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
                required
                className="form-input"
              />
            </div>
            
            <div className="form-group">
              <label>Длительность (мин) *</label>
              <input
                type="number"
                min="1"
                value={formData.duration}
                onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) || 30 })}
                required
                className="form-input"
              />
            </div>
          </div>
          
          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="form-checkbox"
              />
              <span>Активна</span>
            </label>
          </div>
          
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              {service ? 'Сохранить' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Services
