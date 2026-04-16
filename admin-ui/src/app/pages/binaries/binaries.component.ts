import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Binary } from '../../models';

@Component({
  selector: 'app-binaries',
  standalone: true,
  imports: [FormsModule],
  template: `
    <h1>Binaries</h1>
    <p class="muted">Zip your binary folder (executable + all dependencies) and upload the <code>.zip</code> here.</p>
    <form (ngSubmit)="onUpload()" class="row">
      <select [(ngModel)]="kind" name="kind">
        <option value="debug">debug</option>
        <option value="release">release</option>
      </select>
      <select [(ngModel)]="platform" name="platform">
        <option value="linux">linux</option>
        <option value="windows">windows</option>
      </select>
      <input placeholder="version (e.g. 0.1.0)" [(ngModel)]="version" name="version" required />
      <input type="file" accept=".zip" (change)="onFileChange($event)" />
      <button type="submit" [disabled]="busy">{{ busy ? 'Uploading...' : 'Upload .zip' }}</button>
    </form>
    @if (error) { <div class="error">{{ error }}</div> }
    <table>
      <thead>
        <tr><th>ID</th><th>Kind</th><th>Platform</th><th>Version</th><th>Filename</th><th>Size</th><th></th></tr>
      </thead>
      <tbody>
        @for (b of rows; track b.id) {
          <tr>
            <td>{{ b.id }}</td>
            <td>{{ b.kind }}</td>
            <td>{{ b.platform }}</td>
            <td>{{ b.version }}</td>
            <td><code>{{ b.filename }}</code></td>
            <td>{{ formatSize(b.size_bytes) }}</td>
            <td>
              <button (click)="onDownload(b)">Download</button>
              <button class="danger" (click)="onDelete(b)" style="margin-left:6px">Delete</button>
            </td>
          </tr>
        }
      </tbody>
    </table>
  `
})
export class BinariesComponent implements OnInit {
  rows: Binary[] = [];
  kind = 'debug';
  platform = 'linux';
  version = '';
  file: File | null = null;
  busy = false;
  error: string | null = null;

  constructor(private auth: AuthService, private api: ApiService) {}

  ngOnInit() { this.refresh(); }

  async refresh() {
    try {
      this.rows = await this.api.listBinaries(this.auth.token()!);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.file = input.files[0];
    }
  }

  async onUpload() {
    if (!this.file) { this.error = 'Select a .zip file first'; return; }
    this.error = null;
    this.busy = true;
    try {
      await this.api.uploadBinary(this.auth.token()!, this.kind, this.platform, this.version, this.file);
      this.version = '';
      this.file = null;
      await this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
    this.busy = false;
  }

  async onDownload(b: Binary) {
    try {
      await this.api.downloadBinary(this.auth.token()!, b.id, b.filename);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async onDelete(b: Binary) {
    if (!confirm('Delete ' + b.filename + '?')) return;
    try {
      await this.api.deleteBinary(this.auth.token()!, b.id);
      this.refresh();
    } catch (e: any) {
      this.error = e.message;
    }
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
