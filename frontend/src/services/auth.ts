import { LoginRequest, TokenResponse, AuthenticatedUser } from '../types/user';
import { login as apiLogin, getCurrentUser as apiGetCurrentUser, logout as apiLogout } from '../api/auth';

export class AuthService {
  static async login(credentials: LoginRequest): Promise<TokenResponse> {
    return await apiLogin(credentials);
  }

  static async getCurrentUser(): Promise<AuthenticatedUser> {
    return await apiGetCurrentUser();
  }

  static async logout(): Promise<void> {
    await apiLogout();
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  static saveToken(token: string): void {
    localStorage.setItem('access_token', token);
  }

  static getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  static isAuthenticated(): boolean {
    return !!this.getToken();
  }
}