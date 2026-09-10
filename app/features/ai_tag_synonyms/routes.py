"""Super-admin HTML routes for managing AI tag synonyms."""

from urllib.parse import quote

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.repositories import ai_tag_synonyms as repo

router = APIRouter(tags=["Chat"])


def _main():
    from app import main
    return main


def _terms(raw: object) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",")]


def _redirect(error: str | None = None) -> RedirectResponse:
    target = "/admin/chat/ai-tag-synonyms"
    if error:
        target += f"?error={quote(error)}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/chat/ai-tag-synonyms", response_class=HTMLResponse)
async def ai_tag_synonyms_page(request: Request):
    main = _main()
    user, redirect = await main._require_super_admin_page(request)
    if redirect:
        return redirect
    return await main._render_template(
        "admin/matrix_chat_configuration.html", request, user,
        extra={"title": "AI Tag Synonyms", "synonym_groups": await repo.list_groups(),
               "error_message": request.query_params.get("error")},
    )


@router.post("/admin/chat/ai-tag-synonyms")
async def create_ai_tag_synonym(request: Request):
    main = _main()
    _, redirect = await main._require_super_admin_page(request)
    if redirect:
        return redirect
    form = await request.form()
    try:
        await repo.create_group(_terms(form.get("terms")))
    except repo.InvalidSynonymGroup as exc:
        return _redirect(str(exc))
    return _redirect()


@router.post("/admin/chat/ai-tag-synonyms/{group_id}")
async def update_ai_tag_synonym(group_id: int, request: Request):
    main = _main()
    _, redirect = await main._require_super_admin_page(request)
    if redirect:
        return redirect
    form = await request.form()
    try:
        group = await repo.update_group(group_id, _terms(form.get("terms")))
    except repo.InvalidSynonymGroup as exc:
        return _redirect(str(exc))
    return _redirect(None if group else "Synonym group not found")


@router.post("/admin/chat/ai-tag-synonyms/{group_id}/delete")
async def delete_ai_tag_synonym(group_id: int, request: Request):
    main = _main()
    _, redirect = await main._require_super_admin_page(request)
    if redirect:
        return redirect
    deleted = await repo.delete_group(group_id)
    return _redirect(None if deleted else "Synonym group not found")
