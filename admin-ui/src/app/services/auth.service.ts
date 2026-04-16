import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly token = signal<string | null>(localStorage.getItem('token'));
  readonly role = signal<string | null>(localStorage.getItem('role'));
  readonly userId = signal<number | null>(
    localStorage.getItem('userId') ? Number(localStorage.getItem('userId')) : null
  );

  setAuth(token: string, role: string, userId: number): void {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    localStorage.setItem('userId', String(userId));
    this.token.set(token);
    this.role.set(role);
    this.userId.set(userId);
  }

  logout(): void {
    localStorage.clear();
    this.token.set(null);
    this.role.set(null);
    this.userId.set(null);
  }
}
