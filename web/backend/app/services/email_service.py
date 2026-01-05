"""
Сервис для отправки email уведомлений.

Этот модуль предоставляет методы для:
- Отправки приветственных писем с данными для входа
- Отправки других уведомлений пользователям
"""

import logging
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os

logger = logging.getLogger(__name__)


class EmailService:
    """
    Сервис для отправки email уведомлений.
    
    Использует SMTP для отправки писем.
    """
    
    def __init__(self):
        """Инициализация сервиса с конфигурацией SMTP."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "noreply@autoservice-saas.com")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        logger.info(f"EmailService инициализирован: {self.smtp_host}")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Отправить email.
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            html_content: HTML содержание письма
            text_content: Текстовое содержание (опционально)
        
        Returns:
            True если email отправлен успешно, False в противном случае
        
        Example:
            >>> await email_service.send_email(
            ...     to_email="user@example.com",
            ...     subject="Добро пожаловать!",
            ...     html_content="<h1>Привет!</h1>"
            ... )
        """
        logger.info(f"Отправка email на {to_email}: {subject}")
        
        # Создаем сообщение
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = formataddr(("AutoService SaaS", self.smtp_from))
        message["To"] = to_email
        
        # Добавляем текстовую часть
        if text_content:
            part_text = MIMEText(text_content, "plain", "utf-8")
            message.attach(part_text)
        
        # Добавляем HTML часть
        part_html = MIMEText(html_content, "html", "utf-8")
        message.attach(part_html)
        
        try:
            # Отправляем через SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
                server.quit()
            
            logger.info(f"Email успешно отправлен на {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error(f"Ошибка аутентификации SMTP: {self.smtp_user}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False
    
    async def send_welcome_email(
        self,
        company_name: str,
        email: str,
        password: str,
        dashboard_url: str,
        plan_name: str,
        subscription_end_date
    ) -> bool:
        """
        Отправить приветственное письмо с данными для входа.
        
        Args:
            company_name: Название автосервиса
            email: Email владельца
            password: Пароль (в открытом виде)
            dashboard_url: Ссылка на админ-панель
            plan_name: Название тарифного плана
            subscription_end_date: Дата окончания подписки
        
        Returns:
            True если письмо отправлено, False в противном случае
        
        Example:
            >>> await email_service.send_welcome_email(
            ...     company_name="ООО 'Точка'",
            ...     email="admin@avtoservis.ru",
            ...     password="AbCd1234XyZ",
            ...     dashboard_url="https://autoservice-saas.com/company/001/dashboard",
            ...     plan_name="Business",
            ...     subscription_end_date=date(2024, 2, 5)
            ... )
        """
        logger.info(f"Отправка приветственного письма на {email}")
        
        subject = "Добро пожаловать в AutoService SaaS!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Добро пожаловать в AutoService SaaS!</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; border-radius: 5px; padding: 30px; text-align: center;">
                    <h1 style="color: #28a745; margin-bottom: 20px;">Добро пожаловать!</h1>
                    <p style="font-size: 16px; margin-bottom: 20px;">
                        Ваш автосервис <strong>{company_name}</strong> успешно зарегистрирован в системе AutoService SaaS.
                    </p>
                    
                    <div style="background-color: #e9ecef; border-radius: 5px; padding: 20px; margin-bottom: 20px; text-align: left;">
                        <h2 style="color: #28a745; margin-top: 0;">Данные для входа</h2>
                        
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Пароль:</strong> <code style="background-color: #fff; padding: 5px 10px; border-radius: 3px; border: 1px solid #ddd;">{password}</code></p>
                        
                        <p style="margin-top: 20px; font-size: 14px;">
                            <span style="color: #dc3545;">⚠️</span> 
                            Пожалуйста, сохраните пароль в безопасном месте.
                            Рекомендуем сменить пароль после первого входа.
                        </p>
                    </div>
                    
                    <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 20px; margin-bottom: 20px;">
                        <h3 style="color: #28a745; margin-top: 0;">Ваша подписка</h3>
                        <p><strong>Тарифный план:</strong> {plan_name}</p>
                        <p><strong>Дата окончания:</strong> {subscription_end_date.strftime('%d.%m.%Y')}</p>
                    </div>
                    
                    <div style="margin: 30px 0;">
                        <a href="{dashboard_url}" 
                           style="display: inline-block; background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                            Перейти в админ-панель
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #666; margin-top: 30px;">
                        Если у вас возникли вопросы, пожалуйста, свяжитесь с нашей поддержкой.
                    </p>
                    
                    <p style="font-size: 14px; color: #666;">
                        С уважением,<br>
                        Команда AutoService SaaS
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )
    
    async def send_payment_success_email(
        self,
        company_name: str,
        email: str,
        amount: float,
        dashboard_url: str
    ) -> bool:
        """
        Отправить письмо об успешной оплате.
        
        Args:
            company_name: Название автосервиса
            email: Email владельца
            amount: Сумма платежа
            dashboard_url: Ссылка на админ-панель
        
        Returns:
            True если письмо отправлено, False в противном случае
        """
        subject = f"Оплата принята: {company_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Оплата принята</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 20px; margin-bottom: 20px;">
                    <h2 style="color: #28a745; margin-top: 0;">Оплата принята!</h2>
                    <p>Ваш платеж на сумму <strong>{amount:.2f} RUB</strong> успешно обработан.</p>
                </div>
                
                <div style="margin: 30px 0;">
                    <a href="{dashboard_url}" 
                       style="display: inline-block; background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                        Перейти в админ-панель
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content
        )


# Создание экземпляра сервиса (singleton)
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """
    Получить или создать экземпляр EmailService.
    
    Returns:
        Экземпляр EmailService
    """
    global _email_service
    
    if _email_service is None:
        _email_service = EmailService()
    
    return _email_service


async def send_welcome_email(
    company_name: str,
    email: str,
    password: str,
    dashboard_url: str,
    plan_name: str,
    subscription_end_date
) -> bool:
    """
    Удобная функция для отправки приветственного письма.
    
    Args:
        company_name: Название автосервиса
        email: Email владельца
        password: Пароль (в открытом виде)
        dashboard_url: Ссылка на админ-панель
        plan_name: Название тарифного плана
        subscription_end_date: Дата окончания подписки
    
    Returns:
        True если письмо отправлено, False в противном случае
    """
    service = get_email_service()
    return await service.send_welcome_email(
        company_name, email, password, dashboard_url, plan_name, subscription_end_date
    )

