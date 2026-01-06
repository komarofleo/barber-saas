import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface FormData {
    name: string;
    email: string;
    phone: string;
    telegram_bot_token: string;
    admin_telegram_id: string;
    plan_id: string;
}

interface Plan {
    id: number;
    name: string;
    description: string;
    price_monthly: number;
    price_yearly: number;
    max_bookings_per_month: number;
    max_users: number;
    max_masters: number;
}

interface ValidationError {
    field: string;
    message: string;
}

const RegistrationForm: React.FC = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState<FormData>({
        name: '',
        email: '',
        phone: '+7',
        telegram_bot_token: '',
        admin_telegram_id: '',
        plan_id: '3'
    });
    
    const [plans, setPlans] = useState<Plan[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [errors, setErrors] = useState<ValidationError[]>([]);
    const [submitting, setSubmitting] = useState<boolean>(false);

    // Загрузка тарифных планов
    React.useEffect(() => {
        fetchPlans();
    }, []);

    const fetchPlans = async () => {
        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/public/plans`);
            if (!response.ok) {
                throw new Error('Не удалось загрузить тарифные планы');
            }
            const data = await response.json();
            setPlans(data);
        } catch (error) {
            console.error('Ошибка загрузки планов:', error);
            setErrors([{ field: 'plans', message: 'Не удалось загрузить тарифные планы' }]);
        }
    };

    // Валидация формы
    const validateForm = (): ValidationError[] => {
        const newErrors: ValidationError[] = [];
        
        // Валидация названия
        if (!formData.name || formData.name.length < 3) {
            newErrors.push({ field: 'name', message: 'Название автосервиса должно содержать минимум 3 символа' });
        }
        
        // Валидация email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!formData.email || !emailRegex.test(formData.email)) {
            newErrors.push({ field: 'email', message: 'Пожалуйста, введите корректный email' });
        }
        
        // Валидация телефона
        const phoneRegex = /^\+?7\d{10}$/;
        if (!formData.phone || !phoneRegex.test(formData.phone)) {
            newErrors.push({ field: 'phone', message: 'Телефон должен быть в формате +7XXXXXXXXXX' });
        }
        
        // Валидация токена бота
        if (!formData.telegram_bot_token || formData.telegram_bot_token.length < 50) {
            newErrors.push({ field: 'telegram_bot_token', message: 'Токен бота должен содержать минимум 50 символов' });
        }
        
        // Валидация Telegram ID
        if (!formData.admin_telegram_id || formData.admin_telegram_id.length < 1) {
            newErrors.push({ field: 'admin_telegram_id', message: 'Пожалуйста, введите Telegram ID' });
        }
        
        // Валидация выбора тарифа
        if (!formData.plan_id) {
            newErrors.push({ field: 'plan_id', message: 'Пожалуйста, выберите тарифный план' });
        }
        
        setErrors(newErrors);
        return newErrors;
    };

    // Отправка формы регистрации
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        // Валидация формы
        const validationErrors = validateForm();
        if (validationErrors.length > 0) {
            setErrors(validationErrors);
            return;
        }
        
        setSubmitting(true);
        setLoading(true);
        setErrors([]);

        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/public/companies/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось зарегистрировать компанию');
            }

            const data = await response.json();
            
            // Перенаправляем на страницу оплаты или успеха
            if (data.confirmation_url) {
                window.location.href = data.confirmation_url;
            } else {
                setErrors([{ field: 'general', message: data.message || 'Неизвестная ошибка' }]);
            }
        } catch (error) {
            console.error('Ошибка регистрации:', error);
            setErrors([{ field: 'general', message: 'Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.' }]);
        } finally {
            setLoading(false);
            setSubmitting(false);
        }
    };

    return (
        <div className="registration-container">
            <div className="registration-form">
                <h1 className="form-title">Регистрация автосервиса</h1>
                <p className="form-subtitle">Заполните форму для создания вашей учетной записи</p>
                
                {errors.length > 0 && (
                    <div className="error-messages">
                        {errors.map((error, index) => (
                            <div key={index} className="error-message">
                                {error.message}
                            </div>
                        ))}
                    </div>
                )}
                
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="name">Название автосервиса *</label>
                        <input
                            type="text"
                            id="name"
                            name="name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="form-input"
                            placeholder="ООО 'Точка'"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="email">Email *</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            className="form-input"
                            placeholder="admin@avtoservis.ru"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="phone">Телефон</label>
                        <input
                            type="tel"
                            id="phone"
                            name="phone"
                            value={formData.phone}
                            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                            className="form-input"
                            placeholder="+79001234567"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="telegram_bot_token">Токен Telegram бота *</label>
                        <input
                            type="text"
                            id="telegram_bot_token"
                            name="telegram_bot_token"
                            value={formData.telegram_bot_token}
                            onChange={(e) => setFormData({ ...formData, telegram_bot_token: e.target.value })}
                            className="form-input"
                            placeholder="8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4"
                            required
                        />
                        <small className="form-hint">
                            Получите токен через @BotFather в Telegram
                        </small>
                    </div>

                    <div className="form-group">
                        <label htmlFor="admin_telegram_id">Telegram ID владельца *</label>
                        <input
                            type="number"
                            id="admin_telegram_id"
                            name="admin_telegram_id"
                            value={formData.admin_telegram_id}
                            onChange={(e) => setFormData({ ...formData, admin_telegram_id: e.target.value })}
                            className="form-input"
                            placeholder="329621295"
                            required
                        />
                        <small className="form-hint">
                            Ваш Telegram ID для получения уведомлений
                        </small>
                    </div>

                    <div className="form-group">
                        <label htmlFor="plan_id">Тарифный план *</label>
                        {loading && plans.length === 0 ? (
                            <select disabled className="form-input">
                                <option>Загрузка планов...</option>
                            </select>
                        ) : (
                            <select
                                id="plan_id"
                                name="plan_id"
                                value={formData.plan_id}
                                onChange={(e) => setFormData({ ...formData, plan_id: e.target.value })}
                                className="form-input"
                                required
                            >
                                <option value="">Выберите тариф</option>
                                {plans.map((plan) => (
                                    <option key={plan.id} value={plan.id.toString()}>
                                        {plan.name} - {plan.price_monthly.toLocaleString('ru-RU')} ₽/мес
                                    </option>
                                ))}
                            </select>
                        )}
                    </div>

                    {plans.length > 0 && (
                        <div className="plans-info">
                            <h3>Информация о тарифах:</h3>
                            {plans.map((plan) => (
                                <div key={plan.id} className="plan-card">
                                    <div className="plan-name">{plan.name}</div>
                                    <div className="plan-price">
                                        {plan.price_monthly.toLocaleString('ru-RU')} ₽/мес
                                        <span className="plan-yearly">
                                            или {plan.price_yearly.toLocaleString('ru-RU')} ₽/год
                                        </span>
                                    </div>
                                    <div className="plan-description">{plan.description}</div>
                                    <ul className="plan-features">
                                        <li>Максимум {plan.max_bookings_per_month} записей в месяц</li>
                                        <li>Максимум {plan.max_users} пользователей</li>
                                        <li>Максимум {plan.max_masters} мастеров</li>
                                    </ul>
                                </div>
                            ))}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="submit-button"
                        disabled={submitting || loading}
                    >
                        {submitting ? 'Регистрация...' : 'Зарегистрироваться'}
                    </button>

                    <div className="form-footer">
                        <button
                            type="button"
                            className="secondary-button"
                            onClick={() => navigate('/login')}
                        >
                            Уже есть аккаунт? Войти
                        </button>
                    </div>
                </form>
            </div>

            <style>{`
                .registration-container {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                }

                .registration-form {
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 14px 28px rgba(0, 0, 0, 0.1);
                    padding: 40px;
                    width: 100%;
                    max-width: 800px;
                }

                .form-title {
                    font-size: 32px;
                    font-weight: bold;
                    color: #333;
                    text-align: center;
                    margin-bottom: 10px;
                }

                .form-subtitle {
                    font-size: 16px;
                    color: #666;
                    text-align: center;
                    margin-bottom: 30px;
                }

                .error-messages {
                    margin-bottom: 20px;
                }

                .error-message {
                    background: #f8d7da;
                    border-left: 4px solid #f5c6cb;
                    color: #721c24;
                    padding: 12px;
                    margin-bottom: 10px;
                    border-radius: 4px;
                }

                .form-group {
                    margin-bottom: 20px;
                }

                .form-group label {
                    display: block;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 8px;
                }

                .form-input {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 16px;
                    box-sizing: border-box;
                    transition: border-color 0.3s;
                }

                .form-input:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }

                .form-input:disabled {
                    background: #f5f5f5;
                    cursor: not-allowed;
                }

                .form-hint {
                    display: block;
                    font-size: 12px;
                    color: #999;
                    margin-top: 5px;
                }

                .submit-button {
                    width: 100%;
                    padding: 15px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 18px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s;
                }

                .submit-button:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                }

                .submit-button:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }

                .secondary-button {
                    width: 100%;
                    padding: 15px;
                    background: transparent;
                    color: #667eea;
                    border: 2px solid #667eea;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 15px;
                    transition: all 0.3s;
                }

                .secondary-button:hover {
                    background: #667eea;
                    color: white;
                }

                .plans-info {
                    margin-top: 30px;
                    padding-top: 30px;
                    border-top: 1px solid #eee;
                }

                .plans-info h3 {
                    font-size: 20px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 20px;
                }

                .plan-cards {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-top: 15px;
                }

                .plan-card {
                    background: #f8f9fa;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 20px;
                }

                .plan-card:hover {
                    border-color: #667eea;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
                }

                .plan-name {
                    font-size: 20px;
                    font-weight: 700;
                    color: #667eea;
                    margin-bottom: 10px;
                }

                .plan-price {
                    font-size: 24px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 10px;
                }

                .plan-yearly {
                    font-size: 14px;
                    color: #999;
                    font-weight: 400;
                }

                .plan-description {
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 15px;
                }

                .plan-features {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }

                .plan-features li {
                    padding-left: 20px;
                    position: relative;
                    margin-bottom: 8px;
                    color: #555;
                }

                .plan-features li::before {
                    content: '✓';
                    position: absolute;
                    left: 0;
                    color: #28a745;
                    font-weight: bold;
                }

                .form-footer {
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    text-align: center;
                }
            `}</style>
        </div>
    );
};

export default RegistrationForm;

