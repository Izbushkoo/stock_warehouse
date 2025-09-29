import React, { useState } from 'react';
import { User } from '../../types/user';
import { updateUser } from '../../api/auth';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import styles from './EditUserModal.module.css';

interface EditUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  onUserUpdated: (updatedUser: User) => void;
}

const EditUserModal: React.FC<EditUserModalProps> = ({
  isOpen,
  onClose,
  user,
  onUserUpdated
}) => {
  const [formData, setFormData] = useState({
    display_name: user.display_name,
    email: user.email
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const updatedUser = await updateUser(user.user_id, formData);
      onUserUpdated(updatedUser);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Редактировать пользователя">
      <form onSubmit={handleSubmit} className={styles.form}>
        {error && (
          <div className={styles.error}>
            {error}
          </div>
        )}

        <div className={styles.field}>
          <label htmlFor="display_name" className={styles.label}>
            Отображаемое имя
          </label>
          <input
            type="text"
            id="display_name"
            name="display_name"
            value={formData.display_name}
            onChange={handleChange}
            className={styles.input}
            required
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="email" className={styles.label}>
            Email
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className={styles.input}
            required
          />
        </div>

        <div className={styles.actions}>
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            Отмена
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={loading}
          >
            Сохранить
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default EditUserModal;