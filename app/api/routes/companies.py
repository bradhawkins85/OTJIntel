from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.api.dependencies.auth import get_current_user, require_helpdesk_technician, require_super_admin
from app.api.dependencies.database import require_database
from app.repositories import assets as assets_repo
from app.repositories import companies as company_repo
from app.repositories import company_memberships as membership_repo
from app.repositories import staff as staff_repo
from app.schemas.assets import AssetResponse
from app.schemas.companies import CompanyCreate, CompanyResponse, CompanyUpdate
from app.schemas.users import StaffRequesterOption
from app.services import audit as audit_service
from app.services import m365 as m365_service

router = APIRouter(prefix="/api/companies", tags=["Companies"])
EMAIL_ADAPTER = TypeAdapter(EmailStr)


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    include_archived: bool = False,
    _: None = Depends(require_database),
    __: dict = Depends(require_super_admin),
):
    rows = await company_repo.list_companies(include_archived=include_archived)
    return rows


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    request: Request,
    _: None = Depends(require_database),
    current_user: dict = Depends(require_super_admin),
):
    created = await company_repo.create_company(**payload.model_dump())
    company_id = created.get("id")
    
    # Lookup missing external IDs after creating the company
    if company_id:
        try:
            await company_id_lookup.lookup_missing_company_ids(company_id)
            # Fetch the updated company to return with any newly found IDs
            updated = await company_repo.get_company_by_id(company_id)
            if updated:
                created = updated
        except Exception:
            # If lookup fails, still return the created company
            pass

    await audit_service.record(
        action="company.create",
        request=request,
        user_id=int(current_user["id"]),
        entity_type="company",
        entity_id=int(created["id"]) if created.get("id") is not None else None,
        before=None,
        after=created,
    )
    return created


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    _: None = Depends(require_database),
    __: dict = Depends(require_super_admin),
):
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    request: Request,
    _: None = Depends(require_database),
    current_user: dict = Depends(require_super_admin),
):
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    data = payload.model_dump(exclude_unset=True)
    updated = await company_repo.update_company(company_id, **data)
    
    # Check if any external IDs are missing and lookup if needed
    has_missing_ids = (
        not updated.get("syncro_company_id") or
        not updated.get("tacticalrmm_client_id") or
        not updated.get("xero_id") or
        not updated.get("huntress_organization_id")
        or not updated.get("huntress_sat_account_id")
    )
    
    final_record: dict[str, Any] = updated
    if has_missing_ids:
        try:
            await company_id_lookup.lookup_missing_company_ids(company_id)
            # Fetch the updated company to return with any newly found IDs
            refreshed = await company_repo.get_company_by_id(company_id)
            if refreshed:
                final_record = refreshed
        except Exception:
            # If lookup fails, still return the updated company
            pass

    await audit_service.record(
        action="company.update",
        request=request,
        user_id=int(current_user["id"]),
        entity_type="company",
        entity_id=company_id,
        before=company,
        after=final_record,
    )
    return final_record


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    request: Request,
    _: None = Depends(require_database),
    current_user: dict = Depends(require_super_admin),
):
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    await company_repo.delete_company(company_id)
    await audit_service.record(
        action="company.delete",
        request=request,
        user_id=int(current_user["id"]),
        entity_type="company",
        entity_id=company_id,
        before=company,
        after=None,
    )
    return None


@router.post("/{company_id}/archive", response_model=CompanyResponse)
async def archive_company(
    company_id: int,
    request: Request,
    _: None = Depends(require_database),
    current_user: dict = Depends(require_super_admin),
):
    """Archive a company. Archived companies are hidden throughout the platform."""
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    updated = await company_repo.archive_company(company_id)
    await audit_service.record(
        action="company.archive",
        request=request,
        user_id=int(current_user["id"]),
        entity_type="company",
        entity_id=company_id,
        before=company,
        after=updated,
    )
    return updated


@router.post("/{company_id}/unarchive", response_model=CompanyResponse)
async def unarchive_company(
    company_id: int,
    request: Request,
    _: None = Depends(require_database),
    current_user: dict = Depends(require_super_admin),
):
    """Unarchive a company."""
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    updated = await company_repo.unarchive_company(company_id)
    await audit_service.record(
        action="company.unarchive",
        request=request,
        user_id=int(current_user["id"]),
        entity_type="company",
        entity_id=company_id,
        before=company,
        after=updated,
    )
    return updated


@router.get("/{company_id}/staff-users", response_model=list[StaffRequesterOption])
async def list_company_staff_users(
    company_id: int,
    _: None = Depends(require_database),
    __: dict = Depends(require_helpdesk_technician),
):
    """Get enabled staff members as users for the specified company.
    
    This endpoint returns user records (with user IDs) for enabled staff members,
    which can be used for selecting requesters when creating tickets.
    """
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    users = await staff_repo.list_enabled_staff_users(company_id)
    requester_options: list[StaffRequesterOption] = []
    for user in users:
        try:
            EMAIL_ADAPTER.validate_python(user.get("email"))
        except ValidationError:
            continue
        requester_options.append(StaffRequesterOption.model_validate(user))
    return requester_options




@router.get("/{company_id}/members")
async def list_company_members(
    company_id: int,
    _: None = Depends(require_database),
    current_user: dict = Depends(get_current_user),
):
    """Get company members (users with active memberships).
    
    This endpoint returns users who are members of the company,
    which can be used for assigning quotes and other company-specific tasks.
    Returns a list in the format: {"members": [{"user_id": X, "email": "..."}]}
    """
    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    if not current_user.get("is_super_admin"):
        try:
            user_id = int(current_user.get("id"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from None

        has_helpdesk_access = await membership_repo.user_has_permission(user_id, "helpdesk.technician")
        membership = await membership_repo.get_membership_by_company_user(company_id, user_id)
        is_company_member = bool(membership and membership.get("status") == "active")
        if not has_helpdesk_access and not is_company_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get all memberships for this company
    memberships = await membership_repo.list_company_memberships(company_id)
    
    # Transform to the format expected by the frontend
    members = [
        {
            "user_id": membership.get("user_id"),
            "email": membership.get("user_email"),
        }
        for membership in memberships
    ]

    return {"members": members}
@router.get("/{company_id}/assets", response_model=list[AssetResponse])
async def list_company_assets(
    company_id: int,
    _: None = Depends(require_database),
    current_user: dict = Depends(require_helpdesk_technician),
):
    if not current_user.get("is_super_admin"):
        user_id = current_user.get("id")
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from None

        membership = await membership_repo.get_membership_by_company_user(company_id, user_id_int)
        if not membership or membership.get("status") != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    company = await company_repo.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    rows = await assets_repo.list_company_assets(company_id)
    assets: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        for numeric_key in ("ram_gb", "approx_age", "performance_score"):
            value = record.get(numeric_key)
            if value is None or value == "":
                record[numeric_key] = None
                continue
            try:
                record[numeric_key] = float(value)
            except (TypeError, ValueError):
                record[numeric_key] = None
        assets.append(record)
    return assets
