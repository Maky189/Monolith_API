import { Component } from '@angular/core';
import { AuthService } from './services/auth.service';
import { LoginComponent } from './pages/login/login.component';
import { ConsoleComponent } from './pages/console/console.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LoginComponent, ConsoleComponent],
  template: `
    @if (!auth.token()) {
      <app-login />
    } @else if (auth.role() !== 'admin') {
      <div class="login-container">
        <h1>Access denied</h1>
        <p class="muted">Admin console requires an admin account. You are signed in as <b>{{ auth.role() }}</b>.</p>
        <button (click)="auth.logout()">Sign out</button>
      </div>
    } @else {
      <app-console />
    }
  `
})
export class AppComponent {
  constructor(public auth: AuthService) {}
}
