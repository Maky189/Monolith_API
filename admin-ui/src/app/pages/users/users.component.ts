import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Role, User } from '../../models';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [FormsModule],
  template: `
    <h1>Users</h1>
    <form (ngSubmit)="onCreate()" class="row">
      <input placeholder="username" [(ngModel)]="form.username" name="username" required />
      <input type="email" placeholder="email" [(ngModel)]="form.email" name="email" required />
      <input type="password" placeholder="password (min 6)" [(ngModel)]="form.password" name="password" required />
      <select [(ngModel)]="form.role" name="role">
        @for (r of roles; track r) { <option [value]="r">{{ r }}</option> }
      </select>
      <button type="submit">Add User</button>
    </form>
    @if (error) { <div class="error">{{ error }}</div> }
    <table>
      <thead>
        <tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Active</th><th></th></tr>
      </thead>
      <tbody>
        @for (u of users; track u.id) {
          <tr>
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.role }}</td>
            <td>{{ u.is_active ? 'Yes' : 'No' }}</td>
            <td>
              <button class="secondary" (click)="toggleActive(u)">
                {{ u.is_active ? 'Disable' : 'Enable' }}
              </button>
              @if (u.id !== auth.userId()) {
                <button class="danger" (click)="onDelete(u)" style="margin-left:6px">Delete</button>
              }
            </td>
          </tr>
        }
      </tbody>
    </table>
  `
})
export class UsersComponent implements OnInit {
  roles: Role[] = ['admin', 'engine_backend_dev', 'engine_dev', 'game_dev'];
  users: User[] = [];
  error: string | null = null;
  form = { username: '', email: '', password: '', role: 'game_dev' as Role };

  constructor(public auth: AuthService, private api: ApiService) {}

  ngOnInit() { this.refresh(); }

  async refresh() {
    try {
      this.users = await this.api.listUsers(this.auth.token()!);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onCreate() {
    this.error = null;
    try {
      await this.api.createUser(this.auth.token()!, this.form);
      this.form = { username: '', email: '', password: '', role: 'game_dev' };
      this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async toggleActive(u: User) {
    try {
      await this.api.updateUser(this.auth.token()!, u.id, { is_active: !u.is_active });
      this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onDelete(u: User) {
    if (!confirm('Delete user ' + u.username + '?')) return;
    try {
      await this.api.deleteUser(this.auth.token()!, u.id);
      this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
  }
}
