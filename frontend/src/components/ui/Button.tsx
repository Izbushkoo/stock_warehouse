import React from 'react';
import styles from '../../styles/buttons.module.css';

export type ButtonVariant = 
  | 'primary' 
  | 'success' 
  | 'warning' 
  | 'danger' 
  | 'info' 
  | 'secondary'
  | 'outlinePrimary'
  | 'outlineSuccess'
  | 'outlineDanger';

export type ButtonSize = 'small' | 'medium' | 'large';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  loading?: boolean;
  children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  icon,
  loading = false,
  children,
  className = '',
  disabled,
  ...props
}) => {
  const buttonClasses = [
    styles.button,
    styles[variant],
    size !== 'medium' ? styles[size] : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <button
      className={buttonClasses}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <>
          <div className={styles.spinner} />
          Загрузка...
        </>
      ) : (
        <>
          {icon && <span className={styles.icon}>{icon}</span>}
          {children}
        </>
      )}
    </button>
  );
};

export default Button;