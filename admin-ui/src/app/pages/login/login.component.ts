import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="login-container">
      <h1>Outland Engine</h1>
      <form (ngSubmit)="onSubmit()">
        <label>Email</label>
        <input type="email" [(ngModel)]="email" name="email" required autofocus />
        <label>Password</label>
        <input type="password" [(ngModel)]="password" name="password" required />
        @if (error) { <div class="error">{{ error }}</div> }
        <button type="submit" style="width:100%;margin-top:16px" [disabled]="busy">
          {{ busy ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  `
})
export class LoginComponent {
  email = '';
  password = '';
  error: string | null = null;
  busy = false;

  constructor(private api: ApiService, private auth: AuthService) {}

  async onSubmit() {
    this.error = null;
    this.busy = true;
    try {
      const res = await this.api.login(this.email, this.password);
      this.auth.setAuth(res.access_token, res.role, res.user_id);
    } catch {
      this.error = 'Invalid email or password.';
    } finally {
      this.busy = false;
    }
  }
}
