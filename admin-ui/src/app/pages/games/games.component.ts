import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Game } from '../../models';

@Component({
  selector: 'app-games',
  standalone: true,
  imports: [FormsModule],
  template: `
    <h1>Games</h1>
    <p class="muted">folder_name must match a folder inside <code>Outland/games/</code>. Only letters, numbers, _ and - allowed.</p>
    <form (ngSubmit)="onCreate()" class="row">
      <input placeholder="display name" [(ngModel)]="form.name" name="name" required />
      <input placeholder="folder name (e.g. adventure)" [(ngModel)]="form.folder_name" name="folder_name" required />
      <input placeholder="description (optional)" [(ngModel)]="form.description" name="description" />
      <button type="submit">Add Game</button>
    </form>
    @if (error) { <div class="error">{{ error }}</div> }
    <table>
      <thead>
        <tr><th>ID</th><th>Name</th><th>Folder</th><th>Description</th><th></th></tr>
      </thead>
      <tbody>
        @for (g of games; track g.id) {
          <tr>
            <td>{{ g.id }}</td>
            <td>{{ g.name }}</td>
            <td><code>{{ g.folder_name }}</code></td>
            <td>{{ g.description || '—' }}</td>
            <td><button class="danger" (click)="onDelete(g)">Delete</button></td>
          </tr>
        }
      </tbody>
    </table>
  `
})
export class GamesComponent implements OnInit {
  games: Game[] = [];
  form = { name: '', folder_name: '', description: '' };
  error: string | null = null;

  constructor(private auth: AuthService, private api: ApiService) {}

  ngOnInit() { this.refresh(); }

  async refresh() {
    try {
      this.games = await this.api.listGames(this.auth.token()!);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onCreate() {
    this.error = null;
    try {
      await this.api.createGame(this.auth.token()!, {
        name: this.form.name,
        folder_name: this.form.folder_name,
        description: this.form.description || undefined,
      });
      this.form = { name: '', folder_name: '', description: '' };
      this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onDelete(g: Game) {
    if (!confirm('Delete game ' + g.name + '?')) return;
    try {
      await this.api.deleteGame(this.auth.token()!, g.id);
      this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
  }
}
