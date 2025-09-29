import { useState, useEffect } from 'react';
import { AuthService } from '../services/auth';
import { AuthenticatedUser } from '../types/user';
import UserManagement from '../components/admin/UserManagement';
import CatalogManagement from '../components/admin/CatalogManagement';
import styles from './AdminPage.module.css';

type AdminTab = 'users' | 'catalogs';

const AdminPage = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const user = await AuthService.getCurrentUser();
        setCurrentUser(user);
      } catch (error) {
        console.error('Failed to load current user:', error);
        // Перенаправляем на страницу входа при ошибке
        AuthService.logout();
        window.location.href = '/login';
      } finally {
        setLoading(false);
      }
    };

    loadCurrentUser();
  }, []);

  const tabs = [
    { id: 'users' as AdminTab, label: 'Пользователи', icon: '👥' },
    { id: 'catalogs' as AdminTab, label: 'Каталоги', icon: '📁' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'users':
        return <UserManagement currentUser={currentUser ?? undefined} />;
      case 'catalogs':
        return <CatalogManagement />;
      default:
        return <UserManagement currentUser={currentUser ?? undefined} />;
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Загрузка...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Администрирование</h1>
        <p className={styles.subtitle}>
          Управление пользователями и каталогами системы
        </p>
      </div>

      <div className={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
          >
            <span className={styles.tabIcon}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {renderContent()}
      </div>
    </div>
  );
};

export default AdminPage;