"""CRUD API for AI tag synonym groups."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies.auth import require_super_admin
from app.repositories import ai_tag_synonyms as repo

router = APIRouter(prefix="/api/chat/ai-tag-synonyms", tags=["Chat"])


class SynonymGroupInput(BaseModel):
    terms: list[str] = Field(min_length=2, max_length=repo.MAX_TERMS_PER_GROUP)


class SynonymGroupResponse(BaseModel):
    id: int
    terms: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _invalid(exc: repo.InvalidSynonymGroup) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=list[SynonymGroupResponse], summary="List AI tag synonym groups")
async def list_ai_tag_synonym_groups(_: dict = Depends(require_super_admin)):
    return await repo.list_groups()


@router.post("", response_model=SynonymGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_tag_synonym_group(body: SynonymGroupInput, _: dict = Depends(require_super_admin)):
    try:
        return await repo.create_group(body.terms)
    except repo.InvalidSynonymGroup as exc:
        raise _invalid(exc) from exc


@router.get("/{group_id}", response_model=SynonymGroupResponse)
async def get_ai_tag_synonym_group(group_id: int, _: dict = Depends(require_super_admin)):
    group = await repo.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    return group


@router.put("/{group_id}", response_model=SynonymGroupResponse)
async def update_ai_tag_synonym_group(body: SynonymGroupInput, group_id: int, _: dict = Depends(require_super_admin)):
    try:
        group = await repo.update_group(group_id, body.terms)
    except repo.InvalidSynonymGroup as exc:
        raise _invalid(exc) from exc
    if not group:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_tag_synonym_group(group_id: int, _: dict = Depends(require_super_admin)) -> None:
    if not await repo.delete_group(group_id):
        raise HTTPException(status_code=404, detail="Synonym group not found")
