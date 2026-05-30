import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Binary, TreeEntry } from '../../models';

@Component({
  selector: 'app-dev',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="console-shell">
      <aside class="sidebar">
        <h2>Outland Dev</h2>
        <nav>
          <button [class.active]="tab === 'files'" (click)="tab = 'files'">Files</button>
          <button [class.active]="tab === 'downloads'" (click)="tab = 'downloads'">Downloads</button>
        </nav>
        <div style="margin-top:24px">
          <button class="secondary" (click)="auth.logout()">Sign out</button>
        </div>
      </aside>
      <main class="main">
        @if (tab === 'files') {
          <h1>Source Files</h1>
          <p class="muted">Current folder: <code>{{ currentPath || '/' }}</code></p>
          <div class="row" style="margin-bottom:12px">
            <button (click)="goUp()" [disabled]="!currentPath">Up</button>
            <button (click)="refreshTree()">Refresh</button>
          </div>
          @if (error) { <div class="error">{{ error }}</div> }
          <table>
            <thead>
              <tr><th>Name</th><th>Type</th><th>Access</th><th>Size</th><th></th></tr>
            </thead>
            <tbody>
              @for (entry of entries; track entry.path) {
                <tr>
                  <td>
                    @if (entry.is_dir) {
                      <a href="#" (click)="openFolder(entry); $event.preventDefault()">{{ entry.name }}/</a>
                    } @else {
                      <span>{{ entry.name }}</span>
                    }
                  </td>
                  <td>{{ entry.is_dir ? 'folder' : 'file' }}</td>
                  <td>{{ entry.access }}</td>
                  <td>{{ entry.size !== null ? formatSize(entry.size) : '-' }}</td>
                  <td>
                    @if (!entry.is_dir && entry.access !== 'none') {
                      <button (click)="openFile(entry)">Open</button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>

          @if (openedPath) {
            <h2 style="margin-top:24px">{{ openedPath }}</h2>
            <p class="muted">Access: {{ openedAccess }}</p>
            <textarea [(ngModel)]="fileText" rows="16" style="font-family:monospace;width:100%"></textarea>
            <div class="row" style="margin-top:8px">
              @if (openedAccess === 'write') {
                <button (click)="saveFile()" [disabled]="busy">{{ busy ? 'Saving...' : 'Save' }}</button>
              }
              <button class="secondary" (click)="closeFile()">Close</button>
            </div>
          }
        }
        @if (tab === 'downloads') {
          <h1>Available Builds</h1>
          <p class="muted">Download engine builds you are allowed to use.</p>
          @if (error) { <div class="error">{{ error }}</div> }
          <table>
            <thead>
              <tr><th>Kind</th><th>Platform</th><th>Version</th><th>Filename</th><th>Size</th><th></th></tr>
            </thead>
            <tbody>
              @for (b of binaries; track b.id) {
                <tr>
                  <td>{{ b.kind }}</td>
                  <td>{{ b.platform }}</td>
                  <td>{{ b.version }}</td>
                  <td><code>{{ b.filename }}</code></td>
                  <td>{{ formatSize(b.size_bytes) }}</td>
                  <td><button (click)="download(b)">Download</button></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </main>
    </div>
  `
})
export class DevComponent implements OnInit {
  tab = 'files';
  currentPath = '';
  entries: TreeEntry[] = [];
  binaries: Binary[] = [];
  openedPath = '';
  openedAccess = '';
  fileText = '';
  error: string | null = null;
  busy = false;

  constructor(public auth: AuthService, private api: ApiService) {}

  ngOnInit() {
    this.refreshTree();
    this.refreshBinaries();
  }

  async refreshTree() {
    this.error = null;
    try {
      this.entries = await this.api.listTree(this.auth.token()!, this.currentPath);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async refreshBinaries() {
    try {
      this.binaries = await this.api.listBinaries(this.auth.token()!);
    } catch (e: any) {
      this.error = e.message;
    }
  }

  openFolder(entry: TreeEntry) {
    this.currentPath = entry.path;
    this.closeFile();
    this.refreshTree();
  }

  goUp() {
    if (!this.currentPath) return;
    const parts = this.currentPath.split('/');
    parts.pop();
    this.currentPath = parts.join('/');
    this.closeFile();
    this.refreshTree();
  }

  async openFile(entry: TreeEntry) {
    this.error = null;
    try {
      const file = await this.api.readFile(this.auth.token()!, entry.path);
      this.openedPath = file.path;
      this.openedAccess = file.access;
      this.fileText = file.content;
    } catch (e: any) {
      this.error = e.message;
    }
  }

  async saveFile() {
    this.busy = true;
    this.error = null;
    try {
      await this.api.writeFile(this.auth.token()!, this.openedPath, this.fileText);
    } catch (e: any) {
      this.error = e.message;
    }
    this.busy = false;
  }

  closeFile() {
    this.openedPath = '';
    this.openedAccess = '';
    this.fileText = '';
  }

  async download(b: Binary) {
    try {
      await this.api.downloadBinary(this.auth.token()!, b.id, b.filename);
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
