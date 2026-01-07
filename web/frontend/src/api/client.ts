import axios from 'axios'

// В production используем относительный путь через nginx proxy
// НЕ используем baseURL вообще - axios будет использовать относительные пути
const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor для добавления токена и company_id
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    
    // Извлекаем company_id из JWT токена (если есть)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const company_id = payload.company_id
      if (company_id) {
        // Добавляем company_id в query параметры, если его еще нет
        if (config.params) {
          config.params.company_id = company_id
        } else {
          config.params = { company_id }
        }
      }
    } catch (e) {
      // Игнорируем ошибки парсинга токена
    }
  }
  // Убеждаемся, что используем относительные пути (без baseURL)
  config.baseURL = undefined
  return config
})

// Interceptor для обработки ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      
      // Не перенаправляем, если мы на публичных страницах или страницах супер-админа
      const currentPath = window.location.pathname
      const publicPaths = ['/login', '/register', '/payment/success', '/payment/error', '/super-admin/login']
      
      // Перенаправляем только если мы НЕ на публичных страницах
      if (!publicPaths.includes(currentPath) && !currentPath.startsWith('/super-admin')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

