from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_super_admin
from app.repositories import dropbox as dropbox_repo
from app.schemas.dropbox import DropboxConnectionCreate, DropboxConnectionResponse, DropboxConnectionUpdate, DropboxSyncResponse
from app.services import dropbox as dropbox_service

router = APIRouter(prefix="/api/dropbox", tags=["Dropbox Import"])


@router.get("/connections", response_model=list[DropboxConnectionResponse])
async def list_connections(_: dict = Depends(require_super_admin)):
    return [dropbox_service.public_connection(row) for row in await dropbox_repo.list_connections()]


@router.post("/connections", response_model=DropboxConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(payload: DropboxConnectionCreate, _: dict = Depends(require_super_admin)):
    try:
        return await dropbox_service.create_connection(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/connections/{connection_id}", response_model=DropboxConnectionResponse)
async def get_connection(connection_id: int, _: dict = Depends(require_super_admin)):
    record = await dropbox_repo.get_connection(connection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dropbox connection not found")
    return dropbox_service.public_connection(record)


@router.patch("/connections/{connection_id}", response_model=DropboxConnectionResponse)
async def update_connection(connection_id: int, payload: DropboxConnectionUpdate, _: dict = Depends(require_super_admin)):
    try:
        record = await dropbox_service.update_connection(connection_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not record:
        raise HTTPException(status_code=404, detail="Dropbox connection not found")
    return record


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: int, _: dict = Depends(require_super_admin)):
    if not await dropbox_repo.get_connection(connection_id):
        raise HTTPException(status_code=404, detail="Dropbox connection not found")
    await dropbox_repo.delete_connection(connection_id)


@router.post("/connections/{connection_id}/sync", response_model=DropboxSyncResponse)
async def sync_connection(connection_id: int, user: dict = Depends(require_super_admin)):
    try:
        return await dropbox_service.sync_connection(connection_id, actor_user_id=int(user["id"]))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/connections/{connection_id}/imports")
async def import_history(connection_id: int, _: dict = Depends(require_super_admin)):
    if not await dropbox_repo.get_connection(connection_id):
        raise HTTPException(status_code=404, detail="Dropbox connection not found")
    return await dropbox_repo.list_imports(connection_id)

