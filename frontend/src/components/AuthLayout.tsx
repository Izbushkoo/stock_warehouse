import { Outlet } from 'react-router-dom';
import Logo from './Logo';
import styles from './AuthLayout.module.css';

const AuthLayout = () => (
  <div className={styles.wrapper}>
    <div className={styles.card}>
      <Logo />
      <Outlet />
    </div>
  </div>
);

export default AuthLayout;
