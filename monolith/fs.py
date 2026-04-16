import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acl import Access, access_for, hub, list_permitted_children, rules_for
from database import Game, GameAssignment, Role, SessionLocal, User, get_db
from main import decode_token, get_current_user

router = APIRouter(prefix="/fs", tags=["filesystem"])

MAX_FILE_SIZE = 2 * 1024 * 1024


def get_source_folder():
    return Path(os.getenv("OUTLAND_ROOT", "./Outland"))


def get_full_path(relative_path):
    root = get_source_folder()
    full = (root / relative_path).resolve()
    if not str(full).startswith(str(root.resolve())):
        raise ValueError("path traversal not allowed")
    return full


async def load_user_rules(user, db):
    if user.role == Role.game_dev:
        assignments = (await db.execute(
            select(GameAssignment).where(GameAssignment.user_id == user.id)
        )).scalars().all()
        game_ids = [assignment.game_id for assignment in assignments]
        games = (await db.execute(
            select(Game).where(Game.id.in_(game_ids))
        )).scalars().all()
        folder_names = [game.folder_name for game in games]
        return rules_for(user, folder_names)
    return rules_for(user, [])


class TreeEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    access: Access
    size: int | None = None


class FileContent(BaseModel):
    path: str
    content: str
    size: int
    mtime: float
    access: Access


class FileWrite(BaseModel):
    path: str
    content: str
    if_match_mtime: float | None = None


@router.get("/tree", response_model=list[TreeEntry])
async def get_tree(
    path: str = Query(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rules = await load_user_rules(user, db)
    try:
        target_folder = get_full_path(path) if path else get_source_folder()
    except ValueError as error:
        raise HTTPException(400, str(error))
    if not target_folder.is_dir():
        raise HTTPException(404, "directory not found")

    children = sorted([(item.name, item.is_dir()) for item in target_folder.iterdir()],
                      key=lambda item: (not item[1], item[0].lower()))
    visible_children = list_permitted_children(rules, path, children)

    current_dir = path.strip("/")
    result = []
    for name, is_dir, access, _ in visible_children:
        child_path = (current_dir + "/" + name) if current_dir else name
        file_size = None if is_dir else (target_folder / name).stat().st_size
        result.append(TreeEntry(name=name, path=child_path, is_dir=is_dir, access=access, size=file_size))
    return result


@router.get("/file", response_model=FileContent)
async def read_file(
    path: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rules = await load_user_rules(user, db)
    try:
        access = access_for(rules, path)
        full_path = get_full_path(path)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if access == Access.none:
        raise HTTPException(403, "no access")
    if not full_path.is_file():
        raise HTTPException(404, "file not found")
    if full_path.stat().st_size > MAX_FILE_SIZE:
        raise HTTPException(413, "file too large")
    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "binary file — use /fs/raw")
    return FileContent(path=path, content=content, size=len(content.encode()),
                       mtime=full_path.stat().st_mtime, access=access)


@router.get("/raw")
async def download_raw_file(
    path: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rules = await load_user_rules(user, db)
    try:
        access = access_for(rules, path)
        full_path = get_full_path(path)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if access == Access.none:
        raise HTTPException(403, "no access")
    if not full_path.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(full_path, filename=full_path.name)


@router.put("/file", response_model=FileContent)
async def write_file(
    body: FileWrite,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rules = await load_user_rules(user, db)
    try:
        access = access_for(rules, body.path)
        full_path = get_full_path(body.path)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if access != Access.write:
        raise HTTPException(403, "no write access")
    if full_path.is_dir():
        raise HTTPException(400, "target is a directory")
    if body.if_match_mtime is not None and full_path.exists():
        if abs(full_path.stat().st_mtime - body.if_match_mtime) > 1e-3:
            raise HTTPException(409, "file changed on server (conflict)")
    file_bytes = body.content.encode("utf-8")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(413, "content too large")
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_bytes)
    saved_mtime = full_path.stat().st_mtime
    await hub.publish(body.path, sender_id=user.id, size=len(file_bytes), mtime=saved_mtime)
    return FileContent(path=body.path, content=body.content, size=len(file_bytes), mtime=saved_mtime, access=access)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=1008)
        return
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=1008)
            return
        rules = await load_user_rules(user, db)
    await websocket.accept()
    conn = await hub.connect(websocket, user_id=user_id, rules=rules)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(conn)
