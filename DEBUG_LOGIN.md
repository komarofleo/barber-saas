# 🐛 Отладка проблемы с входом

## Проблема: "request failed" при входе

### Шаг 1: Создать/проверить администратора

**Вариант 1: Через Docker (рекомендуется)**
```bash
./create_admin_docker.sh
```

**Вариант 2: Через Python скрипт**
```bash
python fix_admin.py
```

**Вариант 3: Вручную через SQL**
```bash
docker-compose exec postgres psql -U autoservice_user -d autoservice_db << EOF
-- Создать или обновить администратора
INSERT INTO users (telegram_id, is_admin, is_master, is_blocked, first_name, created_at, updated_at)
VALUES (329621295, true, false, false, 'Admin', NOW(), NOW())
ON CONFLICT (telegram_id) DO UPDATE SET is_admin = true;

-- Проверить результат
SELECT id, telegram_id, first_name, is_admin FROM users WHERE telegram_id = 329621295;
EOF
```

### Шаг 2: Проверить данные для входа

**Формат входа:**
- **Логин:** `329621295` (число, ваш telegram_id)
- **Пароль:** `329621295` (строка, тот же telegram_id)

⚠️ **Важно:** 
- Логин и пароль должны быть одинаковыми (оба = telegram_id)
- Логин - это число
- Пароль - это строка (но содержит то же число)

### Шаг 3: Проверить формат запроса

Endpoint `/api/auth/login` использует `OAuth2PasswordRequestForm`, который требует:
- **Content-Type:** `application/x-www-form-urlencoded`
- **Формат:** `username=329621295&password=329621295`

**Правильный запрос через curl:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=329621295&password=329621295"
```

**Неправильный запрос (JSON не работает!):**
```bash
# ❌ НЕ РАБОТАЕТ
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "329621295", "password": "329621295"}'
```

### Шаг 4: Проверить логи backend

```bash
# Смотреть логи в реальном времени
docker-compose logs -f web

# Или последние 50 строк
docker-compose logs --tail=50 web
```

### Шаг 5: Проверить через браузер

1. Откройте DevTools (F12)
2. Перейдите на вкладку **Network**
3. Попробуйте войти
4. Найдите запрос к `/api/auth/login`
5. Проверьте:
   - **Request Headers:** `Content-Type: application/x-www-form-urlencoded`
   - **Request Payload:** `username=329621295&password=329621295`
   - **Response:** Что возвращает сервер?

### Шаг 6: Типичные ошибки

**Ошибка 1: "Incorrect username or password"**
```
Причина: Пользователь не найден или пароль неверный
Решение: 
1. Проверить, что пользователь существует в БД
2. Проверить, что telegram_id правильный
3. Убедиться, что пароль = telegram_id (строка)
```

**Ошибка 2: "Could not validate credentials"**
```
Причина: Проблема с JWT токеном
Решение: Проверить SECRET_KEY в .env
```

**Ошибка 3: "422 Unprocessable Entity"**
```
Причина: Неправильный формат запроса
Решение: Убедиться, что используется form-data, а не JSON
```

**Ошибка 4: "500 Internal Server Error"**
```
Причина: Ошибка на сервере
Решение: Проверить логи backend
```

### Шаг 7: Проверить базу данных

```bash
# Подключиться к БД
docker-compose exec postgres psql -U autoservice_user -d autoservice_db

# Проверить пользователя
SELECT id, telegram_id, first_name, is_admin, is_master, is_blocked 
FROM users 
WHERE telegram_id = 329621295;

# Если пользователя нет, создать:
INSERT INTO users (telegram_id, is_admin, is_master, is_blocked, first_name, created_at, updated_at)
VALUES (329621295, true, false, false, 'Admin', NOW(), NOW());
```

### Шаг 8: Проверить frontend код

Убедитесь, что frontend отправляет правильный формат:

```typescript
// Правильно (в auth.ts)
const params = new URLSearchParams()
params.append('username', data.username)
params.append('password', data.password)

const response = await axios.post('/api/auth/login', params.toString(), {
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
})
```

## Быстрая проверка

1. ✅ Пользователь существует в БД?
2. ✅ `is_admin = true`?
3. ✅ `telegram_id = 329621295`?
4. ✅ Backend запущен и отвечает?
5. ✅ Формат запроса правильный (form-data)?

## Если ничего не помогает

1. Проверьте логи: `docker-compose logs -f web`
2. Проверьте консоль браузера (F12)
3. Проверьте Network tab в DevTools
4. Попробуйте войти через curl (см. выше)

---

**Дата создания:** 06.01.2026

