"""FastAPI приложение"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.api import auth, bookings, users, services, blocks, promocodes, promotions, broadcasts, export, subscription
from app.api import masters_tenant, posts_tenant, clients_tenant, services_tenant
from app.api import settings as settings_api
from app.middleware.tenant import TenantMiddleware

# ✅ Исправлена архитектура моделей - используем полноценные API
from app.api import public, webhooks, super_admin

from app.api import webhooks

app = FastAPI(title="Barber API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для мульти-тенантности
app.add_middleware(TenantMiddleware)

# Регистрация роутеров
app.include_router(auth.router)
app.include_router(subscription.router)
app.include_router(bookings.router)
app.include_router(users.router)
app.include_router(services_tenant.router)
app.include_router(masters_tenant.router)
app.include_router(posts_tenant.router)
app.include_router(clients_tenant.router)
app.include_router(settings_api.router)
app.include_router(blocks.router)
app.include_router(promocodes.router)
app.include_router(promotions.router)
app.include_router(broadcasts.router)
app.include_router(export.router)

# ✅ Используем полноценные API с ORM моделями
app.include_router(public.router)
app.include_router(webhooks.router)
app.include_router(super_admin.router)


@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return JSONResponse({"status": "ok"})


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "Barber API"}
