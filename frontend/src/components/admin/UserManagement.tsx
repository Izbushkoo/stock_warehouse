import { useState, useEffect } from 'react';
import { AuthenticatedUser, User } from '../../types/user';
import { getUsers, updateUserStatus, deleteUser } from '../../api/auth';
import Button from '../ui/Button';
import AddUserModal from './AddUserModal';
import EditUserModal from './EditUserModal';
import PermissionsModal from './PermissionsModal';
import styles from './UserManagement.module.css';

interface UserManagementProps {
  currentUser?: AuthenticatedUser;
}

const UserManagement = ({ currentUser }: UserManagementProps) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [permissionsUser, setPermissionsUser] = useState<User | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

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

  const handleUserAdded = (newUser: User) => {
    setUsers(prev => [...prev, newUser]);
  };

  const handleUserUpdated = (updatedUser: User) => {
    setUsers(prev => prev.map(user => 
      user.user_id === updatedUser.user_id ? updatedUser : user
    ));
  };

  const handleStatusToggle = async (user: User) => {
    const actionKey = `status-${user.user_id}`;
    setActionLoading(actionKey);
    
    try {
      const updatedUser = await updateUserStatus(user.user_id, !user.is_active);
      handleUserUpdated(updatedUser);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка изменения статуса');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!confirm(`Вы уверены, что хотите удалить пользователя "${user.display_name}"?`)) {
      return;
    }

    const actionKey = `delete-${user.user_id}`;
    setActionLoading(actionKey);
    
    try {
      await deleteUser(user.user_id);
      setUsers(prev => prev.filter(u => u.user_id !== user.user_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка удаления пользователя');
    } finally {
      setActionLoading(null);
    }
  };

  // Проверяем, является ли текущий пользователь системным администратором
  const isSystemAdmin = currentUser?.permissions.is_admin || false;
  const canManageUsers = currentUser?.permissions.can_manage_users || false;

  if (!isSystemAdmin && !canManageUsers) {
    return (
      <div className={styles.noAccess}>
        <h3>Доступ запрещен</h3>
        <p>У вас нет прав для управления пользователями</p>
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
          <Button
            variant="success"
            onClick={() => setShowAddModal(true)}
          >
            Добавить пользователя
          </Button>
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
                  <Button
                    variant="info"
                    size="small"
                    onClick={() => setEditingUser(user)}
                  >
                    Редактировать
                  </Button>
                  <Button
                    variant="warning"
                    size="small"
                    onClick={() => setPermissionsUser(user)}
                  >
                    Разрешения
                  </Button>
                  <Button
                    variant={user.is_active ? "danger" : "success"}
                    size="small"
                    loading={actionLoading === `status-${user.user_id}`}
                    onClick={() => handleStatusToggle(user)}
                  >
                    {user.is_active ? 'Деактивировать' : 'Активировать'}
                  </Button>
                  <Button
                    variant="outlineDanger"
                    size="small"
                    loading={actionLoading === `delete-${user.user_id}`}
                    onClick={() => handleDeleteUser(user)}
                  >
                    Удалить
                  </Button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Модальные окна */}
      <AddUserModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onUserAdded={handleUserAdded}
      />

      {editingUser && (
        <EditUserModal
          isOpen={!!editingUser}
          onClose={() => setEditingUser(null)}
          user={editingUser}
          onUserUpdated={handleUserUpdated}
        />
      )}

      {permissionsUser && (
        <PermissionsModal
          isOpen={!!permissionsUser}
          onClose={() => setPermissionsUser(null)}
          user={permissionsUser}
          onUserUpdated={handleUserUpdated}
        />
      )}
    </div>
  );
};

export default UserManagement;