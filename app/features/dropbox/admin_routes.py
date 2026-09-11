from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings
from app.repositories import dropbox as dropbox_repo
from app.security.flash import flash_redirect
from app.services import audit as audit_service
from app.services import dropbox as dropbox_service

router = APIRouter(tags=["Dropbox Import"])
state_signer = URLSafeTimedSerializer(get_settings().secret_key, salt="dropbox-oauth")


def _main():
    from app import main
    return main


async def _page(request: Request, user: dict, *, error: str | None = None, result: dict | None = None, status_code: int = 200):
    connections = [dropbox_service.public_connection(row) for row in await dropbox_repo.list_connections()]
    history = {row["id"]: await dropbox_repo.list_imports(int(row["id"]), 25) for row in connections}
    response = await _main()._render_template("admin/dropbox.html", request, user, extra={
        "title": "Dropbox import", "connections": connections, "import_history": history,
        "error_message": error, "sync_result": result,
    })
    response.status_code = status_code
    return response


@router.get("/admin/modules/dropbox", response_class=HTMLResponse)
async def dashboard(request: Request):
    user, redirect = await _main()._require_super_admin_page(request)
    if redirect:
        return redirect
    return await _page(request, user)


@router.post("/admin/modules/dropbox/connections")
async def create_connection(request: Request):
    user, redirect = await _main()._require_super_admin_page(request)
    if redirect:
        return redirect
    form = await request.form()
    try:
        record = await dropbox_service.create_connection({
            "name": form.get("name"), "app_key": form.get("appKey"),
            "app_secret": form.get("appSecret"), "root_path": form.get("rootPath"),
            "active": form.get("active") == "on",
        })
    except ValueError as exc:
        return await _page(request, user, error=str(exc), status_code=400)
    await audit_service.record(action="dropbox.connection.create", request=request, user_id=int(user["id"]), entity_type="dropbox_connection", entity_id=record["id"])
    return flash_redirect("/admin/modules/dropbox", "Dropbox configuration created. Connect it to authorize access.", "success")


@router.post("/admin/modules/dropbox/connections/{connection_id}/delete")
async def delete_connection(connection_id: int, request: Request):
    user, redirect = await _main()._require_super_admin_page(request)
    if redirect:
        return redirect
    if await dropbox_repo.get_connection(connection_id):
        await dropbox_repo.delete_connection(connection_id)
        await audit_service.record(action="dropbox.connection.delete", request=request, user_id=int(user["id"]), entity_type="dropbox_connection", entity_id=connection_id)
    return flash_redirect("/admin/modules/dropbox", "Dropbox configuration deleted.", "success")


@router.get("/admin/modules/dropbox/connections/{connection_id}/authorize")
async def authorize(connection_id: int, request: Request):
    _, redirect = await _main()._require_super_admin_page(request)
    if redirect:
        return redirect
    record = await dropbox_repo.get_connection(connection_id)
    if not record:
        return flash_redirect("/admin/modules/dropbox", "Dropbox configuration not found.", "error")
    callback = str(request.url_for("dropbox_oauth_callback"))
    state = state_signer.dumps({"connection_id": connection_id})
    params = {"client_id": record["app_key"], "response_type": "code", "token_access_type": "offline", "redirect_uri": callback, "state": state}
    return RedirectResponse("https://www.dropbox.com/oauth2/authorize?" + urlencode(params), status_code=303)


@router.get("/admin/modules/dropbox/oauth/callback", name="dropbox_oauth_callback")
async def oauth_callback(request: Request, code: str = "", state: str = "", error_description: str = ""):
    user, redirect = await _main()._require_super_admin_page(request)
    if redirect:
        return redirect
    if error_description:
        return flash_redirect("/admin/modules/dropbox", error_description, "error")
    try:
        payload = state_signer.loads(state, max_age=600)
        connection_id = int(payload["connection_id"])
        await dropbox_service.exchange_authorization_code(connection_id, code, str(request.url_for("dropbox_oauth_callback")))
    except (BadSignature, SignatureExpired, KeyError, ValueError) as exc:
        return flash_redirect("/admin/modules/dropbox", f"Dropbox authorization failed: {exc}", "error")
    await audit_service.record(action="dropbox.connection.authorize", request=request, user_id=int(user["id"]), entity_type="dropbox_connection", entity_id=connection_id)
    return flash_redirect("/admin/modules/dropbox", "Dropbox account connected.", "success")


@router.post("/admin/modules/dropbox/connections/{connection_id}/sync")
async def sync(connection_id: int, request: Request):
    user, redirect = await _main()._require_super_admin_page(request)
    if redirect:
        return redirect
    try:
        result = await dropbox_service.sync_connection(connection_id, actor_user_id=int(user["id"]))
    except Exception as exc:
        return await _page(request, user, error=f"Dropbox import failed: {exc}", status_code=502)
    await audit_service.record(action="dropbox.connection.sync", request=request, user_id=int(user["id"]), entity_type="dropbox_connection", entity_id=connection_id, after=result)
    return await _page(request, user, result=result)

