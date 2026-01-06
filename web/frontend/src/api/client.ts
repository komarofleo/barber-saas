import axios from 'axios'

// В production используем относительный путь через nginx proxy
// НЕ используем baseURL вообще - axios будет использовать относительные пути
const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor для добавления токена
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
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
      const publicPaths = ['/login', '/register', '/payment/success', '/payment/error']
      const superAdminPaths = ['/super-admin/login']
      
      if (!publicPaths.includes(currentPath) && !superAdminPaths.includes(currentPath)) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

