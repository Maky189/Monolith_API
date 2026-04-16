import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Binary, Role, User, get_db
from main import get_current_user, require_admin

router = APIRouter(prefix="/binaries", tags=["binaries"])


def get_uploads_folder():
    return Path(os.getenv("BINARIES_DIR", "./binaries"))


class BinaryOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    kind: str
    platform: str
    version: str
    filename: str
    size_bytes: int
    uploaded_by: int | None
    created_at: str

    @classmethod
    def from_orm(cls, binary):
        return cls(
            id=binary.id,
            kind=binary.kind,
            platform=binary.platform,
            version=binary.version,
            filename=binary.filename,
            size_bytes=binary.size_bytes,
            uploaded_by=binary.uploaded_by,
            created_at=binary.created_at.isoformat(),
        )


def user_can_see(role, build_kind):
    if role == Role.admin:
        return True
    if role == Role.game_dev:
        return build_kind in ("debug", "release")
    return build_kind == "debug"


@router.get("/", response_model=list[BinaryOut])
async def list_binaries(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    all_binaries = (await db.execute(select(Binary).order_by(Binary.id.desc()))).scalars().all()
    visible = []
    for binary in all_binaries:
        if user_can_see(user.role, binary.kind):
            visible.append(BinaryOut.from_orm(binary))
    return visible


@router.post("/", response_model=BinaryOut, status_code=201)
async def upload_binary(
    kind: str = Form(...),
    platform: str = Form(...),
    version: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if kind not in ("debug", "release"):
        raise HTTPException(400, "kind must be debug or release")
    if platform not in ("linux", "windows"):
        raise HTTPException(400, "platform must be linux or windows")
    file_name = Path(file.filename or "binary").name
    if not file_name.lower().endswith(".zip"):
        raise HTTPException(400, "must be a .zip archive")

    uploads_folder = get_uploads_folder()
    uploads_folder.mkdir(parents=True, exist_ok=True)
    saved_path = uploads_folder / (uuid.uuid4().hex + "_" + file_name)
    file_data = await file.read()
    saved_path.write_bytes(file_data)

    new_binary = Binary(
        kind=kind,
        platform=platform,
        version=version,
        filename=file_name,
        storage_path=str(saved_path),
        size_bytes=len(file_data),
        uploaded_by=admin.id,
    )
    db.add(new_binary)
    await db.commit()
    await db.refresh(new_binary)
    return BinaryOut.from_orm(new_binary)


@router.get("/{binary_id}/download")
async def download_binary(
    binary_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    binary = await db.get(Binary, binary_id)
    if not binary:
        raise HTTPException(404, "not found")
    if not user_can_see(user.role, binary.kind):
        raise HTTPException(403, "not allowed for your role")
    saved_file = Path(binary.storage_path)
    if not saved_file.exists():
        raise HTTPException(410, "file missing on disk")
    return FileResponse(saved_file, filename=binary.filename, media_type="application/octet-stream")


@router.delete("/{binary_id}", status_code=204)
async def delete_binary(
    binary_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    binary = await db.get(Binary, binary_id)
    if not binary:
        raise HTTPException(404, "not found")
    saved_file = Path(binary.storage_path)
    if saved_file.exists():
        saved_file.unlink()
    await db.delete(binary)
    await db.commit()
