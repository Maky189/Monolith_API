# Outland Engine Dev Platform

A web-based management platform for the **Outland** game engine team. It lets an administrator control who has access to which source files, manage game projects, distribute engine binaries, and see live file edits sync between developers in real time.

---

## What This System Does

The engine team works on a shared C++ source tree (the Outland engine). Different developers have different roles — some work on the core engine, some on the graphics backend (RHI), some on individual games. This platform enforces those boundaries:

- **Admin** creates users and assigns them a role
- **Backend logs in** to the admin web console and manages everything from a browser
- **Developers** use the platform to browse and edit source files they are allowed to touch
- When one developer saves a file, everyone else connected via WebSocket receives a live notification
- The admin can upload engine binaries (`.zip` packages) for distribution

Everything runs on **one machine** (the admin's PC) and is accessible to other developers on the same local network.

---

## Project Structure

```
Monolitic_API/
│
├── docker-compose.yml       # Starts both the backend and the web UI together
├── .env                     # Your local secrets (never committed to git)
├── .env.example             # Template showing what variables are needed
├── users.example.txt        # Template for tracking developer credentials
├── users.txt                # Your personal credential list (never committed)
│
├── monolith/                # The backend server (Python / FastAPI)
│   ├── main.py              # All API routes: auth, users, games, assignments
│   ├── database.py          # Database models (User, Game, Assignment, Binary)
│   ├── acl.py               # Access control rules + WebSocket hub
│   ├── fs.py                # Filesystem routes (browse, read, write files)
│   ├── binaries.py          # Binary upload and download routes
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # How to build the backend container
│   └── tests/               # Automated tests
│
└── admin-ui/                # The web admin console (Angular)
    ├── src/app/             # All Angular components and services
    ├── package.json         # JavaScript dependencies
    ├── angular.json         # Angular build configuration
    ├── Dockerfile           # How to build the web UI container
    └── nginx.conf           # Web server config (serves UI + proxies API calls)
```

---

## Roles and Permissions

Every user has exactly one role. The role determines which source files they can read or write.

| Role | What they can do |
|---|---|
| `admin` | Full access to everything. Manages users, games, assignments, and binaries. |
| `engine_dev` | Read/write `src/` and `shaders/`. Cannot touch `src/RHI/` (only the README there). Cannot touch games. |
| `engine_backend_dev` | Read/write `src/RHI/` and build files (`Makefile`, etc.). Cannot touch anything else. |
| `game_dev` | Read/write `assets/`, `maps/`, and only the specific game folders they are assigned to. |

> `src/RHI/` is the graphics/hardware backend — only `engine_backend_dev` can edit those files. The `engine_dev` can see the `README.md` inside it, but cannot open any source files.

---

## Database Models

The system uses a SQLite database with four tables.

### User
Stores everyone who can log in.

| Field | Type | Description |
|---|---|---|
| `id` | Integer | Unique ID |
| `username` | Text | Display name, must be unique |
| `email` | Text | Used to log in, must be unique |
| `password_hash` | Text | Password stored securely (bcrypt) |
| `role` | Text | One of the four roles above |
| `is_active` | Boolean | Disabled users cannot log in |
| `created_at` | Datetime | When the account was created |

### Game
Represents a game project inside the `games/` folder of the source tree.

| Field | Type | Description |
|---|---|---|
| `id` | Integer | Unique ID |
| `name` | Text | Display name (e.g. "Default Game") |
| `folder_name` | Text | Folder inside `games/` (e.g. `default`) — only letters, numbers, `-`, `_` |
| `description` | Text | Optional description |
| `created_at` | Datetime | When it was created |

### GameAssignment
Links a `game_dev` user to a specific game, granting them write access to that game's folder.

| Field | Type | Description |
|---|---|---|
| `id` | Integer | Unique ID |
| `user_id` | Integer | The user being assigned |
| `game_id` | Integer | The game they are assigned to |
| `created_at` | Datetime | When the assignment was made |

Only users with the `game_dev` role can be assigned to games.

### Binary
Tracks uploaded engine build packages.

| Field | Type | Description |
|---|---|---|
| `id` | Integer | Unique ID |
| `kind` | Text | `debug` or `release` |
| `platform` | Text | e.g. `linux`, `windows` |
| `version` | Text | Version string, e.g. `0.1.0` |
| `filename` | Text | Name of the stored `.zip` file |
| `size_bytes` | Integer | File size |
| `uploaded_by` | Integer | ID of the admin who uploaded it |
| `created_at` | Datetime | When it was uploaded |

---

## API Endpoints

All endpoints except `/health` and `/auth/login` require a JWT token in the request header:
```
Authorization: Bearer <your_token>
```

You get the token by logging in. The token contains your user ID, role, and assigned game IDs.

### Health
| Method | URL | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` — used to check the server is running |

### Authentication
| Method | URL | Who | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Anyone | Log in with email + password, receive a JWT token |

### Users (admin only)
| Method | URL | Description |
|---|---|---|
| `GET` | `/users/` | List all users |
| `GET` | `/users/me` | Get your own profile |
| `POST` | `/users/` | Create a new user |
| `PATCH` | `/users/{id}` | Update a user (role, password, active status) |
| `DELETE` | `/users/{id}` | Delete a user (cannot delete yourself) |

### Games (admin only to create/delete)
| Method | URL | Who | Description |
|---|---|---|---|
| `GET` | `/games/` | All logged-in users | List all games |
| `POST` | `/games/` | Admin | Create a game |
| `DELETE` | `/games/{id}` | Admin | Delete a game |

### Assignments (admin only)
| Method | URL | Description |
|---|---|---|
| `GET` | `/assignments/user/{user_id}` | List games assigned to a user |
| `POST` | `/assignments/` | Assign a game_dev to a game |
| `DELETE` | `/assignments/{id}` | Remove an assignment |

### Filesystem
| Method | URL | Description |
|---|---|---|
| `GET` | `/fs/tree?path=src/Core` | List files and folders at a path (filtered by your role) |
| `GET` | `/fs/file?path=src/Core/Engine.cpp` | Read a text file |
| `GET` | `/fs/raw?path=assets/logo.png` | Download any file as-is |
| `PUT` | `/fs/file` | Write/create a text file |
| `WS` | `/fs/ws?token=<jwt>` | WebSocket — receive live notifications when files change |

The tree listing only shows files you are allowed to see. You cannot access files outside your permissions — the server returns 403.

### Binaries
| Method | URL | Who | Description |
|---|---|---|---|
| `GET` | `/binaries/` | All logged-in users | List available builds. `engine_dev` only sees `debug` builds. |
| `POST` | `/binaries/` | Admin | Upload a `.zip` build package |
| `GET` | `/binaries/{id}/download` | All logged-in users | Download a build |
| `DELETE` | `/binaries/{id}` | Admin | Delete a build |

---

## How to Run

There are two ways: **with Docker** (recommended, everything starts automatically) or **without Docker** (for development).

---

### Option 1 — With Docker (recommended)

Docker starts both the backend and the web UI with a single command. You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.

#### Step 1 — Create your `.env` file

Copy the example and fill it in:

```bash
cp .env.example .env
```

Open `.env` and set these values:

```
OUTLAND_ROOT_HOST=/absolute/path/to/your/Outland
```
This is the folder on your PC that contains the engine source tree. Use the full path, not a relative one. On Windows use forward slashes: `C:/Users/you/Outland`.

```
JWT_SECRET=any-long-random-string-here
```
This is used to sign login tokens. Change it to anything — just make it long.

```
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=adminpass
```
These are the credentials for the first admin account. The account is created automatically when the server starts for the first time. Change these to whatever you want.

```
BACKEND_PORT=5000
ADMIN_UI_PORT=8080
```
The ports the services will listen on. Leave them as-is unless something else is already using those ports.

#### Step 2 — Start everything

```bash
docker compose up -d --build
```

- `-d` means "run in the background"
- `--build` rebuilds the containers (needed the first time, and after any code changes)

Wait about 30 seconds for everything to start. You can watch the logs with:

```bash
docker compose logs -f
```

Press `Ctrl+C` to stop watching logs (the server keeps running).

#### Step 3 — Open the admin console

Go to `http://localhost:8080` in your browser and log in with the admin credentials you set in `.env`.

#### Step 4 — Create users and games

1. Go to the **Users** tab → click **Add User** → fill in the form → select a role → Save
2. Go to the **Games** tab → click **Add Game** → set the folder name to match a folder inside `games/` in your source tree
3. Go to the **Assignments** tab → link a `game_dev` user to a game

#### How to access from another PC on your network

Docker already listens on all network interfaces, so your teammates can access the platform over WiFi or LAN. They need your IP address:

- On **Linux/Mac**: run `ip addr` or `ifconfig` and look for your local IP (e.g. `192.168.1.10`)
- On **Windows**: run `ipconfig` and look for IPv4 Address

Then they open `http://192.168.1.10:8080` in their browser (replace with your actual IP).

> Make sure your firewall allows connections on ports 5000 and 8080. On Windows, you may get a prompt asking to allow Docker through the firewall — click Allow.

#### Stop the server

```bash
docker compose down
```

This stops the containers but keeps the database and uploaded binaries. To also delete all stored data:

```bash
docker compose down -v
```

---

### Option 2 — Without Docker (development mode)

This runs the backend and frontend separately, directly on your machine. Good for making changes and testing quickly.

#### Backend

You need Python 3.11 or newer.

```bash
cd monolith

# Create a virtual environment (isolated Python environment)
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Set the required environment variables
export OUTLAND_ROOT=/path/to/your/Outland
export JWT_SECRET=any-secret-string
export BOOTSTRAP_ADMIN_EMAIL=admin@example.com
export BOOTSTRAP_ADMIN_USERNAME=admin
export BOOTSTRAP_ADMIN_PASSWORD=adminpass

# On Windows, use 'set' instead of 'export':
# set OUTLAND_ROOT=C:\path\to\Outland
# set JWT_SECRET=any-secret-string
# ...

# Start the server
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

The `--reload` flag makes the server restart automatically when you change a Python file.

The server is now running at `http://localhost:5000`. The interactive API documentation is at `http://localhost:5000/docs`.

#### Frontend (admin UI)

You need [Node.js](https://nodejs.org/) 18 or newer.

Open a **new terminal** (keep the backend running):

```bash
cd admin-ui

# Install dependencies (only needed once)
npm install

# Start the development server
npm start
```

The admin UI is now at `http://localhost:4200`. In development mode it proxies API calls to `http://localhost:5000` automatically (configured in `proxy.conf.json`).

---

## How to Run the Tests

The tests use an in-memory SQLite database so they don't need any files or running servers.

```bash
cd monolith

# Activate the virtual environment (if not already active)
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows

# Run all tests
.venv/bin/pytest tests/ -v
```

There are 15 tests covering authentication, user management, games, assignments, filesystem access control, WebSocket notifications, and binary uploads.

## Files You Should Never Commit to Git

These are already in `.gitignore`:

| File | Why |
|---|---|
| `.env` | Contains your JWT secret and admin password |
| `users.txt` | Contains developer passwords |
| `*.db` | SQLite database files |
| `admin-ui/node_modules/` | JavaScript packages (huge, auto-downloaded) |
| `admin-ui/dist/` | Compiled Angular app (auto-generated) |

The `.example` versions of these files (`users.example.txt`, `.env.example`) are committed so teammates know what they need to create.

---

## Files and What They Do

### Backend (`monolith/`)

**`main.py`**
The main entry point of the server. Contains:
- The FastAPI app definition
- JWT token creation and validation
- Password hashing
- All routes for: `/health`, `/auth/login`, `/users/`, `/games/`, `/assignments/`
- The `bootstrap_admin()` function that creates the first admin on startup

**`database.py`**
Defines the database structure using SQLAlchemy. Contains:
- The `Role` enum (`admin`, `engine_dev`, `engine_backend_dev`, `game_dev`)
- The `User`, `Game`, `GameAssignment`, and `Binary` table models
- The database connection setup (SQLite by default)
- The `get_db()` function that routes use to get a database session

**`acl.py`**
The access control logic. Contains:
- The `Access` enum (`none`, `read`, `write`)
- `rules_for(user, game_folders)` — returns the list of path rules for a given user
- `access_for(rules, path)` — given a path, returns what access level the user has
- `list_permitted_children(rules, dir, children)` — filters a directory listing to only show what the user can see
- The `WsHub` class — manages all active WebSocket connections and broadcasts file change events to connected users who have access to the changed file

**`fs.py`**
All filesystem-related API routes:
- `GET /fs/tree` — lists files/folders filtered by the user's permissions
- `GET /fs/file` — reads a text file (returns 403 if no access)
- `GET /fs/raw` — downloads any file (images, binaries)
- `PUT /fs/file` — writes a file and broadcasts the change to all connected WebSocket clients
- `WS /fs/ws` — WebSocket endpoint; clients connect here and receive `file.changed` events in real time

**`binaries.py`**
Routes for managing engine build packages:
- `GET /binaries/` — lists builds (engine_dev only sees debug builds)
- `POST /binaries/` — admin uploads a `.zip` file with build metadata
- `GET /binaries/{id}/download` — download a build package
- `DELETE /binaries/{id}` — admin deletes a build

### Frontend (`admin-ui/src/app/`)

**`app.component.ts`**
The root component. Shows the login page if not authenticated, or the admin console if logged in.

**`app.config.ts`**
Configures Angular (enables HttpClient for API calls).

**`models.ts`**
TypeScript interfaces matching the backend's data shapes: `User`, `Game`, `Assignment`, `Binary`.

**`services/auth.service.ts`**
Handles login and logout. Stores the JWT token and current user info. All other components read from this service to know who is logged in.

**`services/api.service.ts`**
All HTTP calls to the backend. Every page component uses this service to fetch and send data. It automatically adds the `Authorization: Bearer <token>` header to every request.

**`pages/login/`** — The login form.

**`pages/console/`** — The main shell after login. Shows navigation tabs and renders the active page.

**`pages/users/`** — List users, create users, change roles, disable/delete accounts.

**`pages/games/`** — List games, create games, delete games.

**`pages/assignments/`** — Assign game_dev users to games, remove assignments.

**`pages/binaries/`** — List engine builds, upload new `.zip` packages, download or delete builds.
