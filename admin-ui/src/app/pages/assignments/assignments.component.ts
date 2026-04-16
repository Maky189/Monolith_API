import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Assignment, Game, User } from '../../models';

@Component({
  selector: 'app-assignments',
  standalone: true,
  imports: [FormsModule],
  template: `
    <h1>Game Assignments</h1>
    <p class="muted">Only <b>game_dev</b> users can be assigned to games.</p>
    <div class="row">
      <div>
        <label>Game developer</label>
        <select [(ngModel)]="selectedUserId" name="user" (ngModelChange)="onUserChange($event)">
          <option value="">— pick a game_dev —</option>
          @for (u of gameDevs; track u.id) {
            <option [value]="u.id">{{ u.username }}</option>
          }
        </select>
      </div>
      <div>
        <label>Game</label>
        <select [(ngModel)]="selectedGameId" name="game">
          <option value="">— pick a game —</option>
          @for (g of games; track g.id) {
            <option [value]="g.id">{{ g.name }} ({{ g.folder_name }})</option>
          }
        </select>
      </div>
      <div>
        <button (click)="onAssign()" [disabled]="!selectedUserId || !selectedGameId">Assign</button>
      </div>
    </div>
    @if (error) { <div class="error">{{ error }}</div> }
    <table>
      <thead>
        <tr><th>ID</th><th>Game</th><th></th></tr>
      </thead>
      <tbody>
        @for (a of assignments; track a.id) {
          <tr>
            <td>{{ a.id }}</td>
            <td>{{ gameName(a.game_id) }}</td>
            <td><button class="danger" (click)="onRevoke(a)">Revoke</button></td>
          </tr>
        }
      </tbody>
    </table>
  `
})
export class AssignmentsComponent implements OnInit {
  users: User[] = [];
  games: Game[] = [];
  assignments: Assignment[] = [];
  selectedUserId: number | '' = '';
  selectedGameId: number | '' = '';
  error: string | null = null;

  get gameDevs() {
    const result: User[] = [];
    for (const u of this.users) {
      if (u.role === 'game_dev') result.push(u);
    }
    return result;
  }

  constructor(private auth: AuthService, private api: ApiService) {}

  async ngOnInit() {
    try {
      this.users = await this.api.listUsers(this.auth.token()!);
      this.games = await this.api.listGames(this.auth.token()!);
      if (this.gameDevs.length > 0) {
        this.selectedUserId = this.gameDevs[0].id;
        await this.loadAssignments(this.gameDevs[0].id);
      }
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onUserChange(id: number | '') {
    if (id) {
      await this.loadAssignments(Number(id));
    } else {
      this.assignments = [];
    }
  }

  async loadAssignments(uid: number) {
    try {
      this.assignments = await this.api.listAssignments(this.auth.token()!, uid);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onAssign() {
    if (!this.selectedUserId || !this.selectedGameId) return;
    this.error = null;
    try {
      await this.api.createAssignment(this.auth.token()!, Number(this.selectedUserId), Number(this.selectedGameId));
      await this.loadAssignments(Number(this.selectedUserId));
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onRevoke(a: Assignment) {
    try {
      await this.api.deleteAssignment(this.auth.token()!, a.id);
      if (this.selectedUserId) await this.loadAssignments(Number(this.selectedUserId));
    } catch (e: any) {
      this.error = e.message;
    }
  }

  gameName(id: number): string {
    for (const g of this.games) {
      if (g.id === id) return g.name;
    }
    return 'game #' + id;
  }
}
