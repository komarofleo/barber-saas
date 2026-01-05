# 🔄 Инструкция по откату изменений календаря

**Дата создания:** 29 декабря 2025, 05:12  
**Версия:** Calendar Drag-and-Drop Fix

## 📦 Backup файлы

### Локальный backup:
- **Путь:** `/tmp/avtoservis_backup_20251229_051215.tar.gz`
- **Размер:** 18K
- **Содержимое:**
  - `web/backend/app/api/bookings.py`
  - `web/backend/app/schemas/booking.py`
  - `web/frontend/src/pages/Calendar.tsx`
  - `web/frontend/src/pages/Calendar.css`

### Backup на сервере:
- **Путь:** `/tmp/server_backup_calendar_20251229_051241.tar.gz`
- **Размер:** 15K
- **Содержимое:** Те же файлы

## 🔙 Откат на сервере

### Вариант 1: Быстрый откат (если backup на сервере)

```bash
# 1. Восстановить файлы из backup
ssh root@103.71.21.7
cd /opt/avtoservis
tar -xzf /tmp/server_backup_calendar_20251229_051241.tar.gz

# 2. Пересобрать frontend
cd web/frontend
npm run build

# 3. Перезапустить backend
cd /opt/avtoservis
docker compose restart web
```

### Вариант 2: Откат с локального backup

```bash
# 1. Распаковать локальный backup
cd /tmp
tar -xzf avtoservis_backup_20251229_051215.tar.gz

# 2. Скопировать файлы на сервер
sshpass -p '24n7O5x9pNV2' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  web/backend/app/api/bookings.py \
  root@103.71.21.7:/opt/avtoservis/web/backend/app/api/bookings.py

sshpass -p '24n7O5x9pNV2' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  web/backend/app/schemas/booking.py \
  root@103.71.21.7:/opt/avtoservis/web/backend/app/schemas/booking.py

sshpass -p '24n7O5x9pNV2' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  web/frontend/src/pages/Calendar.tsx \
  root@103.71.21.7:/opt/avtoservis/web/frontend/src/pages/Calendar.tsx

sshpass -p '24n7O5x9pNV2' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  web/frontend/src/pages/Calendar.css \
  root@103.71.21.7:/opt/avtoservis/web/frontend/src/pages/Calendar.css

# 3. Пересобрать frontend и перезапустить backend
sshpass -p '24n7O5x9pNV2' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@103.71.21.7 \
  "cd /opt/avtoservis/web/frontend && npm run build && cd /opt/avtoservis && docker compose restart web"
```

## 📝 Что было изменено

### Backend:
1. **`web/backend/app/api/bookings.py`**:
   - Изменен endpoint `update_booking` для обработки данных на уровне FastAPI
   - Строки `date` и `time` преобразуются в объекты до валидации Pydantic
   - Используется `model_construct` для обхода валидации

2. **`web/backend/app/schemas/booking.py`**:
   - Удален `model_validator` из `BookingUpdateRequest`
   - Упрощена схема валидации

### Frontend:
3. **`web/frontend/src/pages/Calendar.tsx`**:
   - Добавлена функциональность drag-and-drop для записей
   - Реализована обработка перемещения в режимах "Неделя" и "День"

4. **`web/frontend/src/pages/Calendar.css`**:
   - Добавлены стили для drag-and-drop
   - Добавлена легенда для статусов записей

## ⚠️ Если что-то пошло не так

1. Проверьте логи backend:
   ```bash
   ssh root@103.71.21.7
   cd /opt/avtoservis
   docker compose logs web | tail -50
   ```

2. Проверьте логи frontend:
   ```bash
   ssh root@103.71.21.7
   cd /opt/avtoservis/web/frontend
   npm run build 2>&1 | tail -20
   ```

3. Проверьте статус контейнеров:
   ```bash
   ssh root@103.71.21.7
   cd /opt/avtoservis
   docker compose ps
   ```

4. Если проблемы критичны - выполните откат по инструкции выше.

## ✅ Проверка работоспособности

После применения изменений проверьте:
- [ ] Календарь загружается без ошибок
- [ ] Можно перемещать записи в режиме "Неделя"
- [ ] Можно перемещать записи в режиме "День"
- [ ] Записи корректно обновляются на сервере после перемещения
- [ ] Нет ошибок в консоли браузера
- [ ] Нет ошибок в логах backend


