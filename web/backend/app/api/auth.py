"""API для аутентификации"""
from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from dataclasses import dataclass
import bcrypt
import logging

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.config import settings
from shared.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class UserData:
    """Простой объект для хранения данных пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    is_admin: bool
    is_master: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> UserData:
    """Получить текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        company_id: Optional[int] = payload.get("company_id")
        
        if user_id_str is None:
            raise credentials_exception
        user_id: int = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Если это company_admin, ищем компанию, а не пользователя
    if token_type == "company_admin" and company_id:
        logger.info(f"Получение данных компании {company_id} для company_admin")
        result = await db.execute(
            text("""
                SELECT id, admin_telegram_id, name, email, phone,
                       true, false, false, NOW(), NOW()
                FROM public.companies 
                WHERE id = :company_id AND is_active = true
            """),
            {"company_id": company_id}
        )
        row = result.fetchone()
        if row is None:
            logger.warning(f"Компания {company_id} не найдена или неактивна")
            raise credentials_exception
        
        # Создаем UserData из данных компании
        return UserData(
            id=row[0],  # company_id
            telegram_id=row[1] or 0,  # admin_telegram_id
            username=row[2],  # company name
            first_name=row[2],  # company name
            last_name=None,
            phone=row[4],  # company phone
            is_admin=True,  # company admin всегда админ
            is_master=False,
            is_blocked=False,
            created_at=row[8],
            updated_at=row[9],
        )
    
    # Если это tenant_user, ищем в tenant схеме
    if token_type == "tenant_user" and company_id:
        logger.info(f"Получение данных пользователя {user_id} из tenant схемы компании {company_id}")
        from app.services.tenant_service import get_tenant_service
        
        tenant_service = get_tenant_service()
        schema_name = f"tenant_{company_id}"
        
        async for tenant_session in tenant_service.get_tenant_session(company_id):
            result = await tenant_session.execute(
                text(f"""
                    SELECT id, COALESCE(telegram_id, 0) as telegram_id, username, 
                           COALESCE(full_name, '') as first_name, '' as last_name, 
                           COALESCE(phone, '') as phone,
                           CASE WHEN role = 'admin' THEN true ELSE false END as is_admin,
                           CASE WHEN role = 'master' THEN true ELSE false END as is_master,
                           false as is_blocked,
                           created_at, updated_at
                    FROM "{schema_name}".users
                    WHERE id = :user_id
                """),
                {"user_id": user_id}
            )
            row = result.fetchone()
            if row is None:
                logger.warning(f"Пользователь {user_id} не найден в схеме {schema_name}")
                raise credentials_exception
            
            return UserData(
                id=row[0],
                telegram_id=row[1] or 0,
                username=row[2],
                first_name=row[3],
                last_name=row[4],
                phone=row[5],
                is_admin=row[6],
                is_master=row[7],
                is_blocked=row[8],
                created_at=row[9],
                updated_at=row[10],
            )
            break
    
    # Обычный пользователь - ищем в public.users
    result = await db.execute(
        text("""
            SELECT id, telegram_id, username, first_name, last_name, phone, 
                   is_admin, is_master, is_blocked, created_at, updated_at
            FROM public.users 
            WHERE id = :user_id
        """),
        {"user_id": user_id}
    )
    row = result.fetchone()
    if row is None:
        raise credentials_exception
    
    # Создаем простой объект UserData
    return UserData(
        id=row[0],
        telegram_id=row[1],
        username=row[2],
        first_name=row[3],
        last_name=row[4],
        phone=row[5],
        is_admin=row[6],
        is_master=row[7],
        is_blocked=row[8],
        created_at=row[9],
        updated_at=row[10],
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создать JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль с помощью bcrypt.
    
    Args:
        plain_password: Введенный пароль
        hashed_password: Хешированный пароль из БД
        
    Returns:
        True, если пароли совпадают, иначе False
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Ошибка при проверке пароля: {e}")
        return False


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    """
    Универсальный вход в систему.
    
    Поддерживает два способа входа:
    1. По Email и паролю (для владельцев компаний)
    2. По Telegram ID и паролю (для владельцев компаний)
    
    Args:
        form_data: username (Email или Telegram ID) и password
        db: Асинхронная сессия БД
        
    Returns:
        Токен доступа и данные пользователя
    """
    import re
    
    username = form_data.username
    password = form_data.password
    
    logger.info(f"Попытка входа: {username}")
    
    # Определяем, что ввели: Email или Telegram ID
    is_email = re.match(r'^[^@]+@[^@]+\.[^@]+$', username) is not None
    
    if is_email:
        # Пытаемся войти как владелец компании по Email
        logger.info(f"Попытка входа владельца компании по email: {username}")
        
        # Ищем компанию по email в public схеме
        result = await db.execute(
            text("""
                SELECT id, name, email, phone, telegram_bot_token, admin_telegram_id,
                       subscription_status, can_create_bookings, subscription_end_date,
                       password_hash, is_active
                FROM public.companies
                WHERE email = :email
            """),
            {"email": username}
        )
        row = result.fetchone()
        
        if not row:
            logger.warning(f"Компания с email {username} не найдена")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        # Распаковываем данные
        company_id = row[0]
        company_name = row[1]
        company_email = row[2]
        phone = row[3]
        admin_telegram_id = row[5]
        subscription_status = row[6]
        can_create_bookings = row[7]
        subscription_end_date = row[8]
        password_hash = row[9]
        is_active = row[10]
        
        # Проверяем, активна ли компания
        if not is_active:
            logger.warning(f"Компания {company_id} неактивна")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Компания неактивна. Обратитесь в поддержку."
            )
        
        # Проверяем пароль
        if not password_hash:
            logger.warning(f"Пароль не установлен для компании {company_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        # Проверяем пароль через verify_password
        is_password_valid = verify_password(password, password_hash)
        
        if not is_password_valid:
            logger.warning(f"Неверный пароль для email {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        # Проверяем статус подписки
        if subscription_status != "active":
            logger.warning(f"Подписка компании {company_id} неактивна: {subscription_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Подписка неактивна. Статус: {subscription_status}"
            )
        
        # Создаем токен с company_id
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={
                "sub": str(company_id),
                "type": "company_admin",
                "company_id": company_id
            }, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Владелец компании {company_id} ({username}) успешно вошел в систему")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": company_id,
                "company_id": company_id,
                "telegram_id": admin_telegram_id,
                "username": company_name,
                "first_name": company_name,
                "last_name": None,
                "is_admin": True,
                "is_master": False,
                "email": company_email,
                "phone": phone,
                "subscription_status": subscription_status,
                "can_create_bookings": can_create_bookings,
                "subscription_end_date": subscription_end_date.isoformat() if subscription_end_date else None,
            }
        )
    
    else:
        # Пытаемся войти как пользователь из tenant схемы
        # Сначала проверяем, есть ли company_id в query параметрах
        from fastapi import Request
        from app.services.tenant_service import get_tenant_service
        
        # Пытаемся найти пользователя в tenant схемах всех компаний
        logger.info(f"Попытка входа пользователя из tenant схемы: {username}")
        
        # Получаем список всех активных компаний
        companies_result = await db.execute(
            text("SELECT id FROM public.companies WHERE is_active = true")
        )
        companies = companies_result.fetchall()
        
        tenant_service = get_tenant_service()
        user_found = False
        found_company_id = None
        found_user_data = None
        
        # Ищем пользователя во всех tenant схемах
        for company_row in companies:
            company_id = company_row[0]
            schema_name = f"tenant_{company_id}"
            
            try:
                async for tenant_session in tenant_service.get_tenant_session(company_id):
                    # Ищем пользователя по username или email
                    result = await tenant_session.execute(
                        text(f"""
                            SELECT id, username, email, password_hash, role, is_active, 
                                   full_name, phone, created_at, updated_at
                            FROM "{schema_name}".users
                            WHERE (username = :username OR email = :username)
                            AND is_active = true
                        """),
                        {"username": username}
                    )
                    user_row = result.fetchone()
                    
                    if user_row:
                        # Проверяем пароль
                        user_password_hash = user_row[3]
                        if user_password_hash and verify_password(password, user_password_hash):
                            found_company_id = company_id
                            found_user_data = {
                                "id": user_row[0],
                                "username": user_row[1],
                                "email": user_row[2],
                                "role": user_row[4],
                                "full_name": user_row[6],
                                "phone": user_row[7],
                                "company_id": company_id
                            }
                            user_found = True
                            logger.info(f"Пользователь {username} найден в компании {company_id}")
                            break
                    break  # Выходим из цикла tenant_session
                
                if user_found:
                    break
            except Exception as e:
                logger.warning(f"Ошибка при поиске пользователя в схеме {schema_name}: {e}")
                continue
        
        if user_found and found_user_data:
            # Получаем информацию о компании
            company_result = await db.execute(
                text("""
                    SELECT id, name, email, phone, subscription_status, can_create_bookings, 
                           subscription_end_date, is_active
                    FROM public.companies
                    WHERE id = :company_id
                """),
                {"company_id": found_company_id}
            )
            company_row = company_result.fetchone()
            
            if not company_row or not company_row[7]:  # is_active
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Компания неактивна"
                )
            
            subscription_status = company_row[4]
            if subscription_status != "active":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Подписка неактивна. Статус: {subscription_status}"
                )
            
            # Создаем токен
            access_token_expires = timedelta(hours=24)
            access_token = create_access_token(
                data={
                    "sub": str(found_user_data["id"]),
                    "type": "tenant_user",
                    "company_id": found_company_id
                },
                expires_delta=access_token_expires
            )
            
            logger.info(f"Пользователь {username} успешно вошел в систему (компания {found_company_id})")
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user={
                    "id": found_user_data["id"],
                    "company_id": found_company_id,
                    "telegram_id": None,
                    "username": found_user_data["username"],
                    "first_name": found_user_data["full_name"],
                    "last_name": None,
                    "is_admin": found_user_data["role"] == "admin",
                    "is_master": found_user_data["role"] == "master",
                    "email": found_user_data["email"],
                    "phone": found_user_data["phone"],
                    "subscription_status": subscription_status,
                    "can_create_bookings": company_row[5],
                    "subscription_end_date": company_row[6].isoformat() if company_row[6] else None,
                }
            )
        
        # Если не нашли в tenant схемах, пытаемся войти по Telegram ID (владелец компании)
        try:
            telegram_id = int(username)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        logger.info(f"Попытка входа владельца компании по telegram_id: {telegram_id}")
        
        # Ищем компанию по telegram_id в public схеме
        result = await db.execute(
            text("""
                SELECT id, name, email, phone, telegram_bot_token, admin_telegram_id,
                       subscription_status, can_create_bookings, subscription_end_date,
                       password_hash, is_active
                FROM public.companies
                WHERE admin_telegram_id = :telegram_id
            """),
            {"telegram_id": telegram_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        # Распаковываем данные
        company_id = row[0]
        company_name = row[1]
        company_email = row[2]
        phone = row[3]
        admin_telegram_id = row[5]
        subscription_status = row[6]
        can_create_bookings = row[7]
        subscription_end_date = row[8]
        password_hash = row[9]
        is_active = row[10]
        
        # Проверяем, активна ли компания
        if not is_active:
            logger.warning(f"Компания {company_id} неактивна")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Компания неактивна. Обратитесь в поддержку."
            )
        
        # Проверяем пароль через verify_password
        if not password_hash:
            logger.warning(f"Пароль не установлен для компании {company_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        is_password_valid = verify_password(password, password_hash)
        
        if not is_password_valid:
            logger.warning(f"Неверный пароль для telegram_id {telegram_id} (компания {company_id})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        # Проверяем статус подписки
        if subscription_status != "active":
            logger.warning(f"Подписка компании {company_id} неактивна: {subscription_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Подписка неактивна. Статус: {subscription_status}"
            )
        
        # Создаем токен с company_id
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={
                "sub": str(company_id),
                "type": "company_admin",
                "company_id": company_id
            }, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Владелец компании {company_id} ({telegram_id}) успешно вошел в систему по Telegram ID")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": company_id,
                "company_id": company_id,
                "telegram_id": admin_telegram_id,
                "username": company_name,
                "first_name": company_name,
                "last_name": None,
                "is_admin": True,
                "is_master": False,
                "email": company_email,
                "phone": phone,
                "subscription_status": subscription_status,
                "can_create_bookings": can_create_bookings,
                "subscription_end_date": subscription_end_date.isoformat() if subscription_end_date else None,
            }
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserData = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_admin=current_user.is_admin,
        is_master=current_user.is_master or False,
    )


@router.post("/logout")
async def logout():
    """Выход из системы"""
    return {"message": "Successfully logged out"}
