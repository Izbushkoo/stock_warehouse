import { useState, useEffect } from 'react';
import { AuthenticatedUser, User } from '../../types/user';
import { getUsers } from '../../api/auth';
import styles from './UserManagement.module.css';

interface UserManagementProps {
  currentUser?: AuthenticatedUser;
}

const UserManagement = ({ currentUser }: UserManagementProps) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadUsers = async () => {
      try {
        setLoading(true);
        setError(null);
        const usersList = await getUsers();
        setUsers(usersList);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Не удалось загрузить список пользователей');
        }
      } finally {
        setLoading(false);
      }
    };

    loadUsers();
  }, []);

  // Проверяем, является ли текущий пользователь системным администратором
  const isSystemAdmin = currentUser?.permissions.is_admin || false;
  const canManageUsers = currentUser?.permissions.can_manage_users || false;

  // Отладочная информация
  console.log('UserManagement Debug:', {
    currentUser,
    isSystemAdmin,
    canManageUsers,
    permissions: currentUser?.permissions
  });

  if (!isSystemAdmin && !canManageUsers) {
    return (
      <div className={styles.noAccess}>
        <h3>Доступ запрещен</h3>
        <p>У вас нет прав для управления пользователями</p>
        <details style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
          <summary>Отладочная информация</summary>
          <pre>{JSON.stringify({ isSystemAdmin, canManageUsers, permissions: currentUser?.permissions }, null, 2)}</pre>
        </details>
      </div>
    );
  }

  if (loading) {
    return <div className={styles.loading}>Загрузка...</div>;
  }

  if (error) {
    return (
      <div className={styles.error}>
        <h3>Ошибка загрузки</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Попробовать снова</button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Управление пользователями</h2>
        {isSystemAdmin && (
          <button className={styles.addButton}>
            Добавить пользователя
          </button>
        )}
      </div>

      <div className={styles.usersList}>
        {users.length === 0 ? (
          <p>Пользователи не найдены</p>
        ) : (
          users.map((user) => (
            <div key={user.user_id} className={styles.userCard}>
              <div className={styles.userInfo}>
                <h4>{user.display_name}</h4>
                <p>{user.email}</p>
                <span className={`${styles.status} ${user.is_active ? styles.active : styles.inactive}`}>
                  {user.is_active ? 'Активен' : 'Неактивен'}
                </span>
              </div>
              
              {isSystemAdmin && (
                <div className={styles.userActions}>
                  <button className={styles.editButton}>Редактировать</button>
                  <button className={styles.permissionsButton}>Разрешения</button>
                  {user.is_active ? (
                    <button className={styles.deactivateButton}>Деактивировать</button>
                  ) : (
                    <button className={styles.activateButton}>Активировать</button>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default UserManagement;