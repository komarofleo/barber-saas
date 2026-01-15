import { useState, useEffect } from 'react'
import { blocksApi, BlockedSlot, BlockedSlotCreateRequest } from '../api/blocks'
import { mastersApi, Master } from '../api/masters'
import { postsApi, Post } from '../api/posts'
import { servicesApi, Service } from '../api/services'
import './Blocks.css'

function Blocks() {
  const [blocks, setBlocks] = useState<BlockedSlot[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [filterType, setFilterType] = useState<string>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  useEffect(() => {
    loadBlocks()
  }, [filterType, startDate, endDate])

  const loadBlocks = async () => {
    try {
      setLoading(true)
      const data = await blocksApi.getBlocks(
        startDate || undefined,
        endDate || undefined,
        filterType !== 'all' ? filterType : undefined
      )
      setBlocks(data.items)
    } catch (error: any) {
      console.error('Ошибка загрузки блокировок:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (blockId: number) => {
    if (!confirm('Вы уверены, что хотите удалить эту блокировку?')) {
      return
    }
    
    try {
      await blocksApi.deleteBlock(blockId)
      loadBlocks()
    } catch (error: any) {
      console.error('Ошибка удаления блокировки:', error)
      alert('Не удалось удалить блокировку')
    }
  }

  const handleCreate = async (data: BlockedSlotCreateRequest) => {
    try {
      await blocksApi.createBlock(data)
      setShowCreateModal(false)
      loadBlocks()
    } catch (error: any) {
      console.error('Ошибка создания блокировки:', error)
      alert(error.response?.data?.detail || 'Не удалось создать блокировку')
    }
  }

  const getBlockTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'full_service': 'Весь салон красоты',
      'master': 'Мастер',
      'post': 'Рабочее место',
      'service': 'Услуга'
    }
    return labels[type] || type
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  const formatTime = (timeString: string | null) => {
    if (!timeString) return 'Весь день'
    return timeString.substring(0, 5)
  }

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Блокировки</h1>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          + Добавить блокировку
        </button>
      </div>

      <div className="blocks-filters">
        <div className="filter-group">
          <label>Тип блокировки</label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="filter-select"
          >
            <option value="all">Все</option>
            <option value="full_service">Весь салон красоты</option>
            <option value="master">Мастер</option>
            <option value="post">Рабочее место</option>
            <option value="service">Услуга</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Дата от</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="filter-input"
          />
        </div>
        <div className="filter-group">
          <label>Дата до</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="filter-input"
          />
        </div>
        <button className="btn-filter-compact" onClick={loadBlocks}>
          🔄 Обновить
        </button>
      </div>

      {showCreateModal && (
        <CreateBlockModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : blocks.length === 0 ? (
        <div className="empty-state">
          <p>Блокировок не найдено</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Тип</th>
                <th>Объект</th>
                <th>Дата начала</th>
                <th>Дата окончания</th>
                <th>Время</th>
                <th>Причина</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((block) => (
                <tr key={block.id}>
                  <td>{block.id}</td>
                  <td>{getBlockTypeLabel(block.block_type)}</td>
                  <td>
                    {block.master_name && `Мастер: ${block.master_name}`}
                    {block.post_number && `Пост №${block.post_number}`}
                    {block.service_name && `Услуга: ${block.service_name}`}
                    {block.block_type === 'full_service' && 'Весь салон красоты'}
                  </td>
                  <td>{formatDate(block.start_date)}</td>
                  <td>{formatDate(block.end_date)}</td>
                  <td>
                    {block.start_time && block.end_time
                      ? `${formatTime(block.start_time)} - ${formatTime(block.end_time)}`
                      : 'Весь день'}
                  </td>
                  <td>{block.reason || '-'}</td>
                  <td>
                    <button className="btn-sm btn-delete" onClick={() => handleDelete(block.id)}>
                      🗑️ Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

interface CreateBlockModalProps {
  onClose: () => void
  onSave: (data: BlockedSlotCreateRequest) => void
}

function CreateBlockModal({ onClose, onSave }: CreateBlockModalProps) {
  const [blockType, setBlockType] = useState<string>('full_service')
  const [masterId, setMasterId] = useState<number | undefined>(undefined)
  const [postId, setPostId] = useState<number | undefined>(undefined)
  const [serviceId, setServiceId] = useState<number | undefined>(undefined)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [reason, setReason] = useState('')
  
  const [masters, setMasters] = useState<Master[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [services, setServices] = useState<Service[]>([])

  useEffect(() => {
    console.log('CreateBlockModal: blockType изменился на', blockType)
  }, [blockType])

  useEffect(() => {
    loadMasters()
    loadPosts()
    loadServices()
  }, [])

  const loadMasters = async () => {
    try {
      // Загружаем все данные по частям, если их много
      let allMasters: Master[] = []
      let page = 1
      const pageSize = 100
      let hasMore = true
      
      while (hasMore) {
        const data = await mastersApi.getMasters(page, pageSize)
        allMasters = [...allMasters, ...data.items]
        hasMore = data.items.length === pageSize && allMasters.length < data.total
        page++
      }
      
      setMasters(allMasters)
    } catch (error: any) {
      console.error('Ошибка загрузки мастеров:', error)
      if (error.response?.status === 422) {
        // Если 422, пробуем с меньшим размером страницы
        try {
          const data = await mastersApi.getMasters(1, 50)
          setMasters(data.items)
        } catch (e) {
          console.error('Ошибка загрузки мастеров с page_size=50:', e)
        }
      }
    }
  }

  const loadPosts = async () => {
    try {
      // Загружаем все данные по частям, если их много
      let allPosts: Post[] = []
      let page = 1
      const pageSize = 100
      let hasMore = true
      
      while (hasMore) {
        const data = await postsApi.getPosts(page, pageSize)
        allPosts = [...allPosts, ...data.items]
        hasMore = data.items.length === pageSize && allPosts.length < data.total
        page++
      }
      
      setPosts(allPosts)
    } catch (error: any) {
      console.error('Ошибка загрузки постов:', error)
      if (error.response?.status === 422) {
        // Если 422, пробуем с меньшим размером страницы
        try {
          const data = await postsApi.getPosts(1, 50)
          setPosts(data.items)
        } catch (e) {
          console.error('Ошибка загрузки постов с page_size=50:', e)
        }
      }
    }
  }

  const loadServices = async () => {
    try {
      // Загружаем все данные по частям, если их много
      let allServices: Service[] = []
      let page = 1
      const pageSize = 100
      let hasMore = true
      
      while (hasMore) {
        const data = await servicesApi.getServices(page, pageSize)
        allServices = [...allServices, ...data.items]
        hasMore = data.items.length === pageSize && allServices.length < data.total
        page++
      }
      
      setServices(allServices)
    } catch (error: any) {
      console.error('Ошибка загрузки услуг:', error)
      if (error.response?.status === 422) {
        // Если 422, пробуем с меньшим размером страницы
        try {
          const data = await servicesApi.getServices(1, 50)
          setServices(data.items)
        } catch (e) {
          console.error('Ошибка загрузки услуг с page_size=50:', e)
        }
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!startDate || !endDate) {
      alert('Заполните даты начала и окончания')
      return
    }

    const data: BlockedSlotCreateRequest = {
      block_type: blockType,
      start_date: startDate,
      end_date: endDate,
      start_time: startTime || undefined,
      end_time: endTime || undefined,
      reason: reason || undefined,
    }

    if (blockType === 'master') {
      if (!masterId) {
        alert('Выберите мастера')
        return
      }
      data.master_id = masterId
    } else if (blockType === 'post') {
      if (!postId) {
        alert('Выберите пост')
        return
      }
      data.post_id = postId
    } else if (blockType === 'service') {
      if (!serviceId) {
        alert('Выберите услугу')
        return
      }
      data.service_id = serviceId
    }

    onSave(data)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Создать блокировку</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="block-type-select">Тип блокировки *</label>
            <select
              id="block-type-select"
              value={blockType}
              onChange={(e) => {
                e.stopPropagation()
                const newType = e.target.value
                console.log('onChange сработал! Выбран тип блокировки:', newType, 'Текущий blockType:', blockType)
                setBlockType(newType)
                setMasterId(undefined)
                setPostId(undefined)
                setServiceId(undefined)
              }}
              onClick={(e) => {
                e.stopPropagation()
              }}
              className="form-input"
              required
            >
              <option value="full_service">Весь салон красоты</option>
              <option value="master">Мастер</option>
              <option value="post">Рабочее место</option>
              <option value="service">Услуга</option>
            </select>
          </div>

          {blockType === 'master' && (
            <div className="form-group">
              <label htmlFor="master-select">Мастер *</label>
              <select
                id="master-select"
                value={masterId || ''}
                onChange={(e) => {
                  e.stopPropagation()
                  const value = e.target.value
                  console.log('Выбран мастер:', value)
                  setMasterId(value ? parseInt(value) : undefined)
                }}
                onClick={(e) => {
                  e.stopPropagation()
                }}
                className="form-input"
                required
              >
                <option value="">Выберите мастера</option>
                {masters.map((master) => (
                  <option key={master.id} value={master.id}>
                    {master.full_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {blockType === 'post' && (
            <div className="form-group">
              <label htmlFor="post-select">Пост *</label>
              <select
                id="post-select"
                value={postId || ''}
                onChange={(e) => {
                  e.stopPropagation()
                  const value = e.target.value
                  console.log('Выбран пост:', value)
                  setPostId(value ? parseInt(value) : undefined)
                }}
                onClick={(e) => {
                  e.stopPropagation()
                }}
                className="form-input"
                required
              >
                <option value="">Выберите пост</option>
                {posts.map((post) => (
                  <option key={post.id} value={post.id}>
                    Пост №{post.number} {post.name ? `- ${post.name}` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {blockType === 'service' && (
            <div className="form-group">
              <label htmlFor="service-select">Услуга *</label>
              <select
                id="service-select"
                value={serviceId || ''}
                onChange={(e) => {
                  e.stopPropagation()
                  const value = e.target.value
                  console.log('Выбрана услуга:', value)
                  setServiceId(value ? parseInt(value) : undefined)
                }}
                onClick={(e) => {
                  e.stopPropagation()
                }}
                className="form-input"
                required
              >
                <option value="">Выберите услугу</option>
                {services.map((service) => (
                  <option key={service.id} value={service.id}>
                    {service.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="form-row">
            <div className="form-group">
              <label>Дата начала *</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="form-input"
                required
              />
            </div>
            <div className="form-group">
              <label>Дата окончания *</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="form-input"
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Время начала (опционально)</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="form-input"
              />
              <small>Если не указано, блокировка на весь день</small>
            </div>
            <div className="form-group">
              <label>Время окончания (опционально)</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="form-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Причина</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="form-input"
              rows={3}
              placeholder="Причина блокировки (отпуск, ремонт и т.д.)"
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              Создать
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Blocks





