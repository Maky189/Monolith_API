import { Component } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { UsersComponent } from '../users/users.component';
import { GamesComponent } from '../games/games.component';
import { AssignmentsComponent } from '../assignments/assignments.component';
import { BinariesComponent } from '../binaries/binaries.component';

@Component({
  selector: 'app-console',
  standalone: true,
  imports: [UsersComponent, GamesComponent, AssignmentsComponent, BinariesComponent],
  template: `
    <div class="console-shell">
      <aside class="sidebar">
        <h2>Outland Admin</h2>
        <nav>
          <button [class.active]="tab === 'users'" (click)="tab = 'users'">Users</button>
          <button [class.active]="tab === 'games'" (click)="tab = 'games'">Games</button>
          <button [class.active]="tab === 'assignments'" (click)="tab = 'assignments'">Assignments</button>
          <button [class.active]="tab === 'binaries'" (click)="tab = 'binaries'">Binaries</button>
        </nav>
        <div style="margin-top:24px">
          <button class="secondary" (click)="auth.logout()">Sign out</button>
        </div>
      </aside>
      <main class="main">
        @if (tab === 'users')       { <app-users /> }
        @if (tab === 'games')       { <app-games /> }
        @if (tab === 'assignments') { <app-assignments /> }
        @if (tab === 'binaries')    { <app-binaries /> }
      </main>
    </div>
  `
})
export class ConsoleComponent {
  tab = 'users';
  constructor(public auth: AuthService) {}
}
