import { useState, useEffect } from 'react';
import { AuthService } from '../services/auth';
import { AuthenticatedUser } from '../types/user';
import UserManagement from '../components/admin/UserManagement';
import CatalogManagement from '../components/admin/CatalogManagement';
import PermissionsManagement from '../components/admin/PermissionsManagement';
import styles from './AdminPage.module.css';

type AdminTab = 'users' | 'catalogs' | 'permissions';

const AdminPage = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        console.log('Loading current user...');
        const user = await AuthService.getCurrentUser();
        console.log('Current user loaded:', user);
        setCurrentUser(user);
      } catch (error) {
        console.error('Failed to load current user:', error);
        if (error instanceof Error) {
          console.error('Error message:', error.message);
        }
      } finally {
        setLoading(false);
      }
    };

    loadCurrentUser();
  }, []);

  const tabs = [
    { id: 'users' as AdminTab, label: 'Пользователи', icon: '👥' },
    { id: 'catalogs' as AdminTab, label: 'Каталоги', icon: '📁' },
    { id: 'permissions' as AdminTab, label: 'Разрешения', icon: '🔐' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'users':
        return <UserManagement currentUser={currentUser} />;
      case 'catalogs':
        return <CatalogManagement />;
      case 'permissions':
        return <PermissionsManagement />;
      default:
        return <UserManagement currentUser={currentUser} />;
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
          Управление пользователями, каталогами и разрешениями системы
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