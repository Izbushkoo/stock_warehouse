import { Navigate, Route, Routes } from 'react-router-dom';
import AuthLayout from './components/AuthLayout';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import AdminPage from './pages/AdminPage';
import AllegroPage from './pages/AllegroPage';
import { AuthService } from './services/auth';

const App = () => {
  const isAuthenticated = AuthService.isAuthenticated();

  return (
    <Routes>
      {/* Публичные роуты (аутентификация) */}
      <Route element={<AuthLayout />}>
        <Route 
          path="/login" 
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} 
        />
        <Route 
          path="/register" 
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />} 
        />
      </Route>

      {/* Защищенные роуты */}
      <Route 
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/allegro" element={<AllegroPage />} />
        <Route path="/catalog" element={<div>Каталог (в разработке)</div>} />
        <Route path="/warehouses" element={<div>Склады (в разработке)</div>} />
      </Route>

      {/* Перенаправления */}
      <Route 
        path="/" 
        element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} 
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default App;
