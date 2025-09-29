import { Link, useNavigate } from 'react-router-dom';
import Logo from './Logo';
import styles from './Header.module.css';
import { AuthenticatedUser } from '../types/user';

interface HeaderProps {
  user?: AuthenticatedUser;
  onLogout?: () => void;
}

const Header = ({ user, onLogout }: HeaderProps) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    }
    navigate('/login');
  };

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link to="/dashboard" className={styles.logoLink}>
          <Logo />
        </Link>
        
        <nav className={styles.nav}>
          <Link to="/dashboard" className={styles.navLink}>
            Главная
          </Link>
          <Link to="/catalog" className={styles.navLink}>
            Каталог
          </Link>
          <Link to="/warehouses" className={styles.navLink}>
            Склады
          </Link>
          {user?.permissions.is_admin && (
            <Link to="/admin" className={styles.navLink}>
              Администрирование
            </Link>
          )}
        </nav>

        {user && (
          <div className={styles.userSection}>
            <span className={styles.userName}>{user.display_name}</span>
            <button onClick={handleLogout} className={styles.logoutBtn}>
              Выйти
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;