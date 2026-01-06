"""FastAPI приложение"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import auth, bookings, users, services, masters, posts, clients, settings as settings_api, blocks, promocodes, promotions, broadcasts, export
# ⚠️ ВРЕМЕННО: Закомментирован subscription из-за проблем с моделями
# ОБЯЗАТЕЛЬНО НУЖНО ДОДЕЛАТЬ:
# 1. Исправить импорты в subscription.py (использовать SQL вместо ORM)
# 2. Включить обратно subscription.router
# from app.api import subscription

# ✅ Исправлена архитектура моделей - используем полноценные API
from app.api import public
from app.api import super_admin_simple as super_admin  # Временно используем упрощенную версию

from app.api import webhooks

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
# app.include_router(subscription.router)  # Временно закомментирован
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

# ✅ Используем полноценный public API с ORM моделями
app.include_router(public.router)
# ✅ Используем полноценный webhooks API с ORM моделями
app.include_router(webhooks.router)
# ⚠️ ВРЕМЕННО: Используем упрощенный super_admin API
app.include_router(super_admin.router)


@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return JSONResponse({"status": "ok"})


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "AutoService API"}
