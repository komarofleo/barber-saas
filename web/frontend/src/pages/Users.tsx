import { useState, useEffect } from 'react'
import { usersApi, User, UserCreateRequest } from '../api/users'
import './Users.css'

function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showViewModal, setShowViewModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [viewingUser, setViewingUser] = useState<User | null>(null)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const pageSize = 20

  useEffect(() => {
    loadUsers()
  }, [page])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await usersApi.getUsers(page, pageSize, search || undefined)
      setUsers(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки пользователей:', error)
      if (error.response?.status === 401) {
        window.location.href = '/login'
      }
    } finally {
      setLoading(false)
    }
  }

  const handleToggleAdmin = async (userId: number, currentStatus: boolean) => {
    try {
      await usersApi.toggleAdmin(userId, !currentStatus)
      loadUsers()
    } catch (error: any) {
      console.error('Ошибка изменения статуса админа:', error)
      alert('Не удалось изменить статус администратора')
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadUsers()
  }

  const handleCreate = async (data: UserCreateRequest) => {
    try {
      await usersApi.createUser(data)
      setShowCreateModal(false)
      loadUsers()
    } catch (error: any) {
      console.error('Ошибка создания пользователя:', error)
      alert(error.response?.data?.detail || 'Не удалось создать пользователя')
    }
  }

  const handleView = async (user: User) => {
    try {
      const fullUser = await usersApi.getUser(user.id)
      setViewingUser(fullUser)
      setShowViewModal(true)
    } catch (error: any) {
      console.error('Ошибка загрузки пользователя:', error)
      alert(error.response?.data?.detail || 'Не удалось загрузить данные пользователя')
    }
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    setShowEditModal(true)
  }

  const handleUpdate = async (data: Partial<UserCreateRequest>) => {
    if (!editingUser) return
    
    try {
      await usersApi.updateUser(editingUser.id, data)
      setShowEditModal(false)
      setEditingUser(null)
      loadUsers()
    } catch (error: any) {
      console.error('Ошибка обновления пользователя:', error)
      alert(error.response?.data?.detail || 'Не удалось обновить пользователя')
    }
  }

  const handleDelete = async (user: User) => {
    const confirmed = window.confirm(
      `Удалить пользователя ${user.first_name || user.last_name || `ID ${user.id}`}?\n` +
      'Пользователь будет деактивирован, его данные сохранятся.'
    )
    if (!confirmed) {
      return
    }

    try {
      await usersApi.deleteUser(user.id)
      if (viewingUser?.id === user.id) {
        setShowViewModal(false)
        setViewingUser(null)
      }
      if (editingUser?.id === user.id) {
        setShowEditModal(false)
        setEditingUser(null)
      }
      loadUsers()
    } catch (error: any) {
      console.error('Ошибка удаления пользователя:', error)
      alert(error.response?.data?.detail || 'Не удалось удалить пользователя')
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      <div className="page-header-simple">
        <h1>Пользователи</h1>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          + Добавить пользователя
        </button>
      </div>

      <div className="users-filters">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Поиск по имени или Telegram ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn-search">🔍 Поиск</button>
        </form>
      </div>

      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {showViewModal && viewingUser && (
        <ViewUserModal
          user={viewingUser}
          onClose={() => {
            setShowViewModal(false)
            setViewingUser(null)
          }}
          onEdit={() => {
            setShowViewModal(false)
            handleEdit(viewingUser)
          }}
          onDelete={() => handleDelete(viewingUser)}
        />
      )}

      {showEditModal && editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => {
            setShowEditModal(false)
            setEditingUser(null)
          }}
          onSave={handleUpdate}
        />
      )}

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : users.length === 0 ? (
        <div className="empty-state">
          <p>Пользователи не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Telegram ID</th>
                  <th>Имя</th>
                  <th>Фамилия</th>
                  <th>Username</th>
                  <th>Телефон</th>
                  <th>Админ</th>
                  <th>Мастер</th>
                  <th>Дата регистрации</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.telegram_id}</td>
                    <td>{user.first_name || '-'}</td>
                    <td>{user.last_name || '-'}</td>
                    <td>{user.username || '-'}</td>
                    <td>{user.phone || '-'}</td>
                    <td>
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={user.is_admin}
                          onChange={() => handleToggleAdmin(user.id, user.is_admin)}
                          className="admin-checkbox"
                        />
                        <span className="checkbox-text">{user.is_admin ? 'Да' : 'Нет'}</span>
                      </label>
                    </td>
                    <td>
                      <span className={`badge ${user.is_master ? 'badge-success' : 'badge-default'}`}>
                        {user.is_master ? 'Да' : 'Нет'}
                      </span>
                    </td>
                    <td>{new Date(user.created_at).toLocaleDateString('ru-RU')}</td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-sm btn-view" onClick={() => handleView(user)}>
                          👁️ Просмотр
                        </button>
                        <button className="btn-sm btn-edit" onClick={() => handleEdit(user)}>
                          ✏️ Редактировать
                        </button>
                        <button className="btn-sm btn-delete" onClick={() => handleDelete(user)}>
                          🗑️ Удалить (архив)
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
    </div>
  )
}

