import { useState, useEffect } from 'react'
import { postsApi, Post, PostCreateRequest } from '../api/posts'
import './Posts.css'

function Posts() {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingPost, setEditingPost] = useState<Post | null>(null)
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)
  
  const pageSize = 20

  useEffect(() => {
    loadPosts()
  }, [page, filterActive])

  const loadPosts = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) return
      
      const data = await postsApi.getPosts(page, pageSize, search || undefined, filterActive)
      setPosts(data.items)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Ошибка загрузки постов:', error)
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
    loadPosts()
  }

  const handleCreate = async (data: PostCreateRequest) => {
    try {
      await postsApi.createPost(data)
      setShowCreateModal(false)
      loadPosts()
    } catch (error: any) {
      console.error('Ошибка создания поста:', error)
      alert(error.response?.data?.detail || 'Не удалось создать пост')
    }
  }

  const handleUpdate = async (postId: number, data: Partial<PostCreateRequest>) => {
    try {
      await postsApi.updatePost(postId, data)
      setShowEditModal(false)
      setEditingPost(null)
      loadPosts()
    } catch (error: any) {
      console.error('Ошибка обновления поста:', error)
      alert(error.response?.data?.detail || 'Не удалось обновить пост')
    }
  }

  const handleDelete = async (postId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот пост?')) {
      return
    }
    
    try {
      await postsApi.deletePost(postId)
      loadPosts()
    } catch (error: any) {
      console.error('Ошибка удаления поста:', error)
      alert('Не удалось удалить пост')
    }
  }

  const handleEdit = (post: Post) => {
    setEditingPost(post)
    setShowEditModal(true)
  }

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      
      let url = '/api/export/posts'
      if (filterActive !== undefined) {
        url += `?is_active=${filterActive}`
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error('Ошибка экспорта')
      }
      
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `posts_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(downloadUrl)
      document.body.removeChild(a)
    } catch (error: any) {
      console.error('Ошибка экспорта:', error)
      alert('Не удалось экспортировать данные')
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Посты</h1>
        </div>
      </div>

      <div className="posts-controls-bar">
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
        <div className="posts-actions">
          <button className="btn-secondary" onClick={handleExport}>
            📥 Экспорт CSV
          </button>
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            + Добавить пост
          </button>
        </div>
      </div>

      <div className="posts-filters">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Поиск по номеру или названию..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="btn-search">🔍 Поиск</button>
        </form>
      </div>

      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <p>Посты не найдены</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Номер</th>
                  <th>Название</th>
                  <th>Описание</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post) => (
                  <tr key={post.id}>
                    <td>{post.id}</td>
                    <td>{post.number}</td>
                    <td>{post.name || '-'}</td>
                    <td>{post.description || '-'}</td>
                    <td>
                      <span className={`badge ${post.is_active ? 'badge-success' : 'badge-default'}`}>
                        {post.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-sm btn-edit" onClick={() => handleEdit(post)}>
                          ✏️ Редактировать
                        </button>
                        <button className="btn-sm btn-delete" onClick={() => handleDelete(post.id)}>
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
        <PostModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {showEditModal && editingPost && (
        <PostModal
          post={editingPost}
          onClose={() => {
            setShowEditModal(false)
            setEditingPost(null)
          }}
          onSave={(data) => handleUpdate(editingPost.id, data)}
        />
      )}
    </div>
  )
}

interface PostModalProps {
  post?: Post
  onClose: () => void
  onSave: (data: PostCreateRequest) => void
}

function PostModal({ post, onClose, onSave }: PostModalProps) {
  const [formData, setFormData] = useState<PostCreateRequest>({
    number: post?.number || 1,
    name: post?.name || '',
    description: post?.description || '',
    is_active: post?.is_active ?? true,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{post ? 'Редактировать пост' : 'Создать пост'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Номер поста *</label>
            <input
              type="number"
              min="1"
              value={formData.number}
              onChange={(e) => setFormData({ ...formData, number: parseInt(e.target.value) || 1 })}
              required
              className="form-input"
            />
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label>Название</label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value || undefined })}
                className="form-input"
                placeholder="Например: Пост №1"
              />
            </div>
            
            <div className="form-group">
              <label className="checkbox-label" style={{ marginTop: '24px' }}>
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="form-checkbox"
                />
                <span>Активен</span>
              </label>
            </div>
          </div>
          
          <div className="form-group">
            <label>Описание</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value || undefined })}
              className="form-input"
              rows={3}
              placeholder="Описание поста..."
            />
          </div>
          
          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              {post ? 'Сохранить' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Posts
