import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { Assignment, Binary, Game, Role, User } from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  private headers(token: string) {
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  login(email: string, password: string) {
    return firstValueFrom(
      this.http.post<{ access_token: string; role: string; user_id: number }>(
        '/api/auth/login', { email, password }
      )
    );
  }

  listUsers(token: string) {
    return firstValueFrom(this.http.get<User[]>('/api/users/', { headers: this.headers(token) }));
  }

  createUser(token: string, data: { username: string; email: string; password: string; role: Role }) {
    return firstValueFrom(this.http.post<User>('/api/users/', data, { headers: this.headers(token) }));
  }

  updateUser(token: string, id: number, data: { is_active?: boolean; role?: string }) {
    return firstValueFrom(this.http.patch<User>(`/api/users/${id}`, data, { headers: this.headers(token) }));
  }

  deleteUser(token: string, id: number) {
    return firstValueFrom(this.http.delete(`/api/users/${id}`, { headers: this.headers(token) }));
  }

  listGames(token: string) {
    return firstValueFrom(this.http.get<Game[]>('/api/games/', { headers: this.headers(token) }));
  }

  createGame(token: string, data: { name: string; folder_name: string; description?: string }) {
    return firstValueFrom(this.http.post<Game>('/api/games/', data, { headers: this.headers(token) }));
  }

  deleteGame(token: string, id: number) {
    return firstValueFrom(this.http.delete(`/api/games/${id}`, { headers: this.headers(token) }));
  }

  listAssignments(token: string, userId: number) {
    return firstValueFrom(this.http.get<Assignment[]>(`/api/assignments/user/${userId}`, { headers: this.headers(token) }));
  }

  createAssignment(token: string, user_id: number, game_id: number) {
    return firstValueFrom(this.http.post<Assignment>('/api/assignments/', { user_id, game_id }, { headers: this.headers(token) }));
  }

  deleteAssignment(token: string, id: number) {
    return firstValueFrom(this.http.delete(`/api/assignments/${id}`, { headers: this.headers(token) }));
  }

  listBinaries(token: string) {
    return firstValueFrom(this.http.get<Binary[]>('/api/binaries/', { headers: this.headers(token) }));
  }

  uploadBinary(token: string, kind: string, platform: string, version: string, file: File) {
    const form = new FormData();
    form.append('kind', kind);
    form.append('platform', platform);
    form.append('version', version);
    form.append('file', file);
    return firstValueFrom(
      this.http.post<Binary>('/api/binaries/', form, { headers: new HttpHeaders({ Authorization: `Bearer ${token}` }) })
    );
  }

  async downloadBinary(token: string, id: number, filename: string) {
    const blob = await firstValueFrom(
      this.http.get(`/api/binaries/${id}/download`, { headers: this.headers(token), responseType: 'blob' })
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  deleteBinary(token: string, id: number) {
    return firstValueFrom(this.http.delete(`/api/binaries/${id}`, { headers: this.headers(token) }));
  }
}
