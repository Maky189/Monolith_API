import os
import re
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Game, GameAssignment, Role, SessionLocal, User, get_db, init_db

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "adminpass")

VALID_FOLDER_NAME = re.compile(r'^[a-zA-Z0-9_\-]+$')

password_hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")
token_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain_password):
    return password_hasher.hash(plain_password)


def check_password(plain_password, hashed_password):
    return password_hasher.verify(plain_password, hashed_password)


def create_token(user_id, role, game_ids):
    return jwt.encode({"sub": str(user_id), "role": role, "game_ids": game_ids}, JWT_SECRET, algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


async def get_current_user(token: str = Depends(token_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(token)
        user = await db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(401, "Invalid or expired token")
        return user
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


def require_admin(user: User = Depends(get_current_user)):
    if user.role != Role.admin:
        raise HTTPException(403, "Admin only")
    return user


async def bootstrap_admin():
    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one_or_none()
        if not existing:
            db.add(User(username=ADMIN_USERNAME, email=ADMIN_EMAIL,
                        password_hash=hash_password(ADMIN_PASSWORD), role=Role.admin))
            await db.commit()


@asynccontextmanager
async def lifespan(app):
    await init_db()
    await bootstrap_admin()
    yield


app = FastAPI(title="Outland Admin API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from fs import router as fs_router
from binaries import router as binaries_router

app.include_router(fs_router)
app.include_router(binaries_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    game_ids = []
    if user.role == Role.game_dev:
        assignments = (await db.execute(
            select(GameAssignment).where(GameAssignment.user_id == user.id)
        )).scalars().all()
        for assignment in assignments:
            game_ids.append(assignment.game_id)
    return {"access_token": create_token(user.id, user.role, game_ids), "role": user.role, "user_id": user.id}


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Role = Role.game_dev


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: Role | None = None
    password: str | None = None


@app.get("/users/", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    return (await db.execute(select(User).order_by(User.id))).scalars().all()


@app.get("/users/me", response_model=UserOut)
async def get_my_profile(user: User = Depends(get_current_user)):
    return user


@app.post("/users/", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    new_user = User(username=body.username, email=body.email,
                    password_hash=hash_password(body.password), role=body.role)
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except Exception:
        raise HTTPException(400, "Username or email already exists")
    return new_user


@app.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate,
                      db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    if user_id == admin.id:
        raise HTTPException(400, "Cannot delete yourself")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()


class GameOut(BaseModel):
    id: int
    name: str
    folder_name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GameCreate(BaseModel):
    name: str
    folder_name: str
    description: str | None = None


@app.get("/games/", response_model=list[GameOut])
async def list_games(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return (await db.execute(select(Game).order_by(Game.id))).scalars().all()


@app.post("/games/", response_model=GameOut, status_code=201)
async def create_game(body: GameCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    if not VALID_FOLDER_NAME.match(body.folder_name):
        raise HTTPException(400, "folder_name: only letters, numbers, _ and - allowed")
    new_game = Game(name=body.name, folder_name=body.folder_name, description=body.description)
    db.add(new_game)
    try:
        await db.commit()
        await db.refresh(new_game)
    except Exception:
        raise HTTPException(400, "Name or folder already exists")
    return new_game


@app.delete("/games/{game_id}", status_code=204)
async def delete_game(game_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    await db.delete(game)
    await db.commit()


class AssignmentOut(BaseModel):
    id: int
    user_id: int
    game_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


@app.get("/assignments/user/{user_id}", response_model=list[AssignmentOut])
async def list_user_assignments(user_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return (await db.execute(
        select(GameAssignment).where(GameAssignment.user_id == user_id)
    )).scalars().all()


@app.post("/assignments/", response_model=AssignmentOut, status_code=201)
async def create_assignment(body: dict, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    user_id = int(body["user_id"])
    game_id = int(body["game_id"])
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role != Role.game_dev:
        raise HTTPException(400, "Only game_dev users can be assigned to games")
    already_assigned = (await db.execute(
        select(GameAssignment).where(GameAssignment.user_id == user_id, GameAssignment.game_id == game_id)
    )).scalar_one_or_none()
    if already_assigned:
        raise HTTPException(400, "Already assigned")
    new_assignment = GameAssignment(user_id=user_id, game_id=game_id)
    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)
    return new_assignment


@app.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    assignment = await db.get(GameAssignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    await db.delete(assignment)
    await db.commit()
