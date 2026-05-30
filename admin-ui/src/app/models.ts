export type Role = 'admin' | 'engine_backend_dev' | 'engine_dev' | 'game_dev';

export interface User {
  id: number;
  username: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Game {
  id: number;
  name: string;
  folder_name: string;
  description: string | null;
  created_at: string;
}

export interface Assignment {
  id: number;
  user_id: number;
  game_id: number;
  created_at: string;
}

export interface Binary {
  id: number;
  kind: string;
  platform: string;
  version: string;
  filename: string;
  size_bytes: number;
  uploaded_by: number | null;
  created_at: string;
}

export interface TreeEntry {
  name: string;
  path: string;
  is_dir: boolean;
  access: 'none' | 'read' | 'write';
  size: number | null;
}

export interface FileContent {
  path: string;
  content: string;
  size: number;
  mtime: number;
  access: 'none' | 'read' | 'write';
}