interface CreateUserModalProps {
  onClose: () => void
  onSave: (data: UserCreateRequest) => void
}

function CreateUserModal({ onClose, onSave }: CreateUserModalProps) {
  const [formData, setFormData] = useState<UserCreateRequest>({
    telegram_id: 0,
    first_name: '',
    last_name: '',
    username: '',
    phone: '',
    is_admin: false,
    is_master: false,
  })
  
  const [role, setRole] = useState<string>('customer')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.telegram_id) {
      alert('Введите Telegram ID')
      return
    }
    
    // Устанавливаем роли на основе выбранного статуса
    const updatedFormData = {
      ...formData,
      is_admin: role === 'admin',
      is_master: role === 'master',
    }
    
    onSave(updatedFormData)
  }
  
  const handleRoleChange = (newRole: string) => {
    setRole(newRole)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Создать пользователя</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Telegram ID *</label>
            <input
              type="number"
              value={formData.telegram_id || ''}
              onChange={(e) => setFormData({ ...formData, telegram_id: parseInt(e.target.value) || 0 })}
              required
              className="form-input"
              placeholder="123456789"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Имя</label>
              <input
                type="text"
                value={formData.first_name || ''}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value || undefined })}
                className="form-input"
                placeholder="Иван"
              />
            </div>

            <div className="form-group">
              <label>Фамилия</label>
              <input
                type="text"
                value={formData.last_name || ''}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value || undefined })}
                className="form-input"
                placeholder="Иванов"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                value={formData.username || ''}
                onChange={(e) => setFormData({ ...formData, username: e.target.value || undefined })}
                className="form-input"
                placeholder="@username"
              />
            </div>

            <div className="form-group">
              <label>Телефон</label>
              <input
                type="text"
                value={formData.phone || ''}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value || undefined })}
                className="form-input"
                placeholder="+7 (999) 123-45-67"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Статус *</label>
            <select
              value={role}
              onChange={(e) => handleRoleChange(e.target.value)}
              className="form-input"
              required
            >
              <option value="customer">Заказчик</option>
              <option value="admin">Админ</option>
              <option value="master">Мастер</option>
            </select>
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

interface ViewUserModalProps {
  user: User
  onClose: () => void
  onEdit: () => void
  onDelete: () => void
}

