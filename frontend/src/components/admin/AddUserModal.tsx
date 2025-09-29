import React, { useState } from 'react';
import { User } from '../../types/user';
import { register } from '../../api/auth';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import styles from './AddUserModal.module.css';

interface AddUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUserAdded: (newUser: User) => void;
}

const AddUserModal: React.FC<AddUserModalProps> = ({
  isOpen,
  onClose,
  onUserAdded
}) => {
  const [formData, setFormData] = useState({
    display_name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (formData.password !== formData.confirmPassword) {
      setError('Пароли не совпадают');
      setLoading(false);
      return;
    }

    if (formData.password.length < 6) {
      setError('Пароль должен содержать минимум 6 символов');
      setLoading(false);
      return;
    }

    try {
      const newUser = await register({
        display_name: formData.display_name,
        email: formData.email,
        password: formData.password
      });
      onUserAdded(newUser);
      setFormData({
        display_name: '',
        email: '',
        password: '',
        confirmPassword: ''
      });
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

  const handleClose = () => {
    setFormData({
      display_name: '',
      email: '',
      password: '',
      confirmPassword: ''
    });
    setError(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Добавить пользователя">
      <form onSubmit={handleSubmit} className={styles.form}>
        {error && (
          <div className={styles.error}>
            {error}
          </div>
        )}

        <div className={styles.field}>
          <label htmlFor="display_name" className={styles.label}>
            Отображаемое имя *
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
            Email *
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

        <div className={styles.field}>
          <label htmlFor="password" className={styles.label}>
            Пароль *
          </label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className={styles.input}
            minLength={6}
            required
          />
          <small className={styles.hint}>Минимум 6 символов</small>
        </div>

        <div className={styles.field}>
          <label htmlFor="confirmPassword" className={styles.label}>
            Подтвердите пароль *
          </label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            className={styles.input}
            required
          />
        </div>

        <div className={styles.actions}>
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={loading}
          >
            Отмена
          </Button>
          <Button
            type="submit"
            variant="success"
            loading={loading}
          >
            Добавить пользователя
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default AddUserModal;