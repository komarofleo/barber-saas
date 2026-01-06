import React from 'react';
import RegistrationForm from '../components/RegistrationForm';

const Register: React.FC = () => {
    return (
        <div className="register-page">
            <div className="register-container">
                <div className="register-content">
                    <h1 className="page-title">AutoService SaaS</h1>
                    <p className="page-subtitle">
                        Платформа для управления автосервисами с изоляцией данных
                    </p>
                    
                    <div className="register-form-wrapper">
                        <h2 className="section-title">📋 Регистрация нового автосервиса</h2>
                        <p className="section-description">
                            Заполните форму, чтобы создать свою учетную запись. После успешной регистрации вы получите доступ к админ-панели.
                        </p>
                        
                        <RegistrationForm />
                        
                        <div className="info-cards">
                            <div className="info-card">
                                <h3 className="info-card-title">✅ Быстрый старт</h3>
                                <ul className="info-list">
                                    <li>⚡ Мгновенная регистрация</li>
                                    <li>🚀 Автоматическое создание аккаунта</li>
                                    <li>🔐 Безопасная оплата через Юкассу</li>
                                </ul>
                            </div>
                            
                            <div className="info-card">
                                <h3 className="info-card-title">💰 Гибкие тарифы</h3>
                                <ul className="info-list">
                                    <li>📦 Starter - для небольших автосервисов</li>
                                    <li>🏢 Basic - для среднего бизнеса</li>
                                    <li>🏢 Business - для больших автосервисов</li>
                                </ul>
                            </div>
                            
                            <div className="info-card">
                                <h3 className="info-card-title">🔒 Безопасность</h3>
                                <ul className="info-list">
                                    <li>🛡️ Изоляция данных между клиентами</li>
                                    <li>🔐 Шифрование платежей</li>
                                    <li>✅ Верификация токенов ботов</li>
                                </ul>
                            </div>
                            
                            <div className="info-card">
                                <h3 className="info-card-title">📞 Поддержка</h3>
                                <ul className="info-list">
                                    <li>📧 Техническая поддержка</li>
                                    <li>🤖 Telegram уведомления</li>
                                    <li>📧 Email помощь</li>
                                </ul>
                            </div>
                        </div>
                        
                        <div className="register-footer">
                            <p className="footer-text">
                                Уже есть аккаунт? {' '}
                                <a href="/login" className="footer-link">
                                    Войти
                                </a>
                            </p>
                            <p className="footer-text-small">
                                Нажимая кнопку «Регистрироваться», вы соглашаетесь с{' '}
                                <a href="/terms" className="footer-link">
                                    условиями использования
                                </a>{' '}
                                и{' '}
                                <a href="/privacy" className="footer-link">
                                    политикой конфиденциальности
                                </a>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Register;

