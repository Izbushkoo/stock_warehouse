import { useEffect, useState } from 'react';
import { AuthService } from '../services/auth';
import { AuthenticatedUser } from '../types/user';
import styles from './DashboardPage.module.css';

const DashboardPage = () => {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await AuthService.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('Ошибка загрузки пользователя:', error);
        // Если не удалось загрузить пользователя, выходим
        AuthService.logout();
        window.location.href = '/login';
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner}></div>
        <p>Загрузка...</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className={styles.container}>
      <div className={styles.welcome}>
        <h1>Добро пожаловать, {user.display_name}!</h1>
        <p>Система управления складом Stock Warehouse</p>
      </div>

      <div className={styles.stats}>
        <div className={styles.statCard}>
          <h3>Товары</h3>
          <div className={styles.statNumber}>0</div>
          <p>Всего товаров в системе</p>
        </div>
        
        <div className={styles.statCard}>
          <h3>Склады</h3>
          <div className={styles.statNumber}>0</div>
          <p>Активных складов</p>
        </div>
        
        <div className={styles.statCard}>
          <h3>Заказы</h3>
          <div className={styles.statNumber}>0</div>
          <p>Заказов за сегодня</p>
        </div>
      </div>

      {user.permissions.is_admin && (
        <div className={styles.adminSection}>
          <h2>Администрирование</h2>
          <p>У вас есть права системного администратора</p>
          <div className={styles.adminActions}>
            <a href="/admin" className={styles.adminButton}>
              Панель администратора
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;