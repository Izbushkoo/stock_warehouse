import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../api/auth';
import { AuthService } from '../services/auth';
import formStyles from './AuthForm.module.css';

const RegisterPage = () => {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Пароли не совпадают.');
      return;
    }

    setLoading(true);
    try {
      // Регистрируем пользователя
      await register({ email, password, display_name: fullName });

      // Автоматически выполняем вход
      const loginResponse = await AuthService.login({ email, password });

      // Сохраняем токен
      AuthService.saveToken(loginResponse.access_token);

      // Перенаправляем на дашборд
      navigate('/dashboard');
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Не удалось создать пользователя. Попробуйте ещё раз.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={formStyles.container}>
      <h1 className={formStyles.title}>Регистрация</h1>
      <p className={formStyles.subtitle}>создайте учётную запись для работы со складом</p>

      <form className={formStyles.form} onSubmit={handleSubmit}>
        <label className={formStyles.label}>
          Полное имя
          <input
            type="text"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
            placeholder="Иван Иванов"
          />
        </label>

        <label className={formStyles.label}>
          Электронная почта
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            placeholder="name@example.com"
          />
        </label>

        <label className={formStyles.label}>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="new-password"
            placeholder="минимум 8 символов"
          />
        </label>

        <label className={formStyles.label}>
          Повторите пароль
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            autoComplete="new-password"
            placeholder="повторите пароль"
          />
        </label>

        {error && <div className={formStyles.error}>{error}</div>}

        <button type="submit" className={formStyles.submit} disabled={loading}>
          {loading ? 'Создаём аккаунт и входим…' : 'Создать аккаунт'}
        </button>
      </form>

      <div className={formStyles.footer}>
        <span>Уже есть аккаунт?</span>
        <Link to="/login">Войти</Link>
      </div>
    </div>
  );
};

export default RegisterPage;
