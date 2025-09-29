import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthService } from '../services/auth';
import styles from './AuthForm.module.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await AuthService.login({ email, password });
      
      // Сохраняем токен в localStorage
      AuthService.saveToken(response.access_token);
      
      // Перенаправляем на главную страницу
      navigate('/dashboard');
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Не удалось выполнить вход. Попробуйте ещё раз.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Вход в систему</h1>
      <p className={styles.subtitle}>используйте корпоративную почту и пароль</p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.label}>
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

        <label className={styles.label}>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            placeholder="••••••••"
          />
        </label>

        {error && <div className={styles.error}>{error}</div>}

        <button type="submit" className={styles.submit} disabled={loading}>
          {loading ? 'Входим…' : 'Войти'}
        </button>
      </form>

      <div className={styles.footer}>
        <span>Нет аккаунта?</span>
        <Link to="/register">Зарегистрироваться</Link>
      </div>
    </div>
  );
};

export default LoginPage;
