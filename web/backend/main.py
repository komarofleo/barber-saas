"""FastAPI приложение"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import auth, bookings, users, services, masters, posts, clients, settings as settings_api, blocks, promocodes, promotions, broadcasts, export

# ⚠️ ВРЕМЕННО: Используем упрощенный публичный API без ORM моделей
# ОБЯЗАТЕЛЬНО НУЖНО ДОДЕЛАТЬ:
# 1. Исправить архитектуру моделей public_models.py (проблема с __table_args__ и metadata)
# 2. Включить обратно полноценный public.py с ORM моделями
# 3. Протестировать все endpoints
# 4. Удалить public_simple.py после исправления
from app.api import public_simple as public

# ⚠️ ВРЕМЕННО: Закомментирован super_admin из-за проблем с моделями
# ОБЯЗАТЕЛЬНО НУЖНО ДОДЕЛАТЬ:
# 1. Исправить импорты в super_admin.py (использовать SQL вместо ORM)
# 2. Включить обратно super_admin.router
# from app.api import super_admin

# ⚠️ ВРЕМЕННО: Закомментирован webhooks из-за проблем с моделями
# ОБЯЗАТЕЛЬНО НУЖНО ДОДЕЛАТЬ:
# 1. Исправить импорты в webhooks.py (использовать SQL вместо ORM)
# 2. Включить обратно webhooks.router
# from app.api import webhooks

app = FastAPI(title="AutoService API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров
app.include_router(auth.router)
app.include_router(subscription.router)
app.include_router(bookings.router)
app.include_router(users.router)
app.include_router(services.router)
app.include_router(masters.router)
app.include_router(posts.router)
app.include_router(clients.router)
app.include_router(settings_api.router)
app.include_router(blocks.router)
app.include_router(promocodes.router)
app.include_router(promotions.router)
app.include_router(broadcasts.router)
app.include_router(export.router)

# ⚠️ ВРЕМЕННО: Используем упрощенный публичный API
app.include_router(public.router)

# ⚠️ ВРЕМЕННО: Закомментированы проблемные модули
# app.include_router(webhooks.router)
# app.include_router(super_admin.router)


@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return JSONResponse({"status": "ok"})


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "AutoService API"}
