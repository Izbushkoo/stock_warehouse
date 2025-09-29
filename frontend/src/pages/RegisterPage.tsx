import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { register } from '../api/auth';
import formStyles from './AuthForm.module.css';
import styles from './RegisterPage.module.css';

const RegisterPage = () => {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (password !== confirmPassword) {
      setError('Пароли не совпадают.');
      return;
    }

    setLoading(true);
    try {
      await register({ email, password, full_name: fullName });
      setSuccessMessage('Пользователь создан. Теперь вы можете войти.');
      setEmail('');
      setFullName('');
      setPassword('');
      setConfirmPassword('');
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
        {successMessage && <div className={styles.success}>{successMessage}</div>}

        <button type="submit" className={formStyles.submit} disabled={loading}>
          {loading ? 'Создаём…' : 'Создать аккаунт'}
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