function ViewUserModal({ user, onClose, onEdit, onDelete }: ViewUserModalProps) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Пользователь: {user.first_name || user.last_name || `ID ${user.id}`}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="client-details-grid">
            <div className="client-detail-section">
              <h3 className="detail-section-title">👤 Основная информация</h3>
              <div className="detail-item">
                <div className="detail-label">ID:</div>
                <div className="detail-value">{user.id}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Telegram ID:</div>
                <div className="detail-value">{user.telegram_id}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Имя:</div>
                <div className="detail-value">{user.first_name || '-'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Фамилия:</div>
                <div className="detail-value">{user.last_name || '-'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Username:</div>
                <div className="detail-value">{user.username || '-'}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Телефон:</div>
                <div className="detail-value">{user.phone || '-'}</div>
              </div>
            </div>

            <div className="client-detail-section">
              <h3 className="detail-section-title">🔐 Данные для входа</h3>
              <div className="detail-item">
                <div className="detail-label">Логин:</div>
                <div className="detail-value">{user.telegram_id}</div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Пароль:</div>
                <div className="detail-value">{user.telegram_id}</div>
              </div>
              <div className="detail-item" style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '5px' }}>
                <div className="detail-value" style={{ fontSize: '12px', color: '#666' }}>
                  💡 Для входа в админ-панель используйте Telegram ID как логин и пароль
                </div>
              </div>
            </div>

            <div className="client-detail-section">
              <h3 className="detail-section-title">⚙️ Роли и статусы</h3>
              <div className="detail-item">
                <div className="detail-label">Администратор:</div>
                <div className="detail-value">
                  <span className={`badge ${user.is_admin ? 'badge-success' : 'badge-default'}`}>
                    {user.is_admin ? 'Да' : 'Нет'}
                  </span>
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Мастер:</div>
                <div className="detail-value">
                  <span className={`badge ${user.is_master ? 'badge-success' : 'badge-default'}`}>
                    {user.is_master ? 'Да' : 'Нет'}
                  </span>
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Заблокирован:</div>
                <div className="detail-value">
                  <span className={`badge ${user.is_blocked ? 'badge-danger' : 'badge-success'}`}>
                    {user.is_blocked ? 'Да' : 'Нет'}
                  </span>
                </div>
              </div>
              <div className="detail-item">
                <div className="detail-label">Дата регистрации:</div>
                <div className="detail-value">
                  {new Date(user.created_at).toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Закрыть
          </button>
          <button type="button" className="btn-danger" onClick={onDelete}>
            🗑️ Удалить (архив)
          </button>
          <button type="button" className="btn-primary" onClick={onEdit}>
            ✏️ Редактировать
          </button>
        </div>
      </div>
    </div>
  )
}

interface EditUserModalProps {
  user: User
  onClose: () => void
  onSave: (data: Partial<UserCreateRequest>) => void
}

function EditUserModal({ user, onClose, onSave }: EditUserModalProps) {
  const [formData, setFormData] = useState({
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    username: user.username || '',
    phone: user.phone || '',
    is_admin: user.is_admin,
    is_master: user.is_master,
    is_blocked: user.is_blocked || false,
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setLoading(true)
      await onSave({
        first_name: formData.first_name || undefined,
        last_name: formData.last_name || undefined,
        username: formData.username || undefined,
        phone: formData.phone || undefined,
        is_admin: formData.is_admin,
        is_master: formData.is_master,
        is_blocked: formData.is_blocked,
      })
    } catch (error: any) {
      console.error('Ошибка обновления пользователя:', error)
      alert(error.response?.data?.detail || 'Не удалось обновить пользователя')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Редактировать пользователя</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Telegram ID (неизменяемо)</label>
            <input
              type="number"
              value={user.telegram_id}
              disabled
              className="form-input"
              style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
            />
            <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              💡 Telegram ID используется как логин и пароль для входа
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Имя</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="form-input"
                placeholder="Иван"
              />
            </div>

            <div className="form-group">
              <label>Фамилия</label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="form-input"
                placeholder="Иванов"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="form-input"
                placeholder="@username"
              />
            </div>

            <div className="form-group">
              <label>Телефон</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="form-input"
                placeholder="+7 (999) 123-45-67"
              />
            </div>
          </div>

          <div className="form-row form-row-checkboxes">
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_admin}
                  onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                  className="form-checkbox"
                />
                <span>Администратор</span>
              </label>
            </div>

            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_master}
                  onChange={(e) => setFormData({ ...formData, is_master: e.target.checked })}
                  className="form-checkbox"
                />
                <span>Мастер</span>
              </label>
            </div>

            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_blocked}
                  onChange={(e) => setFormData({ ...formData, is_blocked: e.target.checked })}
                  className="form-checkbox"
                />
                <span>Заблокирован</span>
              </label>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Отмена
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Users
