from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import random
import re
import secrets
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html import escape
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import parse_qsl, quote, urlencode, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiomysql
import httpx
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.params import Form as FormField
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import ValidationError
from starlette.datastructures import FormData, URL
from http import HTTPStatus

from app.api.routes import (
    ai_tag_synonyms,
    api_keys,
    asset_custom_fields,
    audit_logs,
    auth,
    automations as automations_api,
    bc5,
    bc11,
    bcp,
    business_continuity_plans as bc_plans_api,
    companies,
    dashboard as dashboard_api,
    essential8 as essential8_api,
    compliance_checks as compliance_checks_api,
    email_blocklist as email_blocklist_api,
    issues as issues_api,
    knowledge_base as knowledge_base_api,
    licenses as licenses_api,
    memberships,
    message_templates as message_templates_api,
    modules as modules_api,
    notifications,
    ports,
    plugins as plugins_api,
    scheduler as scheduler_api,
    roles,
    service_status as service_status_api,
    staff as staff_api,
    tag_exclusions,
    tickets as tickets_api,
    users,
    system,
    features as features_api,
)
from uuid import uuid4

from app.core.config import get_settings, get_templates_config
from app.core.database import db
from app.core.features import init_registry
from app.core.plugin_loader import get_plugin_loader, init_plugin_loader
from app.core.logging import configure_logging, log_error, log_info, log_warning
from loguru import logger
from app.repositories import access_activity as access_activity_repo
from app.repositories import audit_logs as audit_repo
from app.repositories import api_keys as api_key_repo
from app.repositories import auth as auth_repo
from app.repositories import assets as assets_repo
from app.repositories import companies as company_repo
from app.repositories import company_memberships as membership_repo
from app.repositories import change_log as change_log_repo
from app.repositories import assets as asset_repo
from app.repositories import licenses as license_repo
from app.repositories import license_sku_friendly_names as sku_friendly_repo
from app.repositories import knowledge_base as knowledge_base_repo
from app.repositories import m365 as m365_repo
from app.repositories import notifications as notifications_repo
from app.repositories import reporting as reporting_repo
from app.repositories import roles as role_repo
from app.repositories import scheduled_tasks as scheduled_tasks_repo
from app.repositories import staff as staff_repo
from app.repositories import staff_onboarding_workflows as staff_workflow_repo
from app.repositories import staff_requests as staff_requests_repo
from app.repositories import pending_staff_access as pending_staff_access_repo
from app.repositories import tickets as tickets_repo
from app.repositories import rag_index as rag_index_repo
from app.repositories import rag_relationships as rag_relationship_repo
from app.repositories import ticket_attachments as attachments_repo
from app.repositories import ticket_expenses as expenses_repo
from app.repositories import ticket_views as ticket_views_repo
from app.repositories import ticket_statuses as ticket_status_repo
from app.repositories import automations as automation_repo
from app.repositories import integration_modules as integration_modules_repo
from app.repositories import user_companies as user_company_repo
from app.repositories import users as user_repo
from app.security.menu_permissions import MENU_PERMISSIONS, catalogue_for_api, menu_has_access, normalize_access_level, normalize_menu_permissions
from app.repositories import issues as issues_repo
from app.repositories import asset_custom_fields as asset_custom_fields_repo
from app.repositories import staff_custom_fields as staff_custom_fields_repo
from app.repositories import site_settings as site_settings_repo
from app.schemas.staff_onboarding_workflows import (
    CompanyWorkflowPolicyUpsertSchema,
    WorkflowConfigSchema,
)
from app.security.cache_control import CacheControlMiddleware
from app.security.client_ip import get_client_ip
from app.security.csrf import CSRFMiddleware
from app.security.encryption import decrypt_secret, encrypt_secret
from app.security.flash import flash_redirect, set_flash
from app.security.ip_whitelist import IPWhitelistMiddleware
from app.security.rate_limiter import (
    EndpointRateLimiter,
    EndpointRateLimiterMiddleware,
    RateLimiterMiddleware,
    SimpleRateLimiter,
)
from app.security.request_logger import RequestLoggingMiddleware
from app.security.security_headers import SecurityHeadersMiddleware
from app.security.session import SessionData, session_manager
from app.api.dependencies.auth import get_current_session
from app.services.scheduler import scheduler_service, COMMANDS_BY_MODULE
from app.services import audit as audit_service
from app.services import background as background_tasks
from app.services import automations as automations_service
from app.services import change_log as change_log_service
from app.services import cron_calendar as cron_calendar_service
from app.services import company_domains
from app.services import company_access
from app.services import dashboard as dashboard_service
from app.services import email as email_service
from app.services import rag_relationships as rag_relationship_service
from app.services import m365 as m365_service
from app.services import modules as modules_service
from app.services import notification_event_settings as event_settings_service
from app.services import message_templates as message_templates_service
from app.services import staff_access as staff_access_service
from app.services import staff_field_config as staff_field_config_service
from app.services import staff_onboarding_workflows as staff_onboarding_workflow_service
from app.services import labour_types as labour_types_service
from app.services import tickets as tickets_service
from app.services import rag_index as rag_index_service
from app.services import ticket_attachments as attachments_service
from app.services import template_variables
from app.services import webhook_monitor
from app.services import issues as issues_service
from app.services import reporting as reporting_service
from app.services import service_status as service_status_service
from app.services import system_state as system_state_service
from app.services import impersonation as impersonation_service
from app.services.realtime import refresh_notifier
from app.services.redis import close_redis_client, get_redis_client
from app.services.sanitization import sanitize_rich_text

configure_logging()
settings = get_settings()
templates_config = get_templates_config()
oauth_state_serializer = URLSafeSerializer(settings.secret_key, salt="m365-oauth")
PWA_THEME_COLOR = "#0f172a"
PWA_BACKGROUND_COLOR = "#0f172a"
_TICKET_DASHBOARD_REFERENCE_TTL_SECONDS = 60
_ticket_dashboard_reference_cache: dict[str, Any] = {
    "expires_at": None,
    "modules": [],
    "companies": [],
    "technicians": [],
    "company_lookup": {},
    "user_lookup": {},
}
_ticket_dashboard_reference_lock = asyncio.Lock()
_M365_PROVISION_PKCE_TTL_SECONDS = 600
_m365_provision_pkce_cache: dict[str, tuple[str, datetime]] = {}
_m365_provision_pkce_lock = asyncio.Lock()


async def _store_m365_provision_code_verifier(verifier: str) -> str:
    """Store a one-time PKCE code verifier for the M365 provision flow."""

    verifier_id = secrets.token_urlsafe(24)
    redis_client = get_redis_client()
    if redis_client is not None:
        await redis_client.setex(
            f"m365:provision:pkce:{verifier_id}",
            _M365_PROVISION_PKCE_TTL_SECONDS,
            verifier,
        )
        return verifier_id

    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=_M365_PROVISION_PKCE_TTL_SECONDS
    )
    async with _m365_provision_pkce_lock:
        _m365_provision_pkce_cache[verifier_id] = (verifier, expires_at)
    return verifier_id


async def _pop_m365_provision_code_verifier(verifier_id: str | None) -> str | None:
    """Return and remove a previously stored one-time PKCE code verifier."""

    if not verifier_id:
        return None

    redis_client = get_redis_client()
    if redis_client is not None:
        key = f"m365:provision:pkce:{verifier_id}"
        pipeline = redis_client.pipeline()
        pipeline.get(key)
        pipeline.delete(key)
        value, _ = await pipeline.execute()
        if not value:
            return None
        return str(value)

    now = datetime.now(timezone.utc)
    async with _m365_provision_pkce_lock:
        stale_keys = [
            key
            for key, (_, expires_at) in _m365_provision_pkce_cache.items()
            if expires_at <= now
        ]
        for key in stale_keys:
            _m365_provision_pkce_cache.pop(key, None)
        entry = _m365_provision_pkce_cache.pop(verifier_id, None)
    if entry is None:
        return None
    verifier, expires_at = entry
    if expires_at <= now:
        return None
    return verifier

# Load app version for cache busting static files
_APP_VERSION = ""
_version_file = Path(__file__).resolve().parent.parent / "version.txt"
if _version_file.is_file():
    try:
        _APP_VERSION = _version_file.read_text().strip()
    except Exception:
        pass

_PWA_SERVICE_WORKER_PATH = templates_config.static_path / "service-worker.js"
_PWA_ICON_SOURCES = [
    {
        "src": "/static/logo.svg",
        "sizes": "192x192",
        "type": "image/svg+xml",
        "purpose": "any",
    },
    {
        "src": "/static/logo.svg",
        "sizes": "512x512",
        "type": "image/svg+xml",
        "purpose": "any",
    },
    {
        "src": "/static/logo.svg",
        "sizes": "any",
        "type": "image/svg+xml",
        "purpose": "any maskable",
    },
]
def _random_daily_cron() -> str:
    """Return a randomised daily cron expression (``MM HH * * *``)."""
    minute = random.randint(0, 59)
    hour = random.randint(0, 23)
    return f"{minute} {hour} * * *"




async def _store_pkce_verifier(code_verifier: str) -> str:
    """Store a PKCE code_verifier server-side and return an opaque handle."""

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=_PKCE_VERIFIER_TTL_SECONDS)
    handle = secrets.token_urlsafe(32)
    async with _pkce_verifier_store_lock:
        # Opportunistically purge expired entries.
        expired_handles = [
            key for key, (_, expiry) in _pkce_verifier_store.items() if expiry <= now
        ]
        for key in expired_handles:
            _pkce_verifier_store.pop(key, None)
        _pkce_verifier_store[handle] = (code_verifier, expires_at)
    return handle


async def _pop_pkce_verifier(handle: str) -> str | None:
    """Consume a stored PKCE verifier handle and return the verifier once."""

    now = datetime.now(timezone.utc)
    async with _pkce_verifier_store_lock:
        value = _pkce_verifier_store.pop(handle, None)
    if not value:
        return None
    verifier, expires_at = value
    if expires_at <= now:
        return None
    return verifier


def _serialise_for_json(value: Any) -> Any:
    """Convert mappings and sequences to JSON-safe primitives for templates."""

    if isinstance(value, datetime):
        target = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return target.astimezone(timezone.utc).isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _serialise_for_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialise_for_json(item) for item in value]
    return value
tags_metadata = [
    {
        "name": "API Keys",
        "description": "Super-admin management of API credentials with usage telemetry.",
    },
    {
        "name": "Assets",
        "description": "Device inventory, warranty status, and Syncro asset synchronisation endpoints.",
    },
    {"name": "Audit Logs", "description": "Structured audit trail of privileged actions."},
    {"name": "Auth", "description": "Authentication, registration, and session management."},
    {
        "name": "Automations",
        "description": "Workflow automations combining scheduling, event triggers, and module actions.",
    },
    {
        "name": "Business Continuity (BC5)",
        "description": "Comprehensive BC planning API with templates, plans, versions, workflows, attachments, and exports. Implements RBAC with viewer, editor, approver, and admin roles.",
    },
    {
        "name": "ChatGPT MCP",
        "description": "Expose secure Model Context Protocol tooling for ChatGPT ticket triage and updates.",
    },
    {"name": "Companies", "description": "Company catalogue and membership management."},
    {
        "name": "Forms",
        "description": "OpnForm publishing, company assignments, and secure embedding endpoints.",
    },
    {
        "name": "Integration Modules",
        "description": "Manage external module credentials for Ollama, SMTP, TacticalRMM, ntfy, and ChatGPT MCP.",
    },
    {"name": "Invoices", "description": "Invoice catalogue, status tracking, and reconciliation APIs."},
    {
        "name": "Knowledge Base",
        "description": "Permission-scoped articles with Ollama-assisted semantic search.",
    },
    {
        "name": "Agent",
        "description": "AI-assisted portal agent powered by the Ollama module with permission-aware context.",
    },
    {
        "name": "Licenses",
        "description": "Software license catalogue, assignments, and ordering workflows.",
    },
    {
        "name": "Memberships",
        "description": "Company membership workflows with approval tracking.",
    },
    {
        "name": "Message Templates",
        "description": "Reusable email and message bodies for automations and integrations.",
    },
    {"name": "Notifications", "description": "System-wide and user-specific notification feeds."},
    {"name": "Office365", "description": "Microsoft 365 credential management and synchronisation APIs."},
    {"name": "Ports", "description": "Port catalogue, document storage, and pricing workflow APIs."},
    {"name": "Roles", "description": "Role definitions and access controls."},
    {"name": "Shop", "description": "Product catalogue management and visibility controls."},
    {
        "name": "Shop Packages",
        "description": "Pre-built bundles of products designed to simplify repeat ordering workflows.",
    },
    {
        "name": "Staff",
        "description": "Staff directory management, Syncro contact synchronisation, and verification workflows.",
    },
    {
        "name": "System",
        "description": "Administrative system controls and realtime refresh notifications.",
    },
    {
        "name": "Tickets",
        "description": "Ticketing workspace with replies, watchers, and module-aligned categorisation.",
    },
    {
        "name": "Users",
        "description": "User administration, profile management, and self-service endpoints.",
    },
]

# Human-readable labels for scheduled task commands used when auto-generating task names.
TASK_COMMAND_LABELS: dict[str, str] = {
    "update_mac_vendors": "Update MAC vendor list",
    "sync_staff": "Sync staff directory",
    "sync_m365_data": "Sync Microsoft 365 data (legacy)",
    "sync_m365_licenses": "Sync Microsoft 365 licenses",
    "sync_m365_contacts": "Sync Microsoft 365 contacts",
    "refresh_m365_consent_status": "Refresh Microsoft 365 consent status",
    "unbill_time_entries": "Un-Bill Time Entries",
    "create_scheduled_ticket": "Create scheduled ticket",
    "rag_index_start": "RAG start indexing",
    "rag_index_stop": "RAG stop indexing",
    "rag_matching_pause": "RAG pause matching",
    "rag_matching_resume": "RAG resume matching",
    "rag_cleanup_stale_matches": "RAG cleanup stale matches",
    "sync_tactical_assets": "Sync Tactical RMM assets",
    "system_update": "Update MyPortal system",
}


def _scheduled_task_command_label(command: str) -> str:
    """Return a friendly display label for a scheduled task command."""
    if command in TASK_COMMAND_LABELS:
        return TASK_COMMAND_LABELS[command]
    return command.replace("_", " ").replace(":", " ").strip().title()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Customer portal API exposing authentication, company administration, port catalogue, "
        "and pricing workflow capabilities."
    ),
    docs_url=None,
    openapi_url=None,
    openapi_tags=tags_metadata,
)


@app.on_event("startup")
async def _load_message_template_cache() -> None:
    try:
        await message_templates_service.preload_cache()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to preload message templates", error=str(exc))


@app.on_event("startup")
async def _start_refresh_notifier() -> None:
    try:
        await refresh_notifier.start(redis_client=get_redis_client())
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to initialise refresh notifier", error=str(exc))


@app.on_event("shutdown")
async def _shutdown_integrations() -> None:
    await refresh_notifier.stop()
    await close_redis_client()

SWAGGER_UI_PATH = settings.swagger_ui_url or "/docs"
PROTECTED_OPENAPI_PATH = "/internal/openapi.json"


async def _get_extra_csp_script_sources() -> list[str]:
    """Get additional CSP script sources from enabled modules.
    
    This function retrieves script sources that need to be allowed in the
    Content-Security-Policy, such as analytics scripts from enabled modules.
    
    Returns:
        List of valid HTTPS URLs to allow as script sources
    """
    return []


# Configure CORS with security-first defaults
# If ALLOWED_ORIGINS is not configured, only allow same-origin requests (empty list)
allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()] if settings.allowed_origins else []

# Log warning if wildcard CORS is detected (should never happen with current config)
if "*" in allowed_origins:
    logger.warning(
        "SECURITY WARNING: Wildcard CORS origin (*) detected. "
        "This allows any website to make requests to this API. "
        "Configure ALLOWED_ORIGINS in .env for production use."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    # Restrict to the specific headers the portal actually uses. Using ``*``
    # together with ``allow_credentials=True`` is permissive and hides bugs
    # where the browser would otherwise reject a cross-origin request.
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Authorization",
        "Cache-Control",
        "Content-Language",
        "Content-Type",
        "If-Match",
        "If-None-Match",
        "X-API-Key",
        "X-CSRF-Token",
        "X-CSRFToken",
        "X-Requested-With",
        "X-Request-ID",
    ],
    expose_headers=["X-Request-ID"],
)

# Add IP whitelisting middleware for sensitive endpoints
# This provides an additional layer of security by restricting access based on IP address
if settings.ip_whitelist_enabled and settings.ip_whitelist:
    whitelist_entries = [entry.strip() for entry in settings.ip_whitelist.split(",") if entry.strip()]
    
    # Determine which paths to protect
    protected_paths = ["/admin"]
    if not settings.ip_whitelist_admin_only:
        protected_paths.append("/api")
    
    # Exempt public endpoints from IP whitelisting
    exempt_paths = [
        "/static",
        "/health",
        "/healthz",
        "/readyz",
        "/login",
        "/register",
        "/api/auth/login",
        "/api/auth/register",
        "/api/webhooks",  # Webhooks use signature verification instead
        "/manifest.webmanifest",
        "/service-worker.js",
    ]
    
    app.add_middleware(
        IPWhitelistMiddleware,
        whitelist=whitelist_entries,
        protected_paths=protected_paths,
        exempt_paths=exempt_paths,
        enabled=True,
    )
    
    logger.info(
        "IP whitelist enabled",
        whitelist_count=len(whitelist_entries),
        protected_paths=protected_paths,
    )
elif settings.ip_whitelist_enabled:
    logger.warning(
        "IP whitelist enabled but no IP addresses configured. "
        "Set IP_WHITELIST in .env to enable IP-based access control."
    )

# Add security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    exempt_paths=("/static",),
    get_extra_script_sources=_get_extra_csp_script_sources,
    get_extra_connect_sources=_get_extra_csp_script_sources,
)

# Add request logging middleware
app.add_middleware(
    RequestLoggingMiddleware,
    exempt_paths=("/static", "/health", "/healthz", "/readyz", "/manifest.webmanifest", "/service-worker.js", "/api/users/me/preferences"),
)

# Configure endpoint-specific rate limits per security requirements
_rate_limit_redis = get_redis_client()
endpoint_limiter = EndpointRateLimiter(redis_client=_rate_limit_redis)

# Login: 5 attempts per 15 minutes per IP
endpoint_limiter.add_limit("/api/auth/login", "POST", limit=5, window_seconds=900)

# Password reset: 3 requests per hour per email
def _password_reset_key(request: Request) -> str:
    """Generate rate limit key based on email from query params or IP fallback."""
    try:
        email = request.query_params.get("email")
        if email:
            return f"reset:{email.lower()}"
        # For POST requests with JSON bodies the body is consumed by FastAPI
        # before middleware runs, so fall back to the validated client IP.
        return get_client_ip(request, default="anonymous") or "anonymous"
    except Exception:
        return get_client_ip(request, default="anonymous") or "anonymous"

endpoint_limiter.add_limit(
    "/api/auth/password/forgot",
    "POST",
    limit=3,
    window_seconds=3600,
    key_func=_password_reset_key,
)
endpoint_limiter.add_limit(
    "/auth/password/forgot",
    "POST",
    limit=3,
    window_seconds=3600,
    key_func=_password_reset_key,
)

# File upload: 10 files per hour per user
def _user_upload_key(request: Request) -> str:
    """Generate rate limit key based on validated client IP."""
    ip = get_client_ip(request, default="anonymous") or "anonymous"
    return f"upload:{ip}"

# Apply to common upload endpoints
upload_paths = [
    "/api/tickets/attachments",
    "/api/business-continuity/attachments",
]
for path in upload_paths:
    endpoint_limiter.add_limit(
        path, "POST", limit=10, window_seconds=3600, key_func=_user_upload_key
    )

# General HTTP traffic: per authenticated browser session, with IP fallback for
# unauthenticated requests. Keying authenticated traffic by IP caused busy NATs,
# office networks, and reverse proxies to share a single bucket across many users.
def _general_rate_limit_key(request: Request) -> str:
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        digest = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
        return f"session:{digest}"
    ip = get_client_ip(request, default="anonymous") or "anonymous"
    return f"ip:{ip}"


app.add_middleware(
    EndpointRateLimiterMiddleware,
    endpoint_limiter=endpoint_limiter,
    exempt_paths=(SWAGGER_UI_PATH, PROTECTED_OPENAPI_PATH, "/static"),
)

general_rate_limiter = SimpleRateLimiter(
    limit=settings.general_rate_limit,
    window_seconds=settings.general_rate_limit_window_seconds,
    redis_client=_rate_limit_redis,
    namespace="rate-limit:general",
)
app.add_middleware(
    RateLimiterMiddleware,
    rate_limiter=general_rate_limiter,
    exempt_paths=(
        SWAGGER_UI_PATH,
        PROTECTED_OPENAPI_PATH,
        "/static",
        "/uploads",
        "/health",
        "/healthz",
        "/readyz",
    ),
    key_func=_general_rate_limit_key,
)

app.add_middleware(
    CacheControlMiddleware,
    exempt_paths=("/static",),
)

app.add_middleware(
    CSRFMiddleware,
    exempt_paths=(
        "/api/webhooks/smtp2go",
        "/api/integration-modules/trello/webhook",
        # Public Wait For Webhook callbacks authenticate with an unguessable
        # webhook URL plus the per-step post key in the JSON payload, not a
        # browser session. Requiring CSRF here blocks legitimate automation.
        "/api/staff/workflow-webhooks",
    ),
)


templates = Jinja2Templates(directory=str(templates_config.template_path))


def _static_url(path: str) -> str:
    """Generate cache-busted URL for static files.
    
    Appends version query string to force browsers (especially Edge) to fetch
    new versions when files change, preventing stale cached content.
    """
    if _APP_VERSION:
        separator = "&" if "?" in path else "?"
        return f"{path}{separator}v={_APP_VERSION}"
    return path


# Add cache-busting helper to Jinja2 globals
templates.env.globals["static_url"] = _static_url

# Ensure document uploads remain web-accessible using the same paths as the
# previous portal stack.  Product images continue to live in the
# private ``/uploads`` directory which requires authentication before access.
_uploads_path = templates_config.static_path / "uploads"
_uploads_path.mkdir(parents=True, exist_ok=True)

_private_uploads_path = Path(__file__).resolve().parent.parent / "private_uploads"
_private_uploads_path.mkdir(parents=True, exist_ok=True)
try:
    _private_uploads_path.chmod(0o700)
except OSError:
    # The filesystem may not support chmod (e.g. on Windows).  Continue with
    # the secure default provided by ``mkdir``.
    pass


def _sanitize_upload_path(file_path: str) -> PurePosixPath:
    """Normalise an upload path and guard against traversal attacks."""

    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    normalised = file_path.replace("\\", "/")
    raw_path = PurePosixPath(normalised)

    if raw_path.is_absolute():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    sanitized_parts: list[str] = []
    for segment in raw_path.parts:
        if segment in {"", "."}:
            continue
        if segment == "..":
            if sanitized_parts:
                sanitized_parts.pop()
            continue
        sanitized_parts.append(segment)
    if not sanitized_parts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return PurePosixPath(*sanitized_parts)


def _resolve_private_upload(file_path: str | PurePosixPath) -> Path:
    """Resolve ``/uploads`` paths to the secured private uploads directory.

    Supports legacy nested directory structures while preventing path traversal
    outside the uploads root.
    """

    sanitized_path = _sanitize_upload_path(file_path) if isinstance(file_path, str) else file_path

    candidate = (_private_uploads_path.joinpath(*sanitized_path.parts)).resolve()
    uploads_root = _private_uploads_path.resolve()

    try:
        candidate.relative_to(uploads_root)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return candidate


@app.get("/manifest.webmanifest", include_in_schema=False)
async def pwa_manifest() -> JSONResponse:
    """Expose the Progressive Web App manifest for installable clients."""

    manifest = {
        "name": settings.app_name,
        "short_name": settings.app_name[:30],
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "background_color": PWA_BACKGROUND_COLOR,
        "theme_color": PWA_THEME_COLOR,
        "description": f"{settings.app_name} portal with offline support.",
        "lang": "en",
        "dir": "ltr",
        "icons": _PWA_ICON_SOURCES,
        "shortcuts": [
            {
                "name": "Dashboard",
                "url": "/",
                "icons": [_PWA_ICON_SOURCES[0]],
            }
        ],
        "categories": ["productivity", "business"],
    }
    response = JSONResponse(manifest, media_type="application/manifest+json")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.get("/service-worker.js", include_in_schema=False)
async def pwa_service_worker() -> FileResponse:
    """Serve the static service worker with strict caching headers."""

    if not _PWA_SERVICE_WORKER_PATH.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    response = FileResponse(
        _PWA_SERVICE_WORKER_PATH,
        media_type="application/javascript",
        filename="service-worker.js",
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


app.mount("/static", StaticFiles(directory=str(templates_config.static_path)), name="static")


@app.websocket("/ws/refresh")
async def refresh_updates(websocket: WebSocket) -> None:
    """Maintain a websocket connection for realtime refresh notifications."""

    await refresh_notifier.connect(websocket)
    try:
        while True:
            # Keep the connection open and consume incoming messages so we
            # detect client disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await refresh_notifier.disconnect(websocket)


# MCP WebSocket endpoint (only enabled if MCP_ENABLED is true)
if settings.mcp_enabled:
    from app.mcp_server import handle_mcp_connection

    @app.websocket("/mcp/ws")
    async def mcp_websocket_endpoint(websocket: WebSocket) -> None:
        """Model Context Protocol WebSocket endpoint for authorized agent access."""
        await handle_mcp_connection(websocket)


@app.get(PROTECTED_OPENAPI_PATH, include_in_schema=False)
async def authenticated_openapi_schema(
    _: SessionData = Depends(get_current_session),
) -> JSONResponse:
    """Return the OpenAPI schema for authenticated users only."""

    return JSONResponse(app.openapi())


@app.get(SWAGGER_UI_PATH, include_in_schema=False)
async def authenticated_swagger_ui(request: Request) -> Response:
    """Render the Swagger UI after verifying the user session."""

    session = await session_manager.load_session(request)
    if not session:
        next_target = quote(SWAGGER_UI_PATH, safe="/")
        login_url = f"/login?next={next_target}"
        redirect = RedirectResponse(url=login_url, status_code=status.HTTP_303_SEE_OTHER)
        return redirect

    return get_swagger_ui_html(
        openapi_url=PROTECTED_OPENAPI_PATH,
        title=f"{settings.app_name} API Docs",
        oauth2_redirect_url=None,
        swagger_js_url="/static/js/swagger-ui-bundle.js",
        swagger_css_url="/static/css/swagger-ui.css",
        swagger_favicon_url="/static/favicon.svg",
    )

app.include_router(auth.router)
app.include_router(ai_tag_synonyms.router)
app.include_router(dashboard_api.router)
app.include_router(users.router)
app.include_router(companies.router)
app.include_router(essential8_api.router)
app.include_router(compliance_checks_api.router)
app.include_router(licenses_api.router)
app.include_router(knowledge_base_api.router)
app.include_router(bc_plans_api.router)
app.include_router(bc5.router)
app.include_router(bc11.router)
app.include_router(bcp.router)
app.include_router(roles.router)
app.include_router(memberships.router)
app.include_router(message_templates_api.router)
app.include_router(ports.router)
app.include_router(notifications.router)
app.include_router(staff_api.router)
app.include_router(issues_api.router)
app.include_router(audit_logs.router)
app.include_router(api_keys.router)
app.include_router(scheduler_api.router)
app.include_router(tickets_api.router)
app.include_router(email_blocklist_api.router)
app.include_router(automations_api.router)
app.include_router(modules_api.router)
app.include_router(system.router)
app.include_router(service_status_api.router)
app.include_router(asset_custom_fields.router)
app.include_router(tag_exclusions.router)
app.include_router(features_api.router)
app.include_router(plugins_api.router)

# Initialise the feature pack registry.  Packs are loaded lazily on
# startup (see ``on_startup`` below).  The registry remains empty until
# packs are migrated into ``app/features/`` in follow-up PRs.
feature_registry = init_registry(app)

HELPDESK_PERMISSION_KEY = tickets_service.HELPDESK_PERMISSION_KEY
ISSUE_TRACKER_PERMISSION_KEY = issues_service.ISSUE_TRACKER_PERMISSION_KEY
MARKETING_PERMISSION_KEY = "marketing.access"

# Search configuration
_PHONE_SEARCH_LIMIT = 100


TOTP_ENROLLMENT_PAGE_PATH = "/security/2fa"
TOTP_ENROLLMENT_ALLOWED_PAGE_PATHS = frozenset(
    {
        TOTP_ENROLLMENT_PAGE_PATH,
    }
)


async def _user_requires_totp_enrollment(user: Mapping[str, Any]) -> bool:
    user_id = user.get("id")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return True
    return not await auth_repo.user_has_totp_authenticator(user_id_int)


async def _require_authenticated_user(request: Request) -> tuple[dict[str, Any] | None, RedirectResponse | None]:
    session = await session_manager.load_session(request)
    if not session:
        return None, RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = await user_repo.get_user_by_id(session.user_id)
    if not user:
        return None, RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if (
        request.url.path not in TOTP_ENROLLMENT_ALLOWED_PAGE_PATHS
        and await _user_requires_totp_enrollment(user)
    ):
        return None, RedirectResponse(url=TOTP_ENROLLMENT_PAGE_PATH, status_code=status.HTTP_303_SEE_OTHER)
    active_company_id = session.active_company_id
    if active_company_id is None:
        active_company_id = await _resolve_initial_company_id(user)
        if active_company_id is not None:
            await session_manager.set_active_company(session, active_company_id)
    if active_company_id is not None:
        user["company_id"] = active_company_id
    request.state.active_company_id = active_company_id
    return user, None


async def _require_super_admin_page(request: Request) -> tuple[dict[str, Any] | None, RedirectResponse | None]:
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return None, redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    return user, None


async def _is_helpdesk_technician(user: Mapping[str, Any], request: Request | None = None) -> bool:
    if user.get("is_super_admin"):
        if request is not None:
            request.state.is_helpdesk_technician = True
        return True
    if request is not None:
        cached = getattr(request.state, "is_helpdesk_technician", None)
        if cached is not None:
            return bool(cached)
    user_id = user.get("id")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        result = False
    else:
        try:
            result = await membership_repo.user_has_permission(
                user_id_int, HELPDESK_PERMISSION_KEY
            )
            if not result:
                result = await membership_repo.user_has_permission(
                    user_id_int, "helpdesk.technician"
                )
        except Exception as exc:  # pragma: no cover - defensive fallback for tests without DB
            log_error("Failed to determine helpdesk technician role", error=str(exc))
            result = False
    if request is not None:
        request.state.is_helpdesk_technician = bool(result)
    return bool(result)


async def _has_admin_technician_access(user: Mapping[str, Any], request: Request | None = None) -> bool:
    """Return whether the user may access technician-only admin ticket pages.

    ``menu.tickets`` write access allows a company user to see all tickets for
    their company in the portal. It intentionally maps to the legacy
    ``helpdesk.technician`` permission for older ticket workflows, so it must
    not be used as the gate for ``/admin/tickets``. The admin ticket workspace
    is reserved for super administrators and roles with the explicit
    ``menu.admin.technician``/``company.switch_all`` technician switch access.
    """
    if user.get("is_super_admin"):
        if request is not None:
            request.state.has_admin_technician_access = True
        return True
    if request is not None:
        cached = getattr(request.state, "has_admin_technician_access", None)
        if cached is not None:
            return bool(cached)
    user_id = user.get("id")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        result = False
    else:
        try:
            result = await membership_repo.user_has_permission(
                user_id_int, "company.switch_all"
            )
        except Exception as exc:  # pragma: no cover - defensive fallback for tests without DB
            log_error("Failed to determine admin technician access", error=str(exc))
            result = False
    if request is not None:
        request.state.has_admin_technician_access = bool(result)
    return bool(result)


async def _has_issue_tracker_access(user: Mapping[str, Any], request: Request | None = None) -> bool:
    if user.get("is_super_admin"):
        if request is not None:
            request.state.has_issue_tracker_access = True
        return True
    if request is not None:
        cached = getattr(request.state, "has_issue_tracker_access", None)
        if cached is not None:
            return bool(cached)
    user_id = user.get("id")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        result = False
    else:
        try:
            result = await membership_repo.user_has_permission(
                user_id_int, ISSUE_TRACKER_PERMISSION_KEY
            )
        except Exception as exc:  # pragma: no cover - defensive fallback for tests without DB
            log_error("Failed to determine issue tracker access", error=str(exc))
            result = False
        if not result:
            try:
                assignments = await user_company_repo.list_companies_for_user(user_id_int)
            except Exception as exc:  # pragma: no cover - defensive fallback for tests without DB
                log_error(
                    "Failed to evaluate direct issue tracker access",
                    error=str(exc),
                )
                assignments = []
            result = any(bool(assignment.get("can_manage_issues")) for assignment in assignments)
    if request is not None:
        request.state.has_issue_tracker_access = bool(result)
    return bool(result)


async def _has_marketing_access(user: Mapping[str, Any], request: Request | None = None) -> bool:
    if user.get("is_super_admin"):
        if request is not None:
            request.state.has_marketing_access = True
        return True
    if request is not None:
        cached = getattr(request.state, "has_marketing_access", None)
        if cached is not None:
            return bool(cached)
    user_id = user.get("id")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        result = False
    else:
        try:
            result = await membership_repo.user_has_permission(
                user_id_int, MARKETING_PERMISSION_KEY
            )
        except Exception as exc:  # pragma: no cover - defensive fallback for tests without DB
            log_error("Failed to determine marketing access", error=str(exc))
            result = False
    if request is not None:
        request.state.has_marketing_access = bool(result)
    return bool(result)


async def _require_helpdesk_page(request: Request) -> tuple[dict[str, Any] | None, RedirectResponse | None]:
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return None, redirect
    if not await _has_admin_technician_access(user, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return user, None


async def _require_issue_tracker_access(
    request: Request,
) -> tuple[dict[str, Any] | None, RedirectResponse | None]:
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return None, redirect
    has_access = await _has_issue_tracker_access(user, request)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Issue tracker access required",
        )
    return user, None


async def _require_administration_access(
    request: Request,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, RedirectResponse | None]:
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return None, None, redirect

    membership = getattr(request.state, "active_membership", None)
    if membership is None:
        active_company_id = getattr(request.state, "active_company_id", None)
        if active_company_id is not None:
            try:
                membership = await user_company_repo.get_user_company(user["id"], int(active_company_id))
            except Exception:  # pragma: no cover - defensive protection against membership lookup failures
                membership = None
            request.state.active_membership = membership

    is_company_admin = bool(membership and membership.get("is_admin"))
    if not (user.get("is_super_admin") or is_company_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    return user, membership, None


@app.get("/uploads/{file_path:path}", response_class=FileResponse, include_in_schema=False)
async def serve_private_upload(file_path: str, request: Request):
    """Serve product images stored in the legacy private uploads directory."""

    sanitized_path = _sanitize_upload_path(file_path)
    is_public_kb_image = sanitized_path.parts and sanitized_path.parts[0] == "knowledge-base"

    if not is_public_kb_image:
        _, redirect = await _require_authenticated_user(request)
        if redirect:
            return redirect

    resolved_path = _resolve_private_upload(sanitized_path)
    headers = {"Cache-Control": "public, max-age=86400"}
    return FileResponse(resolved_path, headers=headers)


def _to_iso(dt: Any) -> str | None:
    if not dt:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    return str(dt)


def _serialise_for_json(value: Any) -> Any:
    if isinstance(value, datetime):
        return _to_iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return float(value)
    if isinstance(value, Mapping):
        return {key: _serialise_for_json(item) for key, item in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialise_for_json(item) for item in value]
    return value


_NOTIFICATION_METADATA_HIDDEN_KEYS: frozenset[str] = frozenset({"staff_id"})


def _prepare_notification_metadata(metadata: Any) -> list[dict[str, str]]:
    if metadata is None:
        return []

    serialised = _serialise_for_json(metadata)

    if isinstance(serialised, Mapping):
        items: list[dict[str, str]] = []
        for key in sorted(serialised.keys(), key=lambda item: str(item)):
            if str(key) in _NOTIFICATION_METADATA_HIDDEN_KEYS:
                continue
            value = serialised[key]
            if isinstance(value, Mapping) or (
                isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray))
            ):
                value_text = json.dumps(value, ensure_ascii=False)
            else:
                value_text = "" if value is None else str(value)
            items.append({"key": str(key), "value": value_text})
        return items

    if isinstance(serialised, Iterable) and not isinstance(serialised, (str, bytes, bytearray)):
        value_text = json.dumps(serialised, ensure_ascii=False)
        return [{"key": "items", "value": value_text}]

    return [{"key": "value", "value": "" if serialised is None else str(serialised)}]


def _serialise_mapping(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _serialise_for_json(value) for key, value in record.items()}


def _parse_input_date(value: str | None) -> date | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_input_datetime(value: str | None, *, assume_midnight: bool = False) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if assume_midnight and "T" not in text and " " not in text:
        parsed = datetime.combine(parsed.date(), time.min)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def _resolve_timezone(value: str | None) -> tuple[ZoneInfo | None, str | None]:
    zone_name = str(value or "").strip()
    if not zone_name:
        return None, None
    try:
        return ZoneInfo(zone_name), zone_name
    except ZoneInfoNotFoundError:
        return None, None


def _raw_value_includes_time(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return bool(re.search(r"\d{1,2}:\d{2}", text))


def _parse_local_datetime_to_utc(
    value: str | None,
    *,
    timezone_name: str | None = None,
    assume_midnight: bool = False,
) -> datetime | None:
    parsed = _parse_input_datetime(value, assume_midnight=assume_midnight)
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc)
    local_zone, _normalized_timezone = _resolve_timezone(timezone_name)
    if local_zone is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.replace(tzinfo=local_zone).astimezone(timezone.utc)


def _parse_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return default
    return text in {"1", "true", "t", "yes", "y", "on"}


def _parse_int_in_range(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def _validate_subscription_commitment_and_payment(
    subscription_category_id: int | None,
    commitment_type: str | None,
    payment_frequency: str | None,
) -> tuple[str | None, str | None]:
    """Validate subscription commitment type and payment frequency.
    
    Returns:
        Tuple of (commitment_value, payment_frequency_value)
        
    Raises:
        HTTPException: If validation fails
    """
    if not subscription_category_id:
        return None, None
        
    if not commitment_type or commitment_type not in ("monthly", "annual"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Commitment type must be 'monthly' or 'annual' for subscription products"
        )
    
    if not payment_frequency or payment_frequency not in ("monthly", "annual"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment frequency must be 'monthly' or 'annual' for subscription products"
        )
    
    # Validate business rule: Monthly commitment can only have monthly payment
    if commitment_type == "monthly" and payment_frequency != "monthly":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Monthly commitment can only have monthly payment"
        )
    
    return commitment_type, payment_frequency


def _parse_staff_selection(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith("staff:"):
        candidate = text.split(":", 1)[1].strip()
    elif lowered.startswith("s-"):
        candidate = text[2:].strip()
    else:
        return None
    try:
        return int(candidate)
    except ValueError:
        return None


def _request_prefers_json(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept:
        return True
    requested_with = (request.headers.get("x-requested-with") or "").lower()
    if requested_with == "xmlhttprequest":
        return True
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        return True
    return False


def _request_accepts_html(request: Request) -> bool:
    if _request_prefers_json(request):
        return False
    accept = (request.headers.get("accept") or "*").lower()
    if "text/html" in accept or "application/xhtml+xml" in accept:
        return True
    return "*/*" in accept or accept == "*"


def _get_status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"


def _get_request_id(request: Request) -> str | None:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id.strip():
        return request_id
    header_request_id = request.headers.get("x-request-id")
    if header_request_id and header_request_id.strip():
        return header_request_id.strip()
    return None


def _error_payload(*, detail: str, request_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"detail": detail}
    if request_id:
        payload["request_id"] = request_id
        payload["error_reference"] = request_id
    return payload


def _apply_request_id_header(response: Response, request_id: str | None) -> Response:
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def _format_error_detail(detail: Any) -> str | None:
    if detail is None:
        return None
    if isinstance(detail, str):
        return detail
    try:
        return json.dumps(detail, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(detail)


def _generate_error_reference() -> str:
    return uuid4().hex[:12]


def _get_safe_error_path(request: Request) -> str:
    path = request.url.path.strip()
    return path or "/"


def _should_show_error_detail(*, request: Request, user: dict[str, Any] | None) -> bool:
    if bool(getattr(request.app, "debug", False)):
        return True
    if settings.environment.strip().lower() != "production":
        return True
    return bool(user and user.get("is_super_admin"))


async def _render_error_page(
    request: Request,
    *,
    status_code: int,
    title: str | None = None,
    message: str,
    detail: str | None = None,
    error_reference: str | None = None,
) -> HTMLResponse:
    status_message = _get_status_phrase(status_code)
    document_title = title or f"{status_code} {status_message}"
    request_id = _get_request_id(request)
    resolved_error_reference = error_reference or _generate_error_reference()
    try:
        user, _ = await _get_optional_user(request)
    except Exception as exc:  # pragma: no cover - defensive fallback
        log_error(
            "Failed to load user context for error page",
            error=str(exc),
            request_id=request_id,
            error_reference=resolved_error_reference,
            request_path=_get_safe_error_path(request),
        )
        user = None
    show_error_detail = _should_show_error_detail(request=request, user=user)
    context = await _build_portal_context(
        request,
        user,
        extra={
            "title": document_title,
            "error_title": title or status_message,
            "error_message": message,
            "error_status_code": status_code,
            "error_status_message": status_message,
            "error_detail": detail if show_error_detail else None,
            "show_error_detail": show_error_detail,
            "error_path": _get_safe_error_path(request),
            "request_id": request_id,
            "error_reference": resolved_error_reference,
        },
    )
    return templates.TemplateResponse(
        context["request"],
        "errors/error.html",
        context,
        status_code=status_code,
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    path = request.url.path
    request_id = _get_request_id(request)
    if path.startswith("/api/integration-modules/"):
        logger.warning(
            "Webhook payload validation failed",
            request_id=request_id,
            path=path,
            errors=exc.errors(),
            content_type=request.headers.get("content-type"),
            user_agent=request.headers.get("user-agent"),
        )
    response = JSONResponse(
        content=jsonable_encoder({"detail": exc.errors()}),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
    return _apply_request_id_header(response, request_id)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    request_id = _get_request_id(request)
    error_reference = _generate_error_reference()
    if _request_prefers_json(request) or not _request_accepts_html(request):
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            response = JSONResponse(
                _error_payload(detail="Internal server error", request_id=request_id),
                status_code=exc.status_code,
            )
            if exc.headers:
                for header, value in exc.headers.items():
                    response.headers[header] = value
            return _apply_request_id_header(response, request_id)
        response = await http_exception_handler(request, exc)
        return _apply_request_id_header(response, request_id)
    detail_text = _format_error_detail(exc.detail)
    friendly_titles = {
        status.HTTP_404_NOT_FOUND: "Page not found",
        status.HTTP_403_FORBIDDEN: "Access denied",
        status.HTTP_401_UNAUTHORIZED: "Sign in required",
    }
    friendly_messages = {
        status.HTTP_404_NOT_FOUND: "We couldn't find the page you were looking for. Use the navigation menu to continue.",
        status.HTTP_403_FORBIDDEN: "You don't have permission to view this page. Choose another destination from the menu.",
        status.HTTP_401_UNAUTHORIZED: "Please sign in to continue. You can return to the dashboard to start again.",
    }
    message = friendly_messages.get(exc.status_code) or detail_text or _get_status_phrase(exc.status_code)
    detail_for_template = None
    if detail_text and detail_text != message:
        detail_for_template = detail_text
    log_info(
        "Rendering HTTP error page",
        status_code=exc.status_code,
        request_id=request_id,
        error_reference=error_reference,
        request_path=_get_safe_error_path(request),
    )
    response = await _render_error_page(
        request,
        status_code=exc.status_code,
        title=friendly_titles.get(exc.status_code),
        message=message,
        detail=detail_for_template,
        error_reference=error_reference,
    )
    if exc.headers:
        for header, value in exc.headers.items():
            response.headers[header] = value
    return _apply_request_id_header(response, request_id)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):  # pragma: no cover - defensive
    request_id = _get_request_id(request)
    error_reference = _generate_error_reference()
    log_error(
        "Unhandled application error",
        exc=exc,
        event="app.unhandled_exception",
        request_id=request_id,
        error_reference=error_reference,
        path=_get_safe_error_path(request),
    )
    if _request_prefers_json(request):
        response = JSONResponse(
            _error_payload(detail="Internal server error", request_id=request_id),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return _apply_request_id_header(response, request_id)
    if not _request_accepts_html(request):
        response = PlainTextResponse("Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return _apply_request_id_header(response, request_id)
    response = await _render_error_page(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Something went wrong",
        message="We ran into a problem while loading this page. Try again, or pick another destination from the menu.",
        detail=_format_error_detail(exc),
        error_reference=error_reference,
    )
    return _apply_request_id_header(response, request_id)


async def _resolve_initial_company_id(user: dict[str, Any]) -> int | None:
    return await company_access.first_accessible_company_id(user)




def _menu_permission_is_explicit_no_access(raw: Any, key: str) -> bool:
    """Return whether a menu permission payload explicitly denies a menu key."""
    if isinstance(raw, dict):
        source = raw.get("menu") if isinstance(raw.get("menu"), dict) else raw
        if key in source:
            return normalize_access_level(source.get(key)) == "none"
    return False


def _build_menu_access_map(
    *,
    is_super_admin: bool,
    membership_data: dict[str, Any],
    is_helpdesk_technician: bool = False,
    has_issue_tracker_access: bool = False,
    has_marketing_access: bool = False,
) -> dict[str, str]:
    if is_super_admin:
        return {item.key: "write" for item in MENU_PERMISSIONS}

    raw_menu_permissions = membership_data.get("menu_permissions")
    role_menu_permissions = normalize_menu_permissions(raw_menu_permissions)
    menu_access = {item.key: role_menu_permissions.get(item.key, "none") for item in MENU_PERMISSIONS}
    explicitly_denied_menu_keys = {
        item.key
        for item in MENU_PERMISSIONS
        if _menu_permission_is_explicit_no_access(raw_menu_permissions, item.key)
    }
    for key in explicitly_denied_menu_keys:
        menu_access[key] = "none"

    def promote(key: str, level: str = "write") -> None:
        if key in explicitly_denied_menu_keys:
            return
        rank = {"none": 0, "read": 1, "write": 2}
        if rank[level] > rank[menu_access.get(key, "none")]:
            menu_access[key] = level

    # Baseline authenticated pages remain readable unless explicitly controlled by a role.
    for key in ("menu.dashboard", "menu.service_status", "menu.knowledge_base", "menu.admin.profile"):
        promote(key, "read")

    legacy_boolean_to_menu = {
        "can_access_shop": "menu.shop",
        "can_access_cart": "menu.shop",
        "can_access_orders": "menu.orders",
        "can_access_quotes": "menu.quotes",
        "can_access_forms": "menu.forms",
        "can_manage_assets": "menu.assets",
        "can_manage_licenses": "menu.m365.licenses",
        "can_manage_invoices": "menu.invoices",
        "can_manage_staff": "menu.staff",
        "can_view_compliance": "menu.compliance",
        "can_view_bcp": "menu.continuity",
        "can_view_m365_best_practices": "menu.m365.best_practices",
        "can_view_compliance_checks": "menu.compliance_checks",
        "can_manage_compliance_checks": "menu.compliance_checks.library",
        "can_view_m365_user_mailboxes": "menu.m365.user_mailboxes",
        "can_view_m365_shared_mailboxes": "menu.m365.shared_mailboxes",
        "can_access_chat": "menu.chat",
        "is_admin": "menu.admin.company",
    }
    for boolean_key, menu_key in legacy_boolean_to_menu.items():
        if membership_data.get(boolean_key):
            promote(menu_key, "write" if boolean_key.startswith("can_manage") or boolean_key == "is_admin" else "read")

    if membership_data.get("can_manage_licenses"):
        promote("menu.m365.configuration", "write")
    if membership_data.get("can_manage_licenses") and membership_data.get("can_access_cart"):
        promote("menu.subscriptions", "write")
    if is_helpdesk_technician:
        promote("menu.reporting", "write")
    if has_issue_tracker_access:
        promote("menu.issues", "write")
    if has_marketing_access:
        promote("menu.marketing", "write")
    if int(membership_data.get("staff_permission") or 0) > 0:
        promote("menu.staff", "write")
    else:
        # Staff role permissions control what a member may do, but the company
        # membership scope controls whether they may see any staff at all.
        # Never let a role's Read/Write setting grant staff access when the
        # member has neither Department nor All staff access.
        menu_access["menu.staff"] = "none"

    return menu_access


def _menu_can(menu_access: dict[str, Any] | None, key: str, *, write: bool = False) -> bool:
    return menu_has_access(menu_access, key, write=write)


def _can_edit_profile_technician_tools(user: Mapping[str, Any], membership: Mapping[str, Any] | None) -> bool:
    """Return whether technician-only self-profile fields should be visible.

    ``_is_helpdesk_technician`` intentionally treats some ticket access as
    technician-like for broad ticket routing.  The profile-only contact tools
    are narrower: they should be visible only to super admins and users whose
    active membership has full technician ticket access.
    """
    if user.get("is_super_admin"):
        return True
    if not membership:
        return False
    profile_permissions = normalize_menu_permissions(
        membership.get("menu_permissions") or membership.get("permissions")
    )
    return _menu_can(profile_permissions, "menu.tickets", write=True)


async def _has_menu_page_access(request: Request, user: Mapping[str, Any], key: str, *, write: bool = False) -> bool:
    """Return whether the authenticated user has explicit access to a menu-owned page.

    Super administrators keep unrestricted access. Other users must have the
    requested menu permission on their active company membership; baseline
    authenticated menu items are intentionally not elevated here.
    """
    if user.get("is_super_admin"):
        return True

    membership = getattr(request.state, "active_membership", None)
    active_company_id = getattr(request.state, "active_company_id", None) or user.get("company_id")
    if membership is None and active_company_id is not None:
        try:
            membership = await user_company_repo.get_user_company(int(user["id"]), int(active_company_id))
        except (TypeError, ValueError):
            membership = None
        except Exception as exc:  # pragma: no cover - defensive fallback for tests without DB
            log_error("Failed to load active membership for menu access", error=str(exc))
            membership = None
        if membership is not None:
            request.state.active_membership = membership

    membership_data = membership or {}
    is_helpdesk_technician = await _is_helpdesk_technician(user, request)
    has_issue_tracker_access = await _has_issue_tracker_access(user, request)
    has_marketing_access = await _has_marketing_access(user, request)
    menu_access = _build_menu_access_map(
        is_super_admin=False,
        membership_data=membership_data,
        is_helpdesk_technician=is_helpdesk_technician,
        has_issue_tracker_access=has_issue_tracker_access,
        has_marketing_access=has_marketing_access,
    )
    return _menu_can(menu_access, key, write=write)


async def _require_menu_page_access(
    request: Request,
    key: str,
    *,
    write: bool = False,
    detail: str = "Page access permission required",
) -> tuple[dict[str, Any] | None, RedirectResponse | None]:
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return None, redirect
    if not await _has_menu_page_access(request, user, key, write=write):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return user, None

def _membership_menu_can(user: dict[str, Any], membership: dict[str, Any] | None, key: str, *, write: bool = False) -> bool:
    if user.get("is_super_admin"):
        return True
    menu_access = _build_menu_access_map(
        is_super_admin=False,
        membership_data=membership or {},
    )
    return _menu_can(menu_access, key, write=write)


def _build_plausible_config(
    module_lookup: Mapping[str, Mapping[str, Any]],
    user: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a template-safe Plausible configuration.

    The disabled shape is deliberately complete so every page extending the
    base template can render even when modules have not loaded yet.
    """
    disabled: dict[str, Any] = {
        "enabled": False,
        "base_url": "",
        "site_domain": "",
        "track_pageviews": False,
    }
    plausible_module = module_lookup.get("plausible")
    if not plausible_module or not plausible_module.get("enabled"):
        return disabled

    plausible_settings = plausible_module.get("settings") or {}
    base_url = str(plausible_settings.get("base_url") or "").strip().rstrip("/")
    site_domain = str(plausible_settings.get("site_domain") or "").strip()
    parsed_url = urlparse(base_url)
    valid_base_url = (
        parsed_url.scheme in {"http", "https"}
        and bool(parsed_url.netloc)
        and parsed_url.username is None
        and parsed_url.password is None
        and not any(character in base_url for character in "<>\"'")
    )
    valid_site_domain = bool(re.fullmatch(r"[A-Za-z0-9._-]+(?::\d+)?", site_domain))
    if not valid_base_url or not valid_site_domain:
        return disabled

    config: dict[str, Any] = {
        "enabled": True,
        "base_url": base_url,
        "site_domain": site_domain,
        "track_pageviews": bool(plausible_settings.get("track_pageviews")),
    }
    if config["track_pageviews"] and user and user.get("id"):
        from app.security.plausible_tracking import hash_user_id_for_plausible

        config["hashed_user_id"] = hash_user_id_for_plausible(
            int(user["id"]),
            str(plausible_settings.get("pepper") or "").strip(),
            bool(plausible_settings.get("send_pii")),
        )
    return config


def _build_module_lookup(module_list: Iterable[Any]) -> dict[str, Mapping[str, Any]]:
    """Index valid integration-module records without trusting database data.

    A malformed ``slug`` value (for example a decoded JSON object) is not
    hashable and previously caused every page using the shared template
    context to fail with ``TypeError: unhashable type: 'dict'``.  Ignore
    malformed records here so one damaged integration row cannot take down
    otherwise unrelated pages.
    """

    module_lookup: dict[str, Mapping[str, Any]] = {}
    for module in module_list:
        if not isinstance(module, Mapping):
            log_error(
                "Ignoring malformed integration module record",
                record_type=type(module).__name__,
            )
            continue
        slug = module.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            log_error(
                "Ignoring integration module with invalid slug",
                slug_type=type(slug).__name__,
            )
            continue
        module_lookup[slug] = module
    return module_lookup


async def _build_base_context(
    request: Request,
    user: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = await session_manager.load_session(request)
    impersonator_user = None
    impersonation_started_at = None
    is_impersonating = False
    if session and session.impersonator_user_id is not None:
        is_impersonating = True
        impersonation_started_at = session.impersonation_started_at
        cached_impersonator = getattr(request.state, "impersonator_profile", None)
        if cached_impersonator and int(cached_impersonator.get("id", 0)) == session.impersonator_user_id:
            impersonator_user = cached_impersonator
        else:
            try:
                impersonator_user = await user_repo.get_user_by_id(session.impersonator_user_id)
            except Exception as exc:  # pragma: no cover - defensive logging
                log_error("Failed to load impersonator user context", error=str(exc))
                impersonator_user = None
            else:
                request.state.impersonator_profile = impersonator_user
    available_companies = getattr(request.state, "available_companies", None)
    if available_companies is None:
        available_companies = await company_access.list_accessible_companies(user)
        request.state.available_companies = available_companies
    active_company_id = getattr(request.state, "active_company_id", None)
    if active_company_id is None and session:
        active_company_id = session.active_company_id
        request.state.active_company_id = active_company_id
    active_company = None
    for company in available_companies:
        if company.get("company_id") == active_company_id:
            active_company = company
            break
    membership = None
    if active_company_id is not None:
        membership = await user_company_repo.get_user_company(user["id"], int(active_company_id))
        request.state.active_membership = membership

    membership_data = membership or {}
    is_super_admin = bool(user.get("is_super_admin"))
    staff_permission_level = int(membership_data.get("staff_permission") or 0)
    is_helpdesk_technician = await _is_helpdesk_technician(user, request)
    has_admin_technician_access = await _has_admin_technician_access(user, request)
    has_issue_tracker_access = await _has_issue_tracker_access(user, request)
    has_marketing_access = await _has_marketing_access(user, request)
    menu_access = _build_menu_access_map(
        is_super_admin=is_super_admin,
        membership_data=membership_data,
        is_helpdesk_technician=is_helpdesk_technician,
        has_issue_tracker_access=has_issue_tracker_access,
        has_marketing_access=has_marketing_access,
    )

    def _has_permission(flag: str) -> bool:
        return bool(membership_data.get(flag))
    
    # Check BCP permissions - use new continuity.access permission system
    can_view_bcp = is_super_admin or _has_permission("can_view_bcp")
    can_edit_bcp = is_super_admin
    if not is_super_admin and active_company_id is not None:
        user_id = user.get("id")
        if user_id:
            try:
                # Also check legacy bcp:edit permission for backward compatibility
                can_edit_bcp = await membership_repo.user_has_permission(int(user_id), "bcp:edit")
            except Exception as exc:  # pragma: no cover - defensive fallback
                log_error("Failed to check BCP edit permissions", error=str(exc))
                can_edit_bcp = False

    permission_flags = {
        "can_access_shop": _menu_can(menu_access, "menu.shop") or is_super_admin or _has_permission("can_access_shop"),
        "can_access_cart": is_super_admin or _has_permission("can_access_cart"),
        "can_access_orders": _menu_can(menu_access, "menu.orders") or is_super_admin or _has_permission("can_access_orders"),
        "can_access_quotes": _menu_can(menu_access, "menu.quotes") or is_super_admin or _has_permission("can_access_quotes"),
        "can_access_forms": _menu_can(menu_access, "menu.forms") or is_super_admin or _has_permission("can_access_forms"),
        "can_manage_assets": _menu_can(menu_access, "menu.assets", write=True) or is_super_admin or _has_permission("can_manage_assets"),
        "can_manage_licenses": _menu_can(menu_access, "menu.m365.licenses", write=True) or is_super_admin or _has_permission("can_manage_licenses"),
        "can_manage_invoices": _menu_can(menu_access, "menu.invoices", write=True) or is_super_admin or _has_permission("can_manage_invoices"),
        "can_manage_staff": (
            is_super_admin
            or (
                _menu_can(menu_access, "menu.staff")
                and (_has_permission("can_manage_staff") or staff_permission_level > 0)
            )
        ),
        "can_manage_issues": _menu_can(menu_access, "menu.issues", write=True) or has_issue_tracker_access,
        "can_view_compliance": _menu_can(menu_access, "menu.compliance") or is_super_admin or _has_permission("can_view_compliance"),
        "can_view_bcp": _menu_can(menu_access, "menu.continuity") or can_view_bcp,
        "can_edit_bcp": can_edit_bcp,
        "can_view_m365_best_practices": _menu_can(menu_access, "menu.m365.best_practices") or is_super_admin or _has_permission("can_view_m365_best_practices"),
        "can_view_compliance_checks": _menu_can(menu_access, "menu.compliance_checks") or is_super_admin or _has_permission("can_view_compliance_checks"),
        "can_manage_compliance_checks": _menu_can(menu_access, "menu.compliance_checks.library", write=True) or is_super_admin or _has_permission("can_manage_compliance_checks"),
        "can_view_m365_user_mailboxes": _menu_can(menu_access, "menu.m365.user_mailboxes") or is_super_admin or _has_permission("can_view_m365_user_mailboxes"),
        "can_view_m365_shared_mailboxes": _menu_can(menu_access, "menu.m365.shared_mailboxes") or is_super_admin or _has_permission("can_view_m365_shared_mailboxes"),
        "can_access_chat": _menu_can(menu_access, "menu.chat") or is_super_admin or _has_permission("can_access_chat"),
        "can_access_marketing": _menu_can(menu_access, "menu.marketing") or has_marketing_access,
        "can_manage_subscriptions": _menu_can(menu_access, "menu.subscriptions", write=True),
        "can_access_reports": _menu_can(menu_access, "menu.reports"),
        "can_access_reporting": _menu_can(menu_access, "menu.reporting"),
        "can_access_admin_company": _menu_can(menu_access, "menu.admin.company"),
        "menu_access": menu_access,
        "menu_permission_catalogue": catalogue_for_api(),
    }

    module_lookup = getattr(request.state, "module_lookup", None)
    if module_lookup is None:
        try:
            module_list = await modules_service.list_modules()
        except Exception as exc:  # pragma: no cover - defensive logging
            log_error("Failed to load integration modules for context", error=str(exc))
            module_list = []
        module_lookup = _build_module_lookup(module_list)
        request.state.module_lookup = module_lookup

    context: dict[str, Any] = {
        "request": request,
        "app_name": settings.app_name,
        "current_year": datetime.utcnow().year,
        "user": user,
        "current_user": user,
        "available_companies": available_companies,
        "active_company": active_company,
        "active_company_id": active_company_id,
        "active_membership": membership,
        "csrf_token": session.csrf_token if session else None,
        "staff_permission": staff_permission_level,
        "is_super_admin": is_super_admin,
        "is_helpdesk_technician": is_helpdesk_technician,
        "has_admin_technician_access": has_admin_technician_access,
        "is_company_admin": is_super_admin or _menu_can(menu_access, "menu.admin.company"),
        "integration_modules": module_lookup,
        # Normalised, read-only-by-convention feature map for templates.  Keep
        # integration_modules above for callers which need module metadata.
        "module_enabled": {
            slug: bool(module.get("enabled"))
            for slug, module in (module_lookup or {}).items()
        },
        "enabled_module_slugs": frozenset(
            slug
            for slug, module in (module_lookup or {}).items()
            if bool(module.get("enabled"))
        ),
        "plausible_config": _build_plausible_config(module_lookup or {}, user),
        "enable_auto_refresh": bool(settings.enable_auto_refresh),
        "is_impersonating": is_impersonating,
        "impersonator_user": impersonator_user,
        "impersonation_started_at": impersonation_started_at,
        "has_issue_tracker_access": has_issue_tracker_access,
        "can_access_tickets": _menu_can(menu_access, "menu.tickets"),
        "can_access_all_tickets": _menu_can(menu_access, "menu.tickets", write=True),
    }
    context.update(permission_flags)
    if extra:
        context.update(extra)

    if "notification_unread_count" not in context:
        unread_count = 0
        user_id = user.get("id")
        if user_id is not None:
            try:
                unread_count = await notifications_repo.count_notifications(
                    user_id=int(user_id),
                    read_state="unread",
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                log_error("Failed to count unread notifications", error=str(exc))
        context["notification_unread_count"] = unread_count
    return context


async def _build_public_context(
    request: Request,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "request": request,
        "app_name": settings.app_name,
        "current_year": datetime.utcnow().year,
        "user": None,
        "current_user": None,
        "available_companies": [],
        "active_company": None,
        "active_company_id": None,
        "active_membership": None,
        "csrf_token": None,
        "staff_permission": 0,
        "is_super_admin": False,
        "is_helpdesk_technician": False,
        "is_company_admin": False,
        "can_access_shop": False,
        "can_access_cart": False,
        "can_access_orders": False,
        "can_access_quotes": False,
        "can_access_forms": False,
        "can_manage_assets": False,
        "can_manage_licenses": False,
        "can_manage_invoices": False,
        "can_manage_staff": False,
        "can_view_compliance": False,
        "can_view_m365_best_practices": False,
        "can_view_compliance_checks": False,
        "can_manage_compliance_checks": False,
        "can_view_m365_user_mailboxes": False,
        "can_view_m365_shared_mailboxes": False,
        "can_access_chat": False,
        "can_access_marketing": False,
        "plausible_config": _build_plausible_config({}),
        "notification_unread_count": 0,
        "enable_auto_refresh": bool(settings.enable_auto_refresh),
        "integration_modules": {},
        "module_enabled": {},
        "enabled_module_slugs": frozenset(),
    }
    if extra:
        context.update(extra)
    return context


async def _build_portal_context(
    request: Request,
    user: dict[str, Any] | None,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if user:
        return await _build_base_context(request, user, extra=extra)
    return await _build_public_context(request, extra=extra)


async def _get_optional_user(
    request: Request,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    session = await session_manager.load_session(request)
    if not session:
        return None, None
    request.state.session = session
    user = await user_repo.get_user_by_id(session.user_id)
    if not user:
        return None, None
    request.state.active_company_id = session.active_company_id
    membership = None
    if session.active_company_id is not None:
        try:
            membership = await user_company_repo.get_user_company(user["id"], int(session.active_company_id))
        except Exception:  # pragma: no cover - defensive
            membership = None
        if membership is not None:
            request.state.active_membership = membership
    return user, membership


async def _build_consolidated_overview(
    request: Request, user: dict[str, Any]
) -> dict[str, Any]:
    """Build the home-page dashboard payload.

    Delegates to :func:`app.services.dashboard.build_dashboard`. The wrapper
    is kept so other tests/code monkey-patching this name keep working.
    """
    return await dashboard_service.build_dashboard(request, user)


async def _render_template(
    template_name: str,
    request: Request,
    user: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
):
    from app.security.flash import clear_flash, pop_flash

    context = await _build_base_context(request, user, extra=extra)
    if context.get("page_flash") is None:
        context["page_flash"] = _derive_page_flash(context, template_name=template_name)
    # Fall back to flash cookie when no context-derived flash is present.
    if context.get("page_flash") is None:
        context["page_flash"] = pop_flash(request)
    response = templates.TemplateResponse(context["request"], template_name, context)
    # Always clear the flash cookie so it is consumed exactly once.
    clear_flash(response)
    return response


_NOTIFICATION_SORT_CHOICES: list[tuple[str, str]] = [
    ("created_at", "Created date"),
    ("event_type", "Event type"),
    ("read_at", "Read date"),
]

_NOTIFICATION_ORDER_CHOICES: list[tuple[str, str]] = [
    ("desc", "Newest first"),
    ("asc", "Oldest first"),
]

_NOTIFICATION_READ_OPTIONS: list[tuple[str, str]] = [
    ("all", "All notifications"),
    ("unread", "Unread only"),
    ("read", "Read only"),
]

_NOTIFICATION_PAGE_SIZES: list[int] = [10, 25, 50, 100]

_PORTAL_STATUS_BADGE_MAP: dict[str, str] = {
    "open": "badge--warning",
    "in_progress": "badge--warning",
    "pending": "badge--warning",
    "resolved": "badge--success",
    "closed": "badge--muted",
}


async def _load_license_context(
    request: Request,
    *,
    require_manage: bool = True,
    require_order: bool = False,
):
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return user, None, None, None, redirect
    is_super_admin = bool(user.get("is_super_admin"))
    company_id_raw = user.get("company_id")
    if company_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No company associated with the current user",
        )
    try:
        company_id = int(company_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid company identifier")
    membership = await user_company_repo.get_user_company(user["id"], company_id)
    can_manage = bool(membership and membership.get("can_manage_licenses"))
    can_order = bool(membership and membership.get("can_order_licenses"))
    can_view_licenses = _membership_menu_can(user, membership, "menu.m365.licenses")
    can_write_licenses = _membership_menu_can(user, membership, "menu.m365.licenses", write=True)
    if require_manage and not (is_super_admin or can_manage or can_view_licenses):
        return (
            user,
            membership,
            None,
            company_id,
            RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER),
        )
    if require_order and not (is_super_admin or can_order or can_write_licenses):
        return (
            user,
            membership,
            None,
            company_id,
            RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER),
        )
    company = await company_repo.get_company_by_id(company_id)
    return user, membership, company, company_id, None


async def _send_license_webhook(
    *,
    action: str,
    company_id: int,
    license_id: int,
    quantity: int,
) -> None:
    if not settings.licenses_webhook_url or not settings.licenses_webhook_api_key:
        return
    payload = {
        "companyId": company_id,
        "licenseId": license_id,
        "quantity": quantity,
        "action": action,
    }
    headers = {
        "x-api-key": settings.licenses_webhook_api_key,
        "Content-Type": "application/json",
    }
    try:
        await webhook_monitor.enqueue_event(
            name="license-change",
            target_url=str(settings.licenses_webhook_url),
            payload=payload,
            headers=headers,
            max_attempts=5,
            backoff_seconds=300,
            attempt_immediately=True,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to enqueue license webhook", error=str(exc))


async def _load_company_section_context(
    request: Request,
    *,
    permission_field: str,
    allow_super_admin_without_company: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, int | None, RedirectResponse | None]:
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return user, None, None, None, redirect

    is_super_admin = bool(user and user.get("is_super_admin"))
    company_id_raw = user.get("company_id") if user else None
    if company_id_raw is None:
        if is_super_admin and allow_super_admin_without_company:
            return user, None, None, None, None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No company associated with the current user",
        )
    try:
        company_id = int(company_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid company identifier") from exc

    membership = await user_company_repo.get_user_company(user["id"], company_id)
    has_permission = bool(membership and membership.get(permission_field))
    if not (is_super_admin or has_permission):
        return (
            user,
            membership,
            None,
            company_id,
            RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER),
        )

    company = await company_repo.get_company_by_id(company_id)
    return user, membership, company, company_id, None


def _companies_redirect(
    *,
    company_id: int | None = None,
    success: str | None = None,
    error: str | None = None,
    extra: dict[str, str] | None = None,
) -> RedirectResponse:
    params: dict[str, str] = {}
    if company_id is not None:
        params["company_id"] = str(company_id)
    if extra:
        for key, value in extra.items():
            if value is None:
                continue
            params[key] = value
    query = urlencode(params)
    url = "/admin/companies"
    if query:
        url = f"{url}?{query}"
    response = RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    if success:
        set_flash(response, success.strip()[:200], "success")
    elif error:
        set_flash(response, error.strip()[:200], "error")
    return response


def _company_edit_redirect(
    *,
    company_id: int,
    success: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    url = f"/admin/companies/{company_id}/edit"
    response = RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    if success:
        set_flash(response, success.strip()[:200], "success")
    elif error:
        set_flash(response, error.strip()[:200], "error")
    return response





def _sanitize_message(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:200]


def _page_flash(message: str | None, variant: str = "info") -> dict[str, str] | None:
    """Return a normalized toast payload for page-level flash messaging."""
    text = _sanitize_message(message)
    if text is None:
        return None
    normalized_variant = str(variant or "info").strip().lower()
    if normalized_variant not in {"info", "success", "warning", "error"}:
        normalized_variant = "info"
    return {"message": text, "variant": normalized_variant}


def _derive_page_flash(
    context: Mapping[str, Any],
    *,
    template_name: str | None = None,
) -> dict[str, str] | None:
    """Infer a single flash payload from known context keys by precedence."""
    for key, variant in (
        ("error_message", "error"),
        ("cart_error", "error"),
        ("reply_error", "error"),
        ("success_message", "success"),
        ("cart_message", "success"),
        ("status_message", "info"),
        ("order_message", "info"),
    ):
        flash = _page_flash(context.get(key), variant)
        if flash:
            return flash

    errors = context.get("errors")
    if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes, bytearray)):
        collected: list[str] = []
        for entry in errors:
            message = _sanitize_message(str(entry) if entry is not None else None)
            if message:
                collected.append(message)
        if collected:
            flash = _page_flash("; ".join(collected), "error")
            if flash:
                return flash

    return None


def _sanitize_local_redirect_target(
    candidate: str | None,
    *,
    fallback: str,
    allowed_prefixes: Sequence[str] | None = None,
) -> str:
    """Return a safe local redirect target, or fallback when invalid."""
    if not isinstance(candidate, str):
        return fallback

    target = candidate.strip()
    if not target:
        return fallback

    parsed = URL(target)
    if parsed.scheme or parsed.netloc:
        return fallback

    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        return fallback

    if any(ord(char) < 32 for char in target):
        return fallback

    if allowed_prefixes and not any(target.startswith(prefix) for prefix in allowed_prefixes):
        return fallback

    return target




async def _render_impersonation_dashboard(
    request: Request,
    user: dict[str, Any],
    *,
    error_message: str | None = None,
    success_message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    try:
        candidates = await impersonation_service.list_impersonatable_users()
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to enumerate impersonation candidates", error=str(exc))
        candidates = []
        if error_message is None:
            error_message = "Unable to load impersonation candidates."
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    context = await _build_base_context(
        request,
        user,
        extra={
            "title": "User impersonation",
            "impersonation_candidates": candidates,
            "impersonation_error": error_message,
            "impersonation_success": success_message,
        },
    )
    return templates.TemplateResponse(
        context["request"],
        "admin/impersonation.html",
        context,
        status_code=status_code,
    )




@app.on_event("startup")
async def on_startup() -> None:
    try:
        await scheduler_service.run_system_update()
    except Exception as exc:
        log_error("Startup system update failed", error=str(exc))
    await db.connect()
    await db.run_migrations()
    async def _bootstrap_default_bcp_template() -> None:
        from app.services.bcp_template import bootstrap_default_template

        await bootstrap_default_template()

    async def _migrate_sync_m365_data_tasks() -> None:
        """Split legacy M365 sync tasks into the current license/contact tasks."""
        legacy_commands = {"sync_m365_data", "sync_o365"}
        new_commands = {"sync_m365_licenses", "sync_m365_contacts"}
        all_tasks = await scheduled_tasks_repo.list_tasks(include_inactive=False)
        # Group tasks by company_id
        from collections import defaultdict
        by_company: dict[int, list[dict]] = defaultdict(list)
        for t in all_tasks:
            cid = t.get("company_id")
            if cid is not None:
                by_company[int(cid)].append(t)
        migrated = 0
        for company_id, company_tasks in by_company.items():
            commands_for_company = {t["command"] for t in company_tasks}
            has_legacy = bool(legacy_commands & commands_for_company)
            has_new = bool(new_commands & commands_for_company)
            if not has_legacy or has_new:
                continue
            # Find an existing company name from the legacy task name if possible
            legacy_task = next(
                (t for t in company_tasks if t.get("command") in legacy_commands), None
            )
            task_name_prefix = ""
            if legacy_task:
                raw_name: str = legacy_task.get("name") or ""
                for suffix in (" - Sync Microsoft 365 data", " - Sync O365", " - Sync M365"):
                    if raw_name.endswith(suffix):
                        task_name_prefix = raw_name[: -len(suffix)]
                        break
            for command, label_suffix in (
                ("sync_m365_licenses", "Sync Microsoft 365 licenses"),
                ("sync_m365_contacts", "Sync Microsoft 365 contacts"),
            ):
                if command not in commands_for_company:
                    label = (
                        f"{task_name_prefix} - {label_suffix}"
                        if task_name_prefix
                        else label_suffix
                    )
                    await scheduled_tasks_repo.create_task(
                        name=label,
                        command=command,
                        cron=_random_daily_cron(),
                        company_id=company_id,
                        active=True,
                    )
            # Deactivate the legacy task so data is no longer synced twice
            for t in company_tasks:
                if t.get("command") in legacy_commands:
                    await scheduled_tasks_repo.set_task_active(t["id"], False)
            migrated += 1
            log_info(
                "Migrated legacy sync_m365_data task to split tasks",
                company_id=company_id,
            )
        if migrated:
            log_info("sync_m365_data migration complete", companies_migrated=migrated)

    async def _seed_demo_data_once() -> None:
        from app.services import demo_seeding as demo_seeding_service

        result = await demo_seeding_service.seed_demo_data()
        if result.get("skipped"):
            log_info("Demo data already seeded – skipping startup seed")
        else:
            log_info("Demo data seeded on startup", **{k: v for k, v in result.items() if k != "skipped"})

    startup_tasks = [
        ("sync_change_log_sources", change_log_service.sync_change_log_sources()),
        ("ensure_default_modules", modules_service.ensure_default_modules()),
        ("refresh_all_schedules", automations_service.refresh_all_schedules()),
        ("bootstrap_default_bcp_template", _bootstrap_default_bcp_template()),
        ("migrate_sync_m365_data_tasks", _migrate_sync_m365_data_tasks()),
        ("seed_demo_data_once", _seed_demo_data_once()),
    ]

    results = await asyncio.gather(
        *(task for _, task in startup_tasks), return_exceptions=True
    )

    for (name, _), result in zip(startup_tasks, results):
        if isinstance(result, Exception):
            if name == "bootstrap_default_bcp_template":
                log_error(
                    "Failed to bootstrap default BCP template", error=str(result)
                )
            else:
                log_error(
                    "Startup task failed", task=name, error=str(result)
                )
        elif name == "bootstrap_default_bcp_template":
            log_info("BCP default template bootstrapped")

    global _rag_relationship_stop, _rag_relationship_tasks
    _rag_relationship_stop = asyncio.Event()
    _rag_relationship_tasks = []
    if settings.enable_background_relationships and settings.rag_relationship_workers > 0:
        for _ in range(settings.rag_relationship_workers):
            _rag_relationship_tasks.append(asyncio.create_task(rag_relationship_service.relationship_worker(_rag_relationship_stop)))
    # Load every built-in feature pack discovered under ``app/features/``.
    pack_slugs = [
        slug.strip()
        for slug in (getattr(settings, "feature_packs", "") or "").split(",")
        if slug.strip()
    ]
    from app.core.module_capabilities import validate_capability_registry

    capability_errors = validate_capability_registry(
        modules_service.DEFAULT_MODULES, configured_feature_packs=pack_slugs
    )
    if capability_errors:
        for error in capability_errors:
            log_error("Module capability validation failed", error=error)
        raise RuntimeError("Invalid module capability registry: " + "; ".join(capability_errors))

    await scheduler_service.start()

    if pack_slugs:
        await feature_registry.load_many(pack_slugs)

    plugin_loader = init_plugin_loader(settings.plugin_dirs)
    await plugin_loader.load_all(feature_registry)

    # Optional dev-only auto-reload: when ``FEATURE_PACK_WATCH=true`` is
    # set we start a per-pack ``watchfiles`` watcher so editing any
    # file under ``app/features/<slug>/`` triggers a debounced reload
    # of just that pack.  Off by default in production.
    global _feature_pack_watcher
    _feature_pack_watcher = None
    if getattr(settings, "feature_pack_watch", False) and feature_registry.list():
        from app.core.feature_watcher import FeaturePackWatcher

        _feature_pack_watcher = FeaturePackWatcher(feature_registry)
        await _feature_pack_watcher.start()

    global _app_ready
    _app_ready = True
    log_info("Application started", environment=settings.environment)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _app_ready
    _app_ready = False
    if globals().get("_rag_relationship_stop") is not None:
        _rag_relationship_stop.set()
    for task in globals().get("_rag_relationship_tasks", []) or []:
        task.cancel()
    if globals().get("_rag_relationship_tasks"):
        await asyncio.gather(*_rag_relationship_tasks, return_exceptions=True)
    if _feature_pack_watcher is not None:
        await _feature_pack_watcher.stop()
    await feature_registry.unload_all()
    await scheduler_service.stop()
    await db.disconnect()
    log_info("Application shutdown")


def _first_non_blank(keys: Iterable[str], *sources: Mapping[str, Any]) -> Any | None:
    for source in sources:
        if not source:
            continue
        for key in keys:
            if key not in source:
                continue
            value = source[key]
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return None


def _parse_multipart_fallback(text_body: str) -> dict[str, str]:
    """Parse rudimentary multipart form payloads when the content type is wrong."""

    boundary: str | None = None
    for line in text_body.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("--") and "content-disposition" not in candidate.lower():
            boundary = candidate
            break

    if not boundary:
        return {}

    parts = text_body.split(boundary)
    parsed: dict[str, str] = {}

    for part in parts:
        chunk = part.strip()
        if not chunk or chunk == "--":
            continue
        if chunk.startswith("--") and not chunk.strip("-"):
            continue

        # Remove any leading CRLF left after splitting.
        while chunk.startswith("\r\n"):
            chunk = chunk[2:]

        headers_section, separator, value_section = chunk.partition("\r\n\r\n")
        if not separator:
            continue

        field_name: str | None = None
        for header_line in headers_section.splitlines():
            header = header_line.strip()
            if not header.lower().startswith("content-disposition"):
                continue
            for attribute in header.split(";"):
                attribute = attribute.strip()
                if attribute.lower().startswith("name="):
                    field_name = attribute.split("=", 1)[1].strip().strip('"')
                    break
            if field_name:
                break

        if not field_name:
            continue

        value = value_section.rstrip()
        if value.endswith("--"):
            value = value[:-2].rstrip()

        parsed[field_name] = value

    return parsed


async def _extract_switch_company_payload(request: Request) -> dict[str, Any]:
    raw_content_type = request.headers.get("content-type", "")
    content_type = raw_content_type.split(";", 1)[0].strip().lower()

    data: dict[str, Any] = {}

    if content_type == "application/json":
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError, RuntimeError, UnicodeDecodeError):
            payload = None
        if isinstance(payload, dict):
            return payload
        # Fall back to parsing the raw body below so mislabelled JSON requests
        # (for example, form submissions with an incorrect content type) are
        # still handled gracefully.

    should_attempt_form = content_type in {
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    }

    cached_form: FormData | None = getattr(request, "_form", None)
    form_data: FormData | None
    if cached_form is not None:
        form_data = cached_form
    elif should_attempt_form:
        try:
            form_data = await request.form()
        except Exception:  # pragma: no cover - fallback when Starlette cannot parse the body
            form_data = None
    else:
        form_data = None

    if form_data is not None:
        keys = list(form_data.keys())
        if keys:
            for key in keys:
                values = form_data.getlist(key)
                if values:
                    data[key] = values[0]
            return data

    body_bytes: bytes | None = getattr(request, "_body", None)

    if body_bytes is None:
        try:
            body_bytes = await request.body()
        except RuntimeError:
            body_bytes = getattr(request, "_body", None)

    if not body_bytes:
        return data

    charset = getattr(request, "charset", None) or "utf-8"
    try:
        text_body = body_bytes.decode(charset, errors="replace")
    except LookupError:  # pragma: no cover - unsupported encodings
        text_body = body_bytes.decode("utf-8", errors="replace")

    lower_body = text_body.lower()

    if "content-disposition:" in lower_body and "form-data" in lower_body:
        parsed = _parse_multipart_fallback(text_body)
        if parsed:
            for key, value in parsed.items():
                if key not in data:
                    data[key] = value
            if data:
                return data

    if "=" in text_body or "&" in text_body:
        for key, value in parse_qsl(text_body, keep_blank_values=True):
            if key not in data:
                data[key] = value

        if data:
            return data

    try:
        payload = json.loads(text_body)
    except (json.JSONDecodeError, ValueError):
        return data

    if isinstance(payload, dict):
        return payload

    return data


@app.get("/search", response_class=HTMLResponse)
async def ai_search_page(request: Request):
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return redirect
    return await _render_template(
        "search.html",
        request,
        user,
        extra={"title": "Search"},
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return redirect
    overview = await _build_consolidated_overview(request, user)

    extra: dict[str, Any] = {
        "title": "Dashboard",
        "dashboard": overview,
    }
    if isinstance(overview, dict) and "unread_notifications" in overview:
        extra["notification_unread_count"] = overview.get("unread_notifications", 0)

    return await _render_template(
        "dashboard.html",
        request,
        user,
        extra=extra,
    )


@app.get("/licenses", response_class=HTMLResponse)
async def licenses_page(request: Request):
    user, membership, company, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    records = await license_repo.list_company_licenses(company_id)
    formatted: list[dict[str, Any]] = []
    for record in records:
        expiry_value = record.get("expiry_date")
        if isinstance(expiry_value, datetime):
            expiry_display = expiry_value.strftime("%Y-%m-%d")
        elif isinstance(expiry_value, date):
            expiry_display = expiry_value.strftime("%Y-%m-%d")
        elif expiry_value:
            expiry_display = str(expiry_value)
        else:
            expiry_display = ""
        formatted.append(record | {"expiry_display": expiry_display})
    is_super_admin = bool(user.get("is_super_admin"))
    can_order = bool(is_super_admin or (membership and membership.get("can_order_licenses")))
    can_manage = bool(is_super_admin or (membership and membership.get("can_manage_licenses")))
    credentials = await m365_repo.get_credentials(company_id)
    extra = {
        "title": "Licenses",
        "licenses": formatted,
        "company": company,
        "can_order_licenses": can_order,
        "can_manage_licenses": can_manage,
        "can_manage_sku_mappings": is_super_admin,
        "webhook_enabled": bool(settings.licenses_webhook_url and settings.licenses_webhook_api_key),
        "has_m365_credentials": bool(credentials),
    }
    return await _render_template("licenses/index.html", request, user, extra=extra)


@app.get("/licenses/sku-mappings", response_class=JSONResponse)
async def list_license_sku_mappings(request: Request):
    user, _membership, _company, _company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    mappings = await sku_friendly_repo.list_mappings()
    return JSONResponse({"items": mappings})


@app.post("/licenses/sku-mappings", response_class=JSONResponse)
async def upsert_license_sku_mapping(request: Request):
    user, _membership, _company, _company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
    sku = str(payload.get("sku") or "").strip().upper()
    friendly_name = str(payload.get("friendly_name") or "").strip()
    hidden = bool(payload.get("hidden"))
    if not sku:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU is required")
    if not friendly_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Friendly name is required")
    mapping = await sku_friendly_repo.upsert_mapping(sku, friendly_name, hidden=hidden)
    return JSONResponse({"item": mapping, "success": True})


@app.delete("/licenses/sku-mappings/{sku}", response_class=JSONResponse)
async def delete_license_sku_mapping(request: Request, sku: str):
    user, _membership, _company, _company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    cleaned_sku = sku.strip().upper()
    if not cleaned_sku:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU is required")
    await sku_friendly_repo.delete_mapping(cleaned_sku)
    return JSONResponse({"success": True})


# ---------------------------------------------------------------------------
# Company overview report
# ---------------------------------------------------------------------------
@app.get("/licenses/{license_id}/allocated", response_class=JSONResponse)
async def license_allocations(request: Request, license_id: int):
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    record = await license_repo.get_license_by_id(license_id)
    if not record or int(record.get("company_id", 0)) != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    members = await license_repo.list_staff_for_license(license_id)
    return JSONResponse(members)


@app.post("/licenses/{license_id}/order", response_class=JSONResponse)
async def order_license(request: Request, license_id: int):
    user, membership, _, company_id, redirect = await _load_license_context(
        request,
        require_manage=False,
        require_order=True,
    )
    if redirect:
        return redirect
    record = await license_repo.get_license_by_id(license_id)
    if not record or int(record.get("company_id", 0)) != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
    quantity = int(payload.get("quantity", 0) or 0)
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than zero")
    await _send_license_webhook(
        action="order",
        company_id=company_id,
        license_id=license_id,
        quantity=quantity,
    )
    log_info(
        "License order submitted",
        company_id=company_id,
        license_id=license_id,
        quantity=quantity,
        user_id=user.get("id"),
    )
    return JSONResponse({"success": True})


@app.post("/licenses/{license_id}/remove", response_class=JSONResponse)
async def remove_license(request: Request, license_id: int):
    user, membership, _, company_id, redirect = await _load_license_context(
        request,
        require_manage=False,
        require_order=True,
    )
    if redirect:
        return redirect
    record = await license_repo.get_license_by_id(license_id)
    if not record or int(record.get("company_id", 0)) != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
    quantity = int(payload.get("quantity", 0) or 0)
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than zero")
    await _send_license_webhook(
        action="remove",
        company_id=company_id,
        license_id=license_id,
        quantity=quantity,
    )
    log_info(
        "License removal requested",
        company_id=company_id,
        license_id=license_id,
        quantity=quantity,
        user_id=user.get("id"),
    )
    return JSONResponse({"success": True})


@app.post("/switch-company", response_class=RedirectResponse)
async def switch_company(
    request: Request,
):
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return redirect
    session = await session_manager.load_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    body_data = await _extract_switch_company_payload(request)
    query_params = request.query_params

    company_id_raw = _first_non_blank(("companyId", "company_id"), body_data, query_params)
    if company_id_raw is not None:
        try:
            company_id = int(company_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid company identifier")
    else:
        company_id = None

    if company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="companyId is required")

    return_url_raw = _first_non_blank(("returnUrl", "return_url"), body_data, query_params)
    return_url: str | None = return_url_raw if isinstance(return_url_raw, str) else None

    companies = await company_access.list_accessible_companies(user)
    request.state.available_companies = companies

    if any(company.get("company_id") == company_id for company in companies):
        await session_manager.set_active_company(session, company_id)
        user["company_id"] = company_id
        request.state.active_company_id = company_id

    destination = _sanitize_local_redirect_target(return_url, fallback="/")

    return RedirectResponse(url=destination, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/m365", response_class=HTMLResponse)
async def m365_page(request: Request):
    user, membership, company, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not _membership_menu_can(user, membership, "menu.m365.configuration"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Office 365 configuration access required")
    credentials = await m365_service.get_credentials(company_id)
    credential_view = None
    if credentials:
        expires = credentials.get("token_expires_at")
        if isinstance(expires, datetime):
            expires_display = expires.replace(tzinfo=timezone.utc).isoformat()
        elif expires:
            expires_display = str(expires)
        else:
            expires_display = None
        credential_view = {
            "tenant_id": credentials.get("tenant_id"),
            "client_id": credentials.get("client_id"),
            "token_expires_at": expires_display,
        }

    extra = {
        "title": "Office 365",
        "company": company,
        "credential": credential_view,
        "is_super_admin": bool(user.get("is_super_admin")),
        "has_credentials": bool(credentials),
    }
    return await _render_template("m365/index.html", request, user, extra=extra)










# ---------------------------------------------------------------------------
# Microsoft 365 Best Practices
# ---------------------------------------------------------------------------














































@app.post("/m365/credentials", response_class=RedirectResponse)
async def save_m365_credentials(
    request: Request,
    tenant_id: str = Form(..., alias="tenantId"),
    client_id: str = Form(..., alias="clientId"),
    client_secret: str = Form(..., alias="clientSecret"),
):
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    await m365_service.upsert_credentials(
        company_id=company_id,
        tenant_id=tenant_id.strip(),
        client_id=client_id.strip(),
        client_secret=client_secret.strip(),
    )
    log_info("Microsoft 365 credentials updated", company_id=company_id, user_id=user.get("id"))
    return RedirectResponse(url="/m365", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/m365/credentials/delete", response_class=RedirectResponse)
async def delete_m365_credentials(request: Request):
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    await m365_service.delete_credentials(company_id)
    log_info("Microsoft 365 credentials deleted", company_id=company_id, user_id=user.get("id"))
    return RedirectResponse(url="/m365", status_code=status.HTTP_303_SEE_OTHER)






def _build_m365_redirect_uri(request: Request) -> str:
    """Return the absolute redirect URI for the M365 OAuth callback.

    Uses PORTAL_URL when configured so that the redirect URI is stable
    regardless of which host the request arrives on.  Falls back to
    request.url_for and forces the scheme to HTTPS (required by Azure AD).
    """
    if settings.portal_url:
        base = str(settings.portal_url).rstrip("/")
        return f"{base}/m365/callback"
    uri = str(request.url_for("m365_callback"))
    if uri.startswith("http://"):
        uri = "https://" + uri[len("http://"):]
    return uri


@app.post("/m365/test", response_class=RedirectResponse)
async def test_m365_connectivity(request: Request):
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    try:
        result = await m365_service.test_connectivity(company_id)
    except m365_service.M365Error as exc:
        encoded = urlencode({"error": f"Microsoft 365 connectivity test failed: {exc}"})
        return RedirectResponse(url=f"/m365?{encoded}", status_code=status.HTTP_303_SEE_OTHER)

    org_name = result.get("organization_name")
    summary = "Microsoft 365 connectivity test succeeded"
    if org_name:
        summary = f"Microsoft 365 connectivity test succeeded for {org_name}"
    log_info(summary, company_id=company_id, user_id=user.get("id"))
    encoded = urlencode({"success": summary})
    return RedirectResponse(url=f"/m365?{encoded}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/m365/sync", response_class=JSONResponse)
async def sync_m365(request: Request):
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    try:
        await m365_service.sync_company_licenses(company_id)
    except m365_service.M365Error as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_info("Microsoft 365 license sync triggered", company_id=company_id, user_id=user.get("id"))
    return JSONResponse({"success": True})


@app.get("/m365/connect")
async def m365_connect(request: Request):
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    credentials = await m365_service.get_credentials(company_id)
    if not credentials:
        return RedirectResponse(url="/m365", status_code=status.HTTP_303_SEE_OTHER)
    redirect_uri = _build_m365_redirect_uri(request)
    state = oauth_state_serializer.dumps({
        "company_id": company_id,
        "user_id": user.get("id"),
    })
    params = {
        "client_id": credentials["client_id"],
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": m365_service.CONNECT_SCOPE,
        "state": state,
        "prompt": "consent",
    }
    authorize_url = (
        f"https://login.microsoftonline.com/{credentials['tenant_id']}/oauth2/v2.0/authorize"
        f"?{urlencode(params)}"
    )
    return RedirectResponse(url=authorize_url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/m365/provision")
async def m365_provision(request: Request, tenant_id: str = Query(...)):
    """Start the admin-consent OAuth flow to auto-provision an enterprise app."""
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    tenant_id = tenant_id.strip()
    if not tenant_id:
        encoded = urlencode({"error": "Tenant ID is required to auto-provision."})
        return RedirectResponse(url=f"/m365?{encoded}", status_code=status.HTTP_303_SEE_OTHER)
    redirect_uri = _build_m365_redirect_uri(request)
    code_verifier, code_challenge = m365_service.generate_pkce_pair()
    verifier_id = await _store_m365_provision_code_verifier(code_verifier)
    state = oauth_state_serializer.dumps(
        {
            "company_id": company_id,
            "user_id": user.get("id"),
            "tenant_id": tenant_id,
            "flow": "provision",
            "verifier_id": verifier_id,
        }
    )
    oauth_client_id = await m365_service.get_effective_pkce_client_id_for_company(
        company_id, redirect_uri=redirect_uri
    )
    params = {
        "client_id": oauth_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": m365_service.PROVISION_SCOPE,
        "state": state,
        "prompt": "consent",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        # domain_hint directs the admin to sign in to the correct customer
        # tenant without requiring the PKCE client to be registered in that
        # tenant (avoids AADSTS700016 for single-tenant partner apps).
        "domain_hint": tenant_id,
    }
    # Use the /organizations endpoint so that the PKCE public client does not
    # need to be registered or consented in every customer tenant.  The
    # domain_hint above steers the Global Admin to the correct tenant.
    authorize_url = (
        "https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize"
        f"?{urlencode(params)}"
    )
    return RedirectResponse(url=authorize_url, status_code=status.HTTP_303_SEE_OTHER)




async def _get_m365_admin_credentials(company_id: int | None = None) -> tuple[str | None, str | None]:
    """Return (client_id, client_secret) for the M365 admin app flow.

    Resolution order:
    1. Per-company admin credentials from company_m365_credentials (if company_id provided).
    2. Global ``m365-admin`` integration module settings.
    3. Environment variables ``M365_ADMIN_CLIENT_ID`` / ``M365_ADMIN_CLIENT_SECRET``.

    The ``client_secret`` is decrypted if it was stored as ciphertext;
    plaintext values (manually configured) are returned unchanged because
    :func:`decrypt_secret` is a no-op for non-ciphertext strings.
    """
    # 1. Per-company admin credentials (when company_id is provided)
    if company_id is not None:
        company_admin_creds = await m365_service.get_company_admin_credentials(company_id)
        if company_admin_creds:
            client_id = company_admin_creds.get("client_id")
            client_secret = company_admin_creds.get("client_secret")
            if client_id and client_secret:
                return client_id, client_secret

    # 2. Global module credentials
    try:
        module = await modules_service.get_module("m365-admin", redact=False)
    except RuntimeError:
        module = None
    if module:
        module_settings = module.get("settings") or {}
        client_id = str(module_settings.get("client_id") or "").strip() or None
        raw_secret = str(module_settings.get("client_secret") or "").strip() or None
        if client_id and raw_secret:
            client_secret = decrypt_secret(raw_secret)
            return client_id, client_secret

    # 3. Fall back to environment variables
    return settings.m365_admin_client_id or None, settings.m365_admin_client_secret or None


@app.get("/m365/discover")
async def m365_discover(request: Request):
    """Sign in as Global Admin to discover the tenant ID automatically."""
    user, membership, _, company_id, redirect = await _load_license_context(request)
    if redirect:
        return redirect
    if not user.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    redirect_uri = _build_m365_redirect_uri(request)

    # Always use PKCE for the discover flow regardless of whether admin
    # credentials are configured.  The discover step only needs to extract
    # a tenant ID from the id_token - it requires no confidential-client
    # capabilities.  Using PKCE avoids AADSTS700025 ("Client is public so
    # neither client_assertion nor client_secret should be presented")
    # which occurs when the configured admin client_id belongs to a public
    # PKCE app rather than a confidential app.
    code_verifier, code_challenge = m365_service.generate_pkce_pair()
    oauth_client_id = await m365_service.get_effective_pkce_client_id_for_company(
        company_id, redirect_uri=redirect_uri
    )

    state_payload: dict = {
        "company_id": company_id,
        "user_id": user.get("id"),
        "flow": "discover",
        "code_verifier": code_verifier,
    }

    state = oauth_state_serializer.dumps(state_payload)
    params: dict = {
        "client_id": oauth_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": m365_service.DISCOVER_SCOPE,
        "state": state,
        "prompt": "select_account",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    authorize_url = (
        "https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize"
        f"?{urlencode(params)}"
    )
    return RedirectResponse(url=authorize_url, status_code=status.HTTP_303_SEE_OTHER)






async def _best_effort_sync_m365_email_domains(company_id: int) -> None:
    """Fire-and-forget helper that syncs M365 tenant domains to the company's email domains list.

    Failures are logged but never propagate so that the OAuth callback redirect
    is not affected.
    """
    try:
        result = await m365_service.sync_email_domains(company_id)
        log_info(
            "M365 email domain sync triggered from callback",
            company_id=company_id,
            added=result.get("added"),
        )
    except Exception as exc:  # noqa: BLE001
        log_warning(
            "M365 email domain sync failed (best-effort)",
            company_id=company_id,
            error=str(exc),
        )


@app.get("/m365/callback", name="m365_callback")
async def m365_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        message = request.query_params.get("error_description", error)
        # Try to determine the flow from state so we can redirect to the
        # correct page and clear any stale PKCE client IDs. If state is
        # unparseable we fall back to /m365.
        error_redirect = "/m365"
        state_data: dict[str, Any] = {}
        if state:
            try:
                state_data = oauth_state_serializer.loads(state)
            except Exception:
                pass
        # AADSTS700016 means the PKCE app registration no longer exists in the
        # tenant (it was deleted). Clear the stale pkce_client_id (including
        # any company-specific value) so that the next sign-in attempt falls
        # back to the Azure CLI public client, and guide the admin to re-
        # provision so a fresh PKCE app is created.
        if "AADSTS700016" in message:
            company_id_raw = state_data.get("company_id")
            if company_id_raw is not None:
                try:
                    await m365_service.clear_company_pkce_client_id(int(company_id_raw))
                except (TypeError, ValueError):
                    log_warning(
                        "Skipping per-company PKCE clear; invalid company_id in state",
                        company_id_raw=company_id_raw,
                    )
                except Exception as exc:
                    log_warning(
                        "Failed to clear per-company PKCE client ID after AADSTS700016",
                        company_id_raw=company_id_raw,
                        error=str(exc),
                    )
            try:
                await m365_service.clear_pkce_client_id()
            except Exception as exc:
                log_warning(
                    "Failed to clear global PKCE client ID after AADSTS700016",
                    error=str(exc),
                )
            message = (
                "The PKCE app registration was not found in Azure AD (AADSTS700016). "
                "The cached app ID has been cleared. Please sign in again; if the problem "
                "persists, re-provision the M365 integration via Admin → M365."
            )
        encoded = urlencode({"error": message})
        return RedirectResponse(url=f"{error_redirect}?{encoded}", status_code=status.HTTP_303_SEE_OTHER)
    if not code or not state:
        return flash_redirect("/m365", "invalid response", "error")
    try:
        state_data = oauth_state_serializer.loads(state)
    except BadSignature:
        return flash_redirect("/m365", "invalid state", "error")
    company_id_raw = state_data.get("company_id")
    try:
        company_id = int(company_id_raw)
    except (TypeError, ValueError):
        company_id = 0
    flow = state_data.get("flow", "connect")

    if flow == "discover":
        # ── Tenant-discovery flow ──────────────────────────────────────────
        # Exchange the auth code to get a token, then extract the tid claim.
        return_to_company_edit = state_data.get("return_to") == "company_edit"
        redirect_uri = _build_m365_redirect_uri(request)

        def _discover_error(msg: str) -> RedirectResponse:
            if return_to_company_edit:
                return _company_edit_redirect(company_id=company_id, error=msg)
            encoded = urlencode({"error": msg})
            return RedirectResponse(
                url=f"/m365?{encoded}", status_code=status.HTTP_303_SEE_OTHER
            )

        _discover_cid, _discover_csec = await _get_m365_admin_credentials(company_id)

        # Determine the token exchange method.  When the flow was initiated
        # using PKCE (state contains a verifier handle), the exchange is done
        # with the configured PKCE public client – no client secret required.
        # Otherwise fall back to the traditional secret-based exchange using
        # existing admin credentials or the M365_BOOTSTRAP_* env vars.
        code_verifier: str | None = None
        pkce_handle = state_data.get("pkce_handle")
        if isinstance(pkce_handle, str) and pkce_handle:
            code_verifier = await _pop_pkce_verifier(pkce_handle)
            if not code_verifier:
                return _csp_provision_error(
                    "Provisioning session expired. Please restart the CSP provisioning flow."
                )
        elif state_verifier := state_data.get("code_verifier"):
            # code_verifier stored directly in the signed state by the discover flow.
            code_verifier = str(state_verifier)
        token_endpoint = (
            "https://login.microsoftonline.com/organizations/oauth2/v2.0/token"
        )
        if code_verifier:
            token_data: dict = {
                "client_id": await m365_service.get_effective_pkce_client_id_for_company(
                    company_id, redirect_uri=redirect_uri
                ),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "scope": m365_service.DISCOVER_SCOPE,
            }
        else:
            # code_verifier is always included by the discover endpoints now.
            # This branch handles legacy state tokens that pre-date the PKCE-
            # always change.  Using admin credentials here risks AADSTS700025
            # if the configured client_id belongs to a public PKCE app, so we
            # only fall back when the credentials are actually present and
            # surface a clear error on failure.
            if not _discover_cid or not _discover_csec:
                return _discover_error(
                    "Sign-in session is incomplete. Please click 'Sign in as Global Admin' again."
                )
            token_data = {
                "client_id": _discover_cid,
                "client_secret": _discover_csec,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "scope": m365_service.DISCOVER_SCOPE,
            }
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(token_endpoint, data=token_data)
        if token_response.status_code != 200:
            log_error(
                "Microsoft 365 discover token exchange failed",
                status=token_response.status_code,
                body=token_response.text,
            )
            # AADSTS700025 means the client_id used is a public client but
            # client_secret was presented.  This happens when the configured
            # admin credentials reference a public PKCE app instead of a
            # confidential app.  Provide an actionable error message.
            error_body = token_response.text or ""
            if "AADSTS700025" in error_body:
                return _discover_error(
                    "Tenant discovery failed: the configured admin client is a "
                    "public app and cannot use a client secret (AADSTS700025). "
                    "Please click 'Sign in as Global Admin' to retry using PKCE."
                )
            return _discover_error("Sign-in failed during tenant discovery.")

        token_payload = token_response.json()
        # Prefer id_token (contains tid reliably); fall back to access_token
        id_token = token_payload.get("id_token") or token_payload.get("access_token", "")
        if not id_token:
            return _discover_error("No token received during tenant discovery.")

        try:
            discovered_tenant_id = m365_service.extract_tenant_id_from_token(id_token)
        except m365_service.M365Error as exc:
            log_error(
                "Failed to extract tenant ID from token",
                company_id=company_id,
                error=str(exc),
            )
            return _discover_error(f"Could not determine Tenant ID: {exc}")

        log_info(
            "Tenant ID discovered via Global Admin sign-in",
            company_id=company_id,
            tenant_id=discovered_tenant_id,
        )

        # Redirect to the provision flow using the discovered tenant ID
        if return_to_company_edit:
            return RedirectResponse(
                url=f"/admin/companies/{company_id}/m365-provision"
                f"?{urlencode({'tenant_id': discovered_tenant_id})}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(
            url=f"/m365/provision?{urlencode({'tenant_id': discovered_tenant_id})}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if flow == "csp_admin_provision":
        # ── Auto-provision the CSP/Lighthouse admin app registration ──────
        # The admin signed in with PROVISION_SCOPE targeting /organizations,
        # so their token has Application.ReadWrite.All + AppRoleAssignment.ReadWrite.All
        # in their own partner tenant.  We use it to create a dedicated app
        # registration that will serve as the M365 admin OAuth client.
        redirect_uri = _build_m365_redirect_uri(request)

        def _csp_provision_error(msg: str) -> RedirectResponse:
            encoded = urlencode({"error": msg})
            return RedirectResponse(
                url=f"/admin/csp/customers?{encoded}", status_code=status.HTTP_303_SEE_OTHER
            )

        # Determine the token exchange method.  When the flow was initiated
        # using PKCE (state contains a code_verifier), the exchange is done
        # with the public Azure CLI client – no client secret is required.
        # Otherwise fall back to the traditional secret-based exchange using
        # existing admin credentials or the M365_BOOTSTRAP_* env vars.
        code_verifier: str | None = state_data.get("code_verifier")
        token_endpoint = (
            "https://login.microsoftonline.com/organizations/oauth2/v2.0/token"
        )
        if code_verifier:
            token_data: dict = {
                "client_id": m365_service.get_pkce_client_id(),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "scope": m365_service.PROVISION_SCOPE,
            }
        else:
            bootstrap_client_id = str(settings.m365_bootstrap_client_id or "").strip()
            existing_client_id, existing_client_secret = await _get_m365_admin_credentials()
            oauth_client_id = existing_client_id or bootstrap_client_id
            bootstrap_client_secret = str(settings.m365_bootstrap_client_secret or "").strip()
            oauth_client_secret = existing_client_secret or bootstrap_client_secret

            if not oauth_client_id or not oauth_client_secret:
                return _csp_provision_error(
                    "No client credentials available to complete provisioning. "
                    "Configure M365_BOOTSTRAP_CLIENT_ID / M365_BOOTSTRAP_CLIENT_SECRET or "
                    "enter credentials in the M365 Admin module."
                )

            token_data = {
                "client_id": oauth_client_id,
                "client_secret": oauth_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "scope": m365_service.PROVISION_SCOPE,
            }
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(token_endpoint, data=token_data)
        if token_response.status_code != 200:
            log_error(
                "CSP admin provision token exchange failed",
                status=token_response.status_code,
                body=token_response.text,
            )
            return _csp_provision_error("Authorization failed during CSP admin provisioning.")

        token_payload = token_response.json()
        access_token = token_payload.get("access_token", "")
        if not access_token:
            return _csp_provision_error("No access token received during CSP admin provisioning.")

        # Extract the partner tenant ID from the token
        try:
            partner_tenant_id = m365_service.extract_tenant_id_from_token(access_token)
        except m365_service.M365Error:
            try:
                id_token = token_payload.get("id_token", "")
                partner_tenant_id = m365_service.extract_tenant_id_from_token(id_token)
            except m365_service.M365Error:
                return _csp_provision_error(
                    "Unable to determine partner tenant ID from token."
                )

        try:
            provision_result = await m365_service.provision_csp_admin_app_registration(
                access_token=access_token,
                tenant_id=partner_tenant_id,
                display_name="MyPortal CSP Admin",
                redirect_uri=redirect_uri,
            )
        except m365_service.M365Error as exc:
            log_error(
                "CSP admin app provisioning failed",
                tenant_id=partner_tenant_id,
                error=str(exc),
            )
            return _csp_provision_error(f"Provisioning failed: {exc}")

        await m365_service.update_admin_m365_credentials(
            client_id=provision_result["client_id"],
            client_secret=provision_result["client_secret"],
            tenant_id=provision_result["tenant_id"],
            app_object_id=provision_result.get("app_object_id"),
            client_secret_key_id=provision_result.get("client_secret_key_id"),
            client_secret_expires_at=provision_result.get("client_secret_expires_at"),
        )
        log_info(
            "M365 CSP admin app provisioned and credentials stored",
            tenant_id=partner_tenant_id,
            client_id=provision_result["client_id"],
        )
        encoded = urlencode({"success": "Microsoft 365 CSP admin app provisioned successfully. You can now sign in with your CSP account."})
        return RedirectResponse(
            url=f"/admin/csp/customers?{encoded}", status_code=status.HTTP_303_SEE_OTHER
        )

    if flow == "provision":
        # ── Auto-provision flow ────────────────────────────────────────────
        tenant_id = str(state_data.get("tenant_id", "")).strip()
        return_to_company_edit = state_data.get("return_to") == "company_edit"
        redirect_uri = _build_m365_redirect_uri(request)

        def _provision_error(msg: str) -> RedirectResponse:
            if return_to_company_edit:
                return _company_edit_redirect(company_id=company_id, error=msg)
            encoded = urlencode({"error": msg})
            return RedirectResponse(
                url=f"/m365?{encoded}", status_code=status.HTTP_303_SEE_OTHER
            )

        if not tenant_id:
            return _provision_error("Missing tenant ID in provision state.")

        # Always use PKCE for the provision flow so the customer's Global Admin
        # can grant consent without requiring the CSP admin app to have a service
        # principal in the customer tenant (avoids AADSTS700016).
        verifier_id = state_data.get("verifier_id")
        code_verifier = await _pop_m365_provision_code_verifier(verifier_id)
        token_endpoint = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        )
        if code_verifier:
            token_data = {
                "client_id": await m365_service.get_effective_pkce_client_id_for_company(
                    company_id, redirect_uri=redirect_uri
                ),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "scope": m365_service.PROVISION_SCOPE,
            }
        else:
            # Backward-compatibility: fall back to admin credentials when no
            # verifier_id/code_verifier is present (e.g. old state tokens in flight).
            code_verifier = state_data.get("code_verifier")
            if code_verifier:
                token_data = {
                    "client_id": m365_service.get_pkce_client_id(),
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                    "scope": m365_service.PROVISION_SCOPE,
                }
            else:
                _provision_cid, _provision_csec = await _get_m365_admin_credentials()
                if not _provision_cid or not _provision_csec:
                    return _provision_error("Admin M365 credentials are not configured.")
                token_data = {
                    "client_id": _provision_cid,
                    "client_secret": _provision_csec,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "scope": m365_service.PROVISION_SCOPE,
                }
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(token_endpoint, data=token_data)
        if token_response.status_code != 200:
            log_error(
                "Microsoft 365 provision token exchange failed",
                status=token_response.status_code,
                body=token_response.text,
            )
            return _provision_error("Authorization failed during provision flow.")

        token_payload = token_response.json()
        access_token = token_payload.get("access_token", "")
        if not access_token:
            return _provision_error("No access token received during provision.")

        # Resolve tenant from the returned token when possible. This protects
        # against mismatches where a Global Admin signs into a different tenant
        # than the tenant_id carried in OAuth state, which can otherwise leave
        # credentials stored against the wrong tenant and cause Graph failures.
        try:
            token_tenant_id = m365_service.extract_tenant_id_from_token(access_token)
        except m365_service.M365Error:
            token_tenant_id = ""

        effective_tenant_id = token_tenant_id.strip() or tenant_id
        if token_tenant_id and token_tenant_id != tenant_id:
            log_info(
                "M365 provision callback tenant mismatch; using token tenant",
                company_id=company_id,
                requested_tenant_id=tenant_id,
                token_tenant_id=token_tenant_id,
            )

        # Load company name for a descriptive app display name
        company_record = await company_repo.get_company_by_id(company_id)
        company_name = (company_record.get("name") or "").strip() if company_record else ""
        display_name = f"MyPortal – {company_name}" if company_name else "MyPortal Integration"

        try:
            provision_result = await m365_service.provision_app_registration(
                access_token=access_token,
                display_name=display_name,
                redirect_uri=redirect_uri,
            )
        except m365_service.M365Error as exc:
            log_error(
                "M365 app provisioning failed",
                company_id=company_id,
                tenant_id=effective_tenant_id,
                error=str(exc),
            )
            return _provision_error(f"Provisioning failed: {exc}")

        await m365_service.upsert_credentials(
            company_id=company_id,
            tenant_id=effective_tenant_id,
            client_id=provision_result["client_id"],
            client_secret=provision_result["client_secret"],
            app_object_id=provision_result.get("app_object_id"),
            client_secret_key_id=provision_result.get("client_secret_key_id"),
            client_secret_expires_at=provision_result.get("client_secret_expires_at"),
        )
        log_info(
            "M365 enterprise app provisioned and credentials stored",
            company_id=company_id,
            tenant_id=effective_tenant_id,
            client_id=provision_result["client_id"],
        )

        # Best-effort: provision a dedicated PKCE public client for this company
        try:
            await m365_service.auto_provision_company_pkce_client_id(
                company_id,
                redirect_uri=redirect_uri,
                company_admin_creds={
                    "tenant_id": effective_tenant_id,
                    "client_id": provision_result["client_id"],
                    "client_secret": provision_result["client_secret"],
                    "app_object_id": provision_result.get("app_object_id"),
                    "client_secret_key_id": provision_result.get("client_secret_key_id"),
                    "client_secret_expires_at": provision_result.get(
                        "client_secret_expires_at"
                    ),
                },
            )
        except Exception as exc:  # pragma: no cover - best-effort helper
            log_warning(
                "Per-company PKCE auto-provision failed after M365 app provisioning",
                company_id=company_id,
                error=str(exc),
            )

        # Auto-create default sync tasks for the company if not already present.
        existing_commands = await scheduled_tasks_repo.get_commands_for_company(company_id)
        has_m365_sync_task = bool(
            {"sync_m365_data", "sync_o365", "sync_m365_licenses", "sync_m365_contacts"}
            & existing_commands
        )
        sync_staff_task_name = (
            f"{company_name} - Sync staff directory"
            if company_name
            else "Sync staff directory"
        )
        # Create the split M365 sync tasks if no M365 sync tasks exist yet
        if not has_m365_sync_task:
            for command, label_suffix in (
                ("sync_m365_licenses", "Sync Microsoft 365 licenses"),
                ("sync_m365_contacts", "Sync Microsoft 365 contacts"),
            ):
                label = f"{company_name} - {label_suffix}" if company_name else label_suffix
                await scheduled_tasks_repo.create_task(
                    name=label,
                    command=command,
                    cron=_random_daily_cron(),
                    company_id=company_id,
                    active=True,
                )
                log_info(
                    "Auto-created scheduled task after M365 provisioning",
                    command=command,
                    company_id=company_id,
                )
        if "sync_staff" not in existing_commands:
            await scheduled_tasks_repo.create_task(
                name=sync_staff_task_name,
                command="sync_staff",
                cron=_random_daily_cron(),
                company_id=company_id,
                active=True,
            )
            log_info(
                "Auto-created scheduled task after M365 provisioning",
                command="sync_staff",
                company_id=company_id,
            )
        await scheduler_service.refresh()

        asyncio.create_task(
            _best_effort_sync_m365_email_domains(company_id),
            name=f"sync_m365_email_domains_{company_id}",
        )

        if return_to_company_edit:
            return _company_edit_redirect(
                company_id=company_id,
                success="Microsoft 365 enterprise app provisioned successfully.",
            )
        return RedirectResponse(url="/m365", status_code=status.HTTP_303_SEE_OTHER)

    # ── Standard connect/token-refresh flow ────────────────────────────────
    credentials = await m365_service.get_credentials(company_id)
    if not credentials:
        return flash_redirect("/m365", "missing credentials", "error")
    token_endpoint = f"https://login.microsoftonline.com/{credentials['tenant_id']}/oauth2/v2.0/token"
    redirect_uri = _build_m365_redirect_uri(request)
    data = {
        "client_id": credentials["client_id"],
        "client_secret": credentials.get("client_secret") or "",
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": m365_service.CONNECT_SCOPE,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(token_endpoint, data=data)
    if response.status_code != 200:
        log_error(
            "Microsoft 365 authorization failed",
            status=response.status_code,
            body=response.text,
        )
        return flash_redirect("/m365", "authorization failed", "error")
    payload = response.json()
    refresh_token = payload.get("refresh_token")
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    expires_at = None
    if isinstance(expires_in, (int, float)):
        expires_at = datetime.utcnow() + timedelta(seconds=float(expires_in))
    await m365_repo.update_tokens(
        company_id=company_id,
        refresh_token=encrypt_secret(refresh_token) if refresh_token else None,
        access_token=None,
        token_expires_at=None,
    )
    # Best-effort: grant any newly-required app role assignments (e.g. the
    # permissions added for mailbox sync) using the admin's delegated token.
    # This ensures existing deployments pick up new permissions automatically
    # when an administrator re-runs "Authorize portal access".
    if access_token:
        new_permissions_granted = await m365_service.try_grant_missing_permissions(
            company_id=company_id,
            access_token=access_token,
        )
        if new_permissions_granted:
            log_info(
                "Granted missing M365 permissions via connect flow",
                company_id=company_id,
            )
    log_info("Microsoft 365 OAuth callback processed", company_id=company_id)
    asyncio.create_task(
        _best_effort_sync_m365_email_domains(company_id),
        name=f"sync_m365_email_domains_{company_id}",
    )
    return RedirectResponse(url="/m365", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/search/", response_class=HTMLResponse)
async def search_by_phone_number(request: Request):
    """
    Search for tickets by requester's phone number.
    Example: /search/?phoneNumber=%2B61412345678
    """
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return redirect
    
    # Get phone number from query parameter
    phone_number = request.query_params.get("phoneNumber", "").strip()
    
    if not phone_number:
        # No phone number provided, redirect to tickets page
        return RedirectResponse(url="/tickets", status_code=status.HTTP_303_SEE_OTHER)
    
    # Search for tickets by requester's phone number within the authenticated user's scope
    available_companies = await company_access.list_accessible_companies(user)
    available_company_ids: list[int] = []
    for entry in available_companies:
        company_id = entry.get("company_id")
        try:
            available_company_ids.append(int(company_id))
        except (TypeError, ValueError):
            continue

    active_company_id = getattr(request.state, "active_company_id", None)
    active_company_ids: list[int] = []
    if active_company_id is not None:
        try:
            active_company_ids = [int(active_company_id)]
        except (TypeError, ValueError):
            active_company_ids = []
    if not active_company_ids:
        active_company_ids = available_company_ids

    # Search for tickets by requester's phone number
    try:
        tickets = await tickets_repo.list_tickets_by_requester_phone(
            phone_number,
            limit=_PHONE_SEARCH_LIMIT,
            user_id=user.get("id"),
            company_ids=active_company_ids or None,
        )
    except Exception as exc:
        log_error(
            "Error searching tickets by phone number",
            exc=exc,
            event="tickets.phone_search_failed",
            request_id=_get_request_id(request),
            path=request.url.path,
            user_id=user.get("id"),
        )
        # On error, redirect to tickets page with error message
        return flash_redirect("/tickets", "Failed to search tickets by phone number", "error")
    
    if not tickets:
        # No tickets found, redirect to tickets page with a message
        return flash_redirect("/tickets", f"No tickets found for phone number {phone_number}", "error")
    
    if len(tickets) == 1:
        # Exactly one ticket found, redirect directly to it
        ticket_id = tickets[0].get("id")
        if ticket_id is None:
            # Handle case where ticket doesn't have an ID (defensive)
            return flash_redirect("/tickets", "Invalid ticket data received", "error")
        return RedirectResponse(
            url=f"/tickets/{ticket_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    # Multiple tickets found, redirect to tickets page with search
    # We'll use the phone number as a search term
    search_param = quote(phone_number)
    return RedirectResponse(
        url=f"/tickets?q={search_param}",
        status_code=status.HTTP_303_SEE_OTHER
    )






@app.head("/admin/service-status", response_class=HTMLResponse)
@app.get("/admin/service-status", response_class=HTMLResponse)
async def admin_service_status_page(request: Request):
    user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    services = await service_status_service.list_services(include_inactive=True)
    summary = service_status_service.summarise_services(services)
    companies = await company_repo.list_companies()
    service_id_param = request.query_params.get("serviceId")
    editing_service = None
    if service_id_param:
        try:
            editing_service = await service_status_service.get_service(int(service_id_param))
        except (TypeError, ValueError):
            editing_service = None
    status_lookup = {entry["value"]: entry for entry in service_status_service.STATUS_DEFINITIONS}
    company_lookup = {
        int(company["id"]): company.get("name")
        for company in companies
        if company.get("id") is not None
    }
    return await _render_template(
        "admin/service_status.html",
        request,
        user,
        extra={
            "title": "Service status",
            "service_status_entries": services,
            "service_status_summary": summary,
            "service_status_definitions": service_status_service.STATUS_DEFINITIONS,
            "service_status_lookup": status_lookup,
            "company_options": companies,
            "service_status_company_lookup": company_lookup,
            "service_status_editing": editing_service,
            "service_status_default": service_status_service.DEFAULT_STATUS,
        },
    )


def _extract_service_status_form(form: FormData) -> tuple[dict[str, Any], list[int]]:
    payload = {
        "name": form.get("name"),
        "description": form.get("description"),
        "status": form.get("status") or service_status_service.DEFAULT_STATUS,
        "status_message": form.get("status_message"),
        "display_order": form.get("display_order"),
        "is_active": bool(form.get("is_active")),
        # AI lookup fields
        "ai_lookup_enabled": bool(form.get("ai_lookup_enabled")),
        "ai_lookup_url": form.get("ai_lookup_url"),
        "ai_lookup_prompt": form.get("ai_lookup_prompt"),
        "ai_lookup_model_override": form.get("ai_lookup_model_override"),
        "ai_lookup_frequency_operational": form.get("ai_lookup_frequency_operational"),
        "ai_lookup_frequency_degraded": form.get("ai_lookup_frequency_degraded"),
        "ai_lookup_frequency_partial_outage": form.get("ai_lookup_frequency_partial_outage"),
        "ai_lookup_frequency_outage": form.get("ai_lookup_frequency_outage"),
        "ai_lookup_frequency_maintenance": form.get("ai_lookup_frequency_maintenance"),
    }
    # Handle tags - can be comma-separated string
    tags_input = form.get("tags")
    if tags_input:
        payload["tags"] = tags_input
    company_ids = form.getlist("companyIds") if hasattr(form, "getlist") else []
    return payload, company_ids


@app.post("/admin/service-status", response_class=HTMLResponse)
async def admin_create_service_status(request: Request):
    user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    form = await request.form()
    payload, company_ids = _extract_service_status_form(form)
    try:
        await service_status_service.create_service(
            payload,
            company_ids=company_ids,
            updated_by=int(user.get("id")) if user.get("id") else None,
        )
    except ValueError as exc:
        return flash_redirect("/admin/service-status", str(exc), "error")
    return flash_redirect("/admin/service-status", "Service created.", "success")


@app.post("/admin/service-status/{service_id}", response_class=HTMLResponse)
async def admin_update_service_status(request: Request, service_id: int):
    user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    form = await request.form()
    payload, company_ids = _extract_service_status_form(form)
    try:
        updated = await service_status_service.update_service(
            service_id,
            payload,
            company_ids=company_ids,
            updated_by=int(user.get("id")) if user.get("id") else None,
        )
    except ValueError as exc:
        return flash_redirect(f"/admin/service-status?serviceId={service_id}", str(exc), "error")
    if not updated:
        return flash_redirect("/admin/service-status", "Service not found.", "error")
    return flash_redirect("/admin/service-status", "Service updated.", "success")


@app.post("/admin/service-status/{service_id}/delete", response_class=HTMLResponse)
async def admin_delete_service_status(request: Request, service_id: int):
    user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    try:
        await service_status_service.delete_service(service_id)
    except Exception as exc:  # pragma: no cover - defensive
        return flash_redirect("/admin/service-status", str(exc), "error")
    return flash_redirect("/admin/service-status", "Service deleted.", "success")


@app.post("/admin/service-status/{service_id}/refresh-tags", response_class=HTMLResponse)
async def admin_refresh_service_tags(request: Request, service_id: int):
    user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    try:
        await service_status_service.refresh_service_tags(service_id)
    except ValueError as exc:
        return flash_redirect(f"/admin/service-status?serviceId={service_id}", str(exc), "error")
    except Exception as exc:  # pragma: no cover - defensive
        return flash_redirect(f"/admin/service-status?serviceId={service_id}", "Failed to refresh tags.", "error")
    return flash_redirect(f"/admin/service-status?serviceId={service_id}", "Tags refreshed.", "success")


async def _admin_service_status_check_now_handler(request: Request, service_id: int):
    user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    try:
        result = await service_status_service.run_ai_lookup_for_service(service_id)
    except Exception as exc:
        log_error(
            "Service status AI lookup raised an unexpected error",
            service_id=service_id,
            error=str(exc),
        )
        url = f"/admin/service-status?serviceId={service_id}"
        return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    if result.get("error"):
        return flash_redirect(f"/admin/service-status?serviceId={service_id}", result["error"], "error")
    msg = "AI lookup completed."
    if result.get("changed"):
        msg = "AI lookup completed — status updated."
    return flash_redirect(f"/admin/service-status?serviceId={service_id}", msg, "success")


@app.post("/admin/service-status/{service_id}/check-now", response_class=HTMLResponse)
@app.post("/admin/service-status/{service_id}/check_now", response_class=HTMLResponse)
@app.post("/admin/service-status/check-now/{service_id}", response_class=HTMLResponse)
async def admin_service_status_check_now(request: Request, service_id: int):
    """
    Trigger an immediate AI lookup for a service.

    Multiple route aliases are kept for backward compatibility with earlier UI
    paths and bookmarked/admin-proxied URLs.
    """
    return await _admin_service_status_check_now_handler(request, service_id)


@app.get("/admin/profile", response_class=HTMLResponse)
async def admin_profile_page(request: Request):
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return redirect

    membership = getattr(request.state, "active_membership", None)
    if membership is None:
        active_company_id = getattr(request.state, "active_company_id", None)
        if active_company_id is not None:
            try:
                membership = await user_company_repo.get_user_company(user["id"], int(active_company_id))
            except Exception:  # pragma: no cover - defensive protection against membership lookup failures
                membership = None
            request.state.active_membership = membership

    if not _membership_menu_can(user, membership, "menu.admin.profile"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile access required")

    try:
        devices = await auth_repo.get_totp_authenticators(user["id"])
    except Exception:  # pragma: no cover - defensive logging for profile rendering
        devices = []

    totp_devices: list[dict[str, Any]] = []
    for device in devices:
        identifier = device.get("id")
        if identifier is None:
            continue
        name = device.get("name") or "Authenticator"
        try:
            identifier = int(identifier)
        except (TypeError, ValueError):
            continue
        totp_devices.append({"id": identifier, "name": name})

    totp_devices.sort(key=lambda entry: entry["name"].lower())

    context = await _build_base_context(
        request,
        user,
        extra={
            "title": "My profile",
            "profile_membership": membership,
            "profile_show_technician_tools": _can_edit_profile_technician_tools(user, membership),
            "profile_totp_devices": totp_devices,
        },
    )
    return templates.TemplateResponse(context["request"], "admin/profile.html", context)








@app.post("/api/tickets/{ticket_id}/requester/mobile", response_class=JSONResponse)
async def attach_ticket_requester_mobile(request: Request, ticket_id: int):
    _, redirect = await _require_authenticated_user(request)
    if redirect:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    ticket = await tickets_repo.get_ticket(ticket_id)
    if not ticket or ticket.get("requester_staff_id") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket requester contact not found")

    payload = await request.json()
    phone = str(payload.get("phone") or "").strip() if isinstance(payload, dict) else ""
    normalized = re.sub(r"[^0-9+]", "", phone)
    if not re.fullmatch(r"\+?[0-9]{3,15}", normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid phone number")

    staff_id = int(ticket["requester_staff_id"])
    if not await staff_repo.get_staff_by_id(staff_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket requester contact not found")
    await staff_repo.update_mobile_phone(staff_id, phone)
    return JSONResponse({"ok": True, "staff_id": staff_id, "mobile_phone": phone})


@app.get("/api/rag/relationships/metrics", response_class=JSONResponse)
async def rag_relationship_metrics():
    from app.repositories import rag_relationships as rel_repo

    return JSONResponse(await rel_repo.metrics())


@app.get("/admin/rag", response_class=HTMLResponse)
async def admin_rag_page(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    return await _render_template(
        "admin/rag.html",
        request,
        current_user,
        extra={"title": "RAG Index"},
    )


@app.get("/admin/impersonation", response_class=HTMLResponse)
async def admin_impersonation_page(
    request: Request,
):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    return await _render_impersonation_dashboard(
        request,
        current_user,
    )


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    active_users = await user_repo.list_active_users_for_admin()
    return await _render_template(
        "admin/users.html",
        request,
        current_user,
        extra={"title": "Users", "users": active_users},
    )


@app.get("/admin/sessions", response_class=HTMLResponse)
async def admin_sessions_page(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    active_sessions = await access_activity_repo.list_active_user_sessions(limit=500)
    recent_connections = await access_activity_repo.list_recent_connection_activity(limit=1000)

    for session in active_sessions:
        session["created_at_iso"] = _to_iso(session.get("created_at"))
        session["last_seen_at_iso"] = _to_iso(session.get("last_seen_at"))
        session["expires_at_iso"] = _to_iso(session.get("expires_at"))

    for connection in recent_connections:
        connection["activity_at_iso"] = _to_iso(connection.get("activity_at"))

    return await _render_template(
        "admin/sessions.html",
        request,
        current_user,
        extra={
            "title": "Sessions",
            "active_sessions": active_sessions,
            "recent_connections": recent_connections,
        },
    )


@app.post("/admin/users/{user_id}/{action}", response_class=HTMLResponse)
async def admin_users_action(request: Request, user_id: int, action: str):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    if action not in {"deactivate", "delete"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown user action"
        )
    if int(current_user["id"]) == user_id:
        return flash_redirect(
            "/admin/users",
            "You cannot deactivate or delete your own account.",
            "error",
        )

    target = await user_repo.get_user_by_id(user_id)
    if not target or not bool(target.get("is_active")):
        return flash_redirect("/admin/users", "Active user not found.", "error")
    if target.get("is_super_admin") and await user_repo.count_active_super_admins() <= 1:
        return flash_redirect("/admin/users", "The last active super admin cannot be removed.", "error")

    from app.services import audit as audit_service

    if action == "deactivate":
        updated = await user_repo.update_user(user_id, is_active=0)
        await audit_service.record(
            action="user.deactivate",
            request=request,
            user_id=int(current_user["id"]),
            entity_type="user",
            entity_id=user_id,
            before=target,
            after=updated,
        )
        message = f"Deactivated {target.get('email') or 'user account'}."
    else:
        try:
            await user_repo.delete_user(user_id)
        except Exception as exc:
            log_error("Failed to delete user account", user_id=user_id, error=str(exc))
            return flash_redirect(
                "/admin/users",
                "This user could not be deleted because related records still exist. Deactivate the account instead.",
                "error",
            )
        await audit_service.record(
            action="user.delete",
            request=request,
            user_id=int(current_user["id"]),
            entity_type="user",
            entity_id=user_id,
            before=target,
            after=None,
        )
        message = f"Deleted {target.get('email') or 'user account'}."
    return flash_redirect("/admin/users", message, "success")


@app.post("/admin/impersonation", response_class=HTMLResponse)
async def admin_impersonation_start(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    form = await request.form()
    target_value = form.get("userId") or form.get("user_id")
    try:
        target_user_id = int(str(target_value))
    except (TypeError, ValueError):
        return await _render_impersonation_dashboard(
            request,
            current_user,
            error_message="Select a valid user to impersonate.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    actor_session = getattr(request.state, "session", None)
    if actor_session is None:
        actor_session = await session_manager.load_session(request)
    if actor_session is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        _, impersonated_session = await impersonation_service.start_impersonation(
            request=request,
            actor_user=current_user,
            actor_session=actor_session,
            target_user_id=target_user_id,
        )
    except impersonation_service.SelfImpersonationError:
        error_message = "You cannot impersonate your own account."
        status_code = status.HTTP_400_BAD_REQUEST
    except impersonation_service.AlreadyImpersonatingError:
        error_message = "An impersonation session is already active."
        status_code = status.HTTP_409_CONFLICT
    except impersonation_service.NotImpersonatableError as exc:
        error_message = str(exc)
        status_code = status.HTTP_403_FORBIDDEN
    else:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        session_manager.apply_session_cookies(response, impersonated_session)
        request.state.session = impersonated_session
        request.state.active_company_id = impersonated_session.active_company_id
        request.state.impersonator_user_id = impersonated_session.impersonator_user_id
        request.state.impersonator_session_id = impersonated_session.impersonator_session_id
        return response

    return await _render_impersonation_dashboard(
        request,
        current_user,
        error_message=_sanitize_message(error_message),
        status_code=status_code,
    )
















































@app.get("/admin/roles", response_class=HTMLResponse)
async def admin_roles(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    roles_list = await role_repo.list_roles()
    extra = {
        "title": "Role management",
        "roles": roles_list,
        "menu_permission_catalogue": catalogue_for_api(),
    }
    return await _render_template("admin/roles.html", request, current_user, extra=extra)


@app.get("/admin/cron-calendar", response_class=HTMLResponse)
async def admin_cron_calendar(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    extra = {"title": "Cron Calendar"}
    return await _render_template("admin/cron_calendar.html", request, current_user, extra=extra)


@app.get("/admin/automation", response_class=HTMLResponse)
async def admin_automation(request: Request, show_inactive: bool = Query(default=False)):
    return RedirectResponse(url="/admin/scheduled-tasks", status_code=status.HTTP_301_MOVED_PERMANENTLY)


@app.get("/admin/scheduled-tasks", response_class=HTMLResponse)
async def admin_scheduled_tasks(
    request: Request,
    show_inactive: bool = Query(default=False),
):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    tasks = await scheduled_tasks_repo.list_tasks(include_inactive=show_inactive)
    companies = await company_repo.list_companies()

    company_lookup: dict[int, str] = {}
    for company in companies:
        try:
            company_id = int(company.get("id")) if company.get("id") is not None else None
        except (TypeError, ValueError):
            company_id = None
        if company_id is None:
            continue
        company_lookup[company_id] = str(company.get("name") or f"Company #{company_id}")

    prepared_tasks: list[dict[str, Any]] = []
    missing_company_ids: set[int] = set()
    for task in tasks:
        serialised_task = _serialise_mapping(task)
        serialised_task["last_run_iso"] = _to_iso(task.get("last_run_at"))
        next_run = cron_calendar_service.calculate_next_run(
            task, timezone_name=settings.default_timezone
        )
        serialised_task["next_run_iso"] = _to_iso(next_run)
        raw_company_id = task.get("company_id")
        company_key: int | None = None
        if raw_company_id is not None:
            try:
                company_key = int(raw_company_id)
            except (TypeError, ValueError):
                company_key = None
        if company_key is None:
            serialised_task["company_name"] = "All companies"
            serialised_task["company_edit_url"] = None
        else:
            company_name = company_lookup.get(company_key)
            if not company_name:
                company_name = f"Company #{company_key}"
                missing_company_ids.add(company_key)
            serialised_task["company_name"] = company_name
            serialised_task["company_edit_url"] = f"/admin/companies/{company_key}/edit"
        prepared_tasks.append(serialised_task)

    try:
        all_modules = await modules_service.list_modules()
        disabled_module_slugs = {m["slug"] for m in all_modules if not m.get("enabled")}
    except Exception:  # pragma: no cover - defensive fallback
        disabled_module_slugs = set()
    disabled_commands_global: set[str] = set()
    for mod_slug, cmds in COMMANDS_BY_MODULE.items():
        if mod_slug in disabled_module_slugs:
            disabled_commands_global.update(cmds)

    available_commands = (
        "update_mac_vendors", "sync_staff", "sync_m365_data", "sync_m365_licenses",
        "sync_m365_contacts", "refresh_m365_consent_status", "unbill_time_entries",
        "create_scheduled_ticket", "rag_index_start",
        "rag_index_stop", "rag_matching_pause", "rag_matching_resume",
        "rag_cleanup_stale_matches",
    )
    command_options = [
        {"value": command, "label": _scheduled_task_command_label(command)}
        for command in available_commands
    ]
    command_options = [o for o in command_options if o["value"] not in disabled_commands_global]
    existing_commands = {task.get("command") for task in tasks if task.get("command")}
    for command in sorted(existing_commands):
        if command and command not in {option["value"] for option in command_options} and command not in disabled_commands_global:
            command_options.append(
                {"value": str(command), "label": _scheduled_task_command_label(str(command))}
            )
    command_options.sort(key=lambda option: option["label"].casefold())

    company_options = [{"value": "", "label": "All companies"}]
    for cid, cname in sorted(company_lookup.items(), key=lambda item: item[1].lower()):
        company_options.append({"value": str(cid), "label": cname})
    for cid in sorted(missing_company_ids):
        company_options.append({"value": str(cid), "label": f"Company #{cid}"})

    bulk_company_options = [
        {"value": option["value"], "label": option["label"]}
        for option in company_options
        if option.get("value")
    ]

    extra = {
        "title": "Scheduled Tasks",
        "tasks": prepared_tasks,
        "show_inactive": show_inactive,
        "upgrade_status": system_state_service.get_upgrade_status(),
        "command_options": command_options,
        "company_options": company_options,
        "bulk_company_options": bulk_company_options,
    }
    return await _render_template("admin/scheduled_tasks.html", request, current_user, extra=extra)



@app.post("/admin/scheduled-tasks/bulk-create", response_class=HTMLResponse)
async def admin_bulk_create_scheduled_tasks(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    form = await request.form()
    command = str(form.get("command") or "").strip()
    cron = str(form.get("cron") or "").strip()
    raw_company_ids = form.getlist("companyIds")
    description = str(form.get("description") or "").strip() or None

    if command == "create_scheduled_ticket":
        json_payload = str(form.get("jsonPayload") or "").strip()
        if not json_payload:
            return flash_redirect("/admin/scheduled-tasks", "JSON payload is required for scheduled ticket tasks.", "error")
        try:
            json.loads(json_payload)
        except json.JSONDecodeError:
            return flash_redirect("/admin/scheduled-tasks", "JSON payload is not valid JSON.", "error")
        description = json_payload

    if not command:
        return flash_redirect("/admin/scheduled-tasks", "Select a task option to bulk create.", "error")

    cron_fields = cron.split()
    start_minute: int | None = None
    start_hour: int | None = None
    if cron:
        if len(cron_fields) not in {5, 6}:
            return flash_redirect("/admin/scheduled-tasks", "Enter a valid five- or six-field cron expression.", "error")
        try:
            start_minute = int(cron_fields[0])
            start_hour = int(cron_fields[1])
        except (TypeError, ValueError):
            return flash_redirect("/admin/scheduled-tasks", "Bulk create requires numeric minute and hour cron fields.", "error")
        if start_minute < 0 or start_minute > 59 or start_hour < 0 or start_hour > 23:
            return flash_redirect("/admin/scheduled-tasks", "Cron start time must be between 00:00 and 23:59 UTC.", "error")

    company_ids: list[int] = []
    seen: set[int] = set()
    for raw in raw_company_ids:
        try:
            company_id = int(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if company_id <= 0 or company_id in seen:
            continue
        seen.add(company_id)
        company_ids.append(company_id)

    if not company_ids:
        return flash_redirect("/admin/scheduled-tasks", "Select at least one active company.", "error")

    companies = await company_repo.list_companies()
    active_company_lookup: dict[int, str] = {}
    for company in companies:
        try:
            cid = int(company.get("id")) if company.get("id") is not None else None
        except (TypeError, ValueError):
            cid = None
        if cid is not None:
            active_company_lookup[cid] = str(company.get("name") or f"Company #{cid}")

    invalid_company_ids = [cid for cid in company_ids if cid not in active_company_lookup]
    if invalid_company_ids:
        return flash_redirect("/admin/scheduled-tasks", "One or more selected companies are no longer active.", "error")

    try:
        max_retries = int(str(form.get("maxRetries") or "12").strip())
        retry_backoff_seconds = int(str(form.get("retryBackoffSeconds") or "300").strip())
    except (TypeError, ValueError):
        return flash_redirect("/admin/scheduled-tasks", "Retry settings must be numeric.", "error")
    if max_retries < 0:
        return flash_redirect("/admin/scheduled-tasks", "Max retries must be zero or a positive number.", "error")
    if retry_backoff_seconds < 30:
        return flash_redirect("/admin/scheduled-tasks", "Retry backoff must be at least 30 seconds.", "error")

    command_label = TASK_COMMAND_LABELS.get(command, command)
    active = form.get("active") is not None
    exclude_from_calendar = form.get("excludeFromCalendar") is not None
    created_count = 0
    for offset, company_id in enumerate(company_ids):
        if start_hour is None or start_minute is None:
            task_cron = _random_daily_cron()
        else:
            fields = list(cron_fields)
            total_minutes = start_hour * 60 + start_minute + offset
            fields[0] = str(total_minutes % 60)
            fields[1] = str((total_minutes // 60) % 24)
            task_cron = " ".join(fields)
        company_name = active_company_lookup[company_id]
        await scheduled_tasks_repo.create_task(
            name=f"{company_name} — {command_label}",
            command=command,
            cron=task_cron,
            company_id=company_id,
            description=description,
            active=active,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            exclude_from_calendar=exclude_from_calendar,
        )
        created_count += 1

    if created_count:
        await scheduler_service.refresh()

    log_info(
        "Scheduled tasks bulk created",
        created_count=created_count,
        command=command,
        start_cron=cron,
        created_by=current_user.get("id") if current_user else None,
        company_ids=company_ids,
    )

    noun = "task" if created_count == 1 else "tasks"
    show_inactive_param = "1" if form.get("show_inactive") else ""
    base_url = "/admin/scheduled-tasks"
    redirect_url = f"{base_url}?show_inactive={show_inactive_param}" if show_inactive_param else base_url
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    if start_hour is None or start_minute is None:
        success_message = f"Created {created_count} scheduled {noun} at random daily times."
    else:
        success_message = f"Created {created_count} scheduled {noun} from {start_hour:02d}:{start_minute:02d} UTC."
    set_flash(response, success_message, "success")
    return response


@app.post("/admin/scheduled-tasks/bulk-delete", response_class=HTMLResponse)
async def admin_bulk_delete_scheduled_tasks(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    form = await request.form()
    raw_ids = form.getlist("taskIds")
    task_ids: list[int] = []
    seen: set[int] = set()
    for raw in raw_ids:
        try:
            identifier = int(raw)
        except (TypeError, ValueError):
            continue
        if identifier <= 0 or identifier in seen:
            continue
        seen.add(identifier)
        task_ids.append(identifier)

    if not task_ids:
        return flash_redirect("/admin/scheduled-tasks", "Select at least one task to delete.", "error")

    try:
        deleted_count = await scheduled_tasks_repo.delete_tasks(task_ids)
        await scheduler_service.refresh()
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error(
            "Failed to bulk delete scheduled tasks",
            task_ids=task_ids,
            error=str(exc),
        )
        return flash_redirect("/admin/scheduled-tasks", "Unable to delete the selected tasks. Please try again.", "error")

    log_info(
        "Scheduled tasks bulk deleted",
        deleted_count=deleted_count,
        deleted_by=current_user.get("id") if current_user else None,
        task_ids=task_ids,
    )

    message_suffix = "task" if deleted_count == 1 else "tasks"
    redirect_message = f"Deleted {deleted_count} {message_suffix}."
    if deleted_count < len(task_ids):
        redirect_message = f"Deleted {deleted_count} {message_suffix}. Some selected tasks were not found."

    show_inactive_raw = form.get("show_inactive")
    show_inactive_param = "1" if show_inactive_raw else ""
    base_url = "/admin/scheduled-tasks"
    redirect_url = f"{base_url}?show_inactive={show_inactive_param}" if show_inactive_param else base_url
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    set_flash(response, redirect_message, "success")
    return response


@app.post("/admin/scheduled-tasks/bulk-rename", response_class=HTMLResponse)
async def admin_bulk_rename_scheduled_tasks(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    form = await request.form()
    raw_ids = form.getlist("taskIds")
    task_ids: list[int] = []
    seen: set[int] = set()
    for raw in raw_ids:
        try:
            identifier = int(raw)
        except (TypeError, ValueError):
            continue
        if identifier <= 0 or identifier in seen:
            continue
        seen.add(identifier)
        task_ids.append(identifier)

    if not task_ids:
        return flash_redirect("/admin/scheduled-tasks", "Select at least one task to rename.", "error")

    companies = await company_repo.list_companies()
    company_lookup: dict[int, str] = {}
    for company in companies:
        try:
            cid = int(company.get("id")) if company.get("id") is not None else None
        except (TypeError, ValueError):
            cid = None
        if cid is None:
            continue
        company_lookup[cid] = str(company.get("name") or f"Company #{cid}")

    renamed_count = 0
    for task_id in task_ids:
        task = await scheduled_tasks_repo.get_task(task_id)
        if not task:
            continue
        raw_company_id = task.get("company_id")
        company_key: int | None = None
        if raw_company_id is not None:
            try:
                company_key = int(raw_company_id)
            except (TypeError, ValueError):
                company_key = None
        if company_key is None:
            company_label = "All companies"
        else:
            company_label = company_lookup.get(company_key, f"Company #{company_key}")

        command = str(task.get("command") or "")
        command_label = TASK_COMMAND_LABELS.get(command, command)

        new_name = f"{company_label} \u2014 {command_label}"
        await scheduled_tasks_repo.rename_task(task_id, new_name)
        renamed_count += 1

    log_info(
        "Scheduled tasks bulk renamed",
        renamed_count=renamed_count,
        renamed_by=current_user.get("id") if current_user else None,
        task_ids=task_ids,
    )

    message_suffix = "task" if renamed_count == 1 else "tasks"
    redirect_message = f"Renamed {renamed_count} {message_suffix}."

    show_inactive_raw = form.get("show_inactive")
    show_inactive_param = "1" if show_inactive_raw else ""
    base_url = "/admin/scheduled-tasks"
    redirect_url = f"{base_url}?show_inactive={show_inactive_param}" if show_inactive_param else base_url
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    set_flash(response, redirect_message, "success")
    return response


@app.post("/admin/scheduled-tasks/bulk-redistribute", response_class=HTMLResponse)
async def admin_bulk_redistribute_scheduled_tasks(request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    form = await request.form()
    raw_ids = form.getlist("taskIds")
    task_ids: list[int] = []
    seen: set[int] = set()
    for raw in raw_ids:
        try:
            identifier = int(raw)
        except (TypeError, ValueError):
            continue
        if identifier <= 0 or identifier in seen:
            continue
        seen.add(identifier)
        task_ids.append(identifier)

    if not task_ids:
        return flash_redirect("/admin/scheduled-tasks", "Select at least one task to redistribute.", "error")

    try:
        hour = int(str(form.get("redistributeHour") or "").strip())
    except (TypeError, ValueError):
        return flash_redirect("/admin/scheduled-tasks", "Enter an hour between 0 and 23.", "error")

    if hour < 0 or hour > 23:
        return flash_redirect("/admin/scheduled-tasks", "Enter an hour between 0 and 23.", "error")

    try:
        minute_offset = int(str(form.get("redistributeOffset") or "0").strip())
    except (TypeError, ValueError):
        return flash_redirect("/admin/scheduled-tasks", "Enter a starting minute offset between 0 and 59.", "error")

    if minute_offset < 0 or minute_offset > 59:
        return flash_redirect("/admin/scheduled-tasks", "Enter a starting minute offset between 0 and 59.", "error")

    redistributed_count = 0
    for offset, task_id in enumerate(task_ids):
        task = await scheduled_tasks_repo.get_task(task_id)
        if not task:
            continue
        fields = str(task.get("cron") or "").split()
        if len(fields) < 5:
            log_warning(
                "Skipped scheduled task cron redistribution due to invalid cron",
                task_id=task_id,
                cron=task.get("cron"),
            )
            continue
        total_minutes = minute_offset + offset
        scheduled_hour = (hour + (total_minutes // 60)) % 24
        scheduled_minute = total_minutes % 60
        fields[0] = str(scheduled_minute)
        fields[1] = str(scheduled_hour)
        await scheduled_tasks_repo.update_task_cron(task_id, " ".join(fields))
        redistributed_count += 1

    if redistributed_count:
        await scheduler_service.refresh()

    log_info(
        "Scheduled tasks bulk redistributed",
        redistributed_count=redistributed_count,
        redistribute_hour=hour,
        redistribute_offset=minute_offset,
        redistributed_by=current_user.get("id") if current_user else None,
        task_ids=task_ids,
    )

    message_suffix = "task" if redistributed_count == 1 else "tasks"
    redirect_message = f"Redistributed {redistributed_count} {message_suffix} to run from {hour:02d}:{minute_offset:02d} UTC."
    if redistributed_count < len(task_ids):
        redirect_message = f"{redirect_message} Some selected tasks were not found or had invalid cron expressions."

    show_inactive_raw = form.get("show_inactive")
    show_inactive_param = "1" if show_inactive_raw else ""
    base_url = "/admin/scheduled-tasks"
    redirect_url = f"{base_url}?show_inactive={show_inactive_param}" if show_inactive_param else base_url
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    set_flash(response, redirect_message, "success")
    return response

# ---------------------------------------------------------------------------



























































































@app.get("/admin/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs(
    request: Request,
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    limit = max(1, min(limit, 500))
    offset = max(0, int(offset))

    def _parse_filter_dt(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    since_dt = _parse_filter_dt(since)
    until_dt = _parse_filter_dt(until)

    filter_kwargs = dict(
        entity_type=entity_type or None,
        entity_id=entity_id,
        user_id=user_id,
        action=(action or "").strip() or None,
        request_id=(request_id or "").strip() or None,
        ip_address=(ip_address or "").strip() or None,
        since=since_dt,
        until=until_dt,
        search=(search or "").strip() or None,
    )
    logs = await audit_repo.list_audit_logs(
        **filter_kwargs,
        limit=limit,
        offset=offset,
    )
    total = await audit_repo.count_audit_logs(**filter_kwargs)
    available_actions = await audit_repo.list_distinct_actions()

    for log in logs:
        log["created_at_iso"] = _to_iso(log.get("created_at"))
        log["diff_rows"] = _build_audit_diff_rows(
            log.get("previous_value"), log.get("new_value")
        )

    extra = {
        "title": "Audit trail",
        "logs": logs,
        "available_actions": available_actions,
        "total": total,
        "filters": {
            "entity_type": entity_type or "",
            "entity_id": entity_id or "",
            "user_id": user_id or "",
            "action": action or "",
            "request_id": request_id or "",
            "ip_address": ip_address or "",
            "since": since or "",
            "until": until or "",
            "search": search or "",
            "limit": limit,
            "offset": offset,
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_prev": offset > 0,
            "has_next": (offset + limit) < total,
            "prev_offset": max(0, offset - limit),
            "next_offset": offset + limit,
        },
    }
    return await _render_template("admin/audit_logs.html", request, current_user, extra=extra)


def _build_audit_diff_rows(previous: Any, current: Any) -> list[dict[str, Any]]:
    """Convert previous/new JSON snapshots into a per-field table for the UI.

    Returns a list of ``{"field", "previous", "current", "changed"}`` entries
    sorted by field name. The diff helper already filtered to changed fields
    when callers used ``audit.record``, but we still flag rows so legacy
    entries (which stored full snapshots) render with a visual hint.
    """

    if isinstance(previous, str):
        try:
            previous = json.loads(previous)
        except (TypeError, ValueError):
            previous = {"value": previous}
    if isinstance(current, str):
        try:
            current = json.loads(current)
        except (TypeError, ValueError):
            current = {"value": current}

    if not isinstance(previous, dict) and not isinstance(current, dict):
        if previous is None and current is None:
            return []
        return [
            {
                "field": "value",
                "previous": previous,
                "current": current,
                "changed": previous != current,
            }
        ]

    keys: set[str] = set()
    if isinstance(previous, dict):
        keys.update(str(k) for k in previous.keys())
    if isinstance(current, dict):
        keys.update(str(k) for k in current.keys())

    rows: list[dict[str, Any]] = []
    for key in sorted(keys):
        prev_value = previous.get(key) if isinstance(previous, dict) else None
        curr_value = current.get(key) if isinstance(current, dict) else None
        rows.append(
            {
                "field": key,
                "previous": prev_value,
                "current": curr_value,
                "changed": prev_value != curr_value,
            }
        )
    return rows


@app.get("/admin/change-log", response_class=HTMLResponse)
async def admin_change_log(
    request: Request,
    change_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    limit = max(1, min(limit, 500))
    available_types = await change_log_repo.list_change_types()

    selected_type: str | None = None
    raw_change_type = (change_type or "").strip()
    if raw_change_type:
        lowered = raw_change_type.lower()
        for candidate in available_types:
            if candidate.lower() == lowered:
                selected_type = candidate
                break

    entries = await change_log_repo.list_change_log_entries(
        change_type=selected_type,
        limit=limit,
    )
    for entry in entries:
        entry["occurred_at_iso"] = _to_iso(entry.get("occurred_at_utc"))

    extra = {
        "title": "Change log",
        "change_entries": entries,
        "change_types": available_types,
        "filters": {
            "change_type": raw_change_type,
            "selected_change_type": selected_type.lower() if selected_type else "",
            "limit": limit,
        },
    }
    return await _render_template("admin/change_log.html", request, current_user, extra=extra)




@app.get("/admin/tag-exclusions", response_class=HTMLResponse)
async def admin_tag_exclusions_page(
    request: Request,
):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    
    context = await _build_base_context(
        request,
        current_user,
        extra={

        },
    )
    return templates.TemplateResponse(
        context["request"],
        "admin/tag_exclusions.html",
        context,
    )


async def _prepare_kb_editor_options() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    users_task = asyncio.create_task(user_repo.list_users())
    companies_task = asyncio.create_task(company_repo.list_companies())
    users, companies = await asyncio.gather(users_task, companies_task)

    user_options: list[dict[str, Any]] = []
    for user in users:
        user_id = user.get("id")
        if user_id is None:
            continue
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            continue
        first_name = (user.get("first_name") or "").strip()
        last_name = (user.get("last_name") or "").strip()
        name_parts = [part for part in (first_name, last_name) if part]
        full_name = " ".join(name_parts)
        email = (user.get("email") or "").strip()
        if full_name and email:
            label = f"{full_name} ({email})"
        elif full_name:
            label = full_name
        elif email:
            label = email
        else:
            label = f"User {user_id_int}"
        user_options.append({"id": user_id_int, "label": label})

    user_options.sort(key=lambda item: item.get("label", "").lower())

    company_options: list[dict[str, Any]] = []
    for company in companies:
        company_id = company.get("id")
        if company_id is None:
            continue
        try:
            company_id_int = int(company_id)
        except (TypeError, ValueError):
            continue
        name = (company.get("name") or "").strip()
        if not name:
            name = f"Company {company_id_int}"
        company_options.append({"id": company_id_int, "name": name})

    company_options.sort(key=lambda item: item.get("name", "").lower())
    return user_options, company_options








async def _render_portal_tickets_page(
    request: Request,
    user: dict[str, Any],
    *,
    status_filter: str | None = None,
    search_term: str | None = None,
    success_message: str | None = None,
    error_message: str | None = None,
    form_values: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    try:
        user_id = int(user.get("id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from None

    available_companies = await company_access.list_accessible_companies(user)
    active_company_id = getattr(request.state, "active_company_id", None)
    company_lookup: dict[int, dict[str, Any]] = {}
    available_company_ids: list[int] = []
    for entry in available_companies:
        company_id = entry.get("company_id")
        try:
            numeric_id = int(company_id)
        except (TypeError, ValueError):
            continue
        available_company_ids.append(numeric_id)
        company_lookup[numeric_id] = entry if isinstance(entry, dict) else dict(entry)

    active_company_ids: list[int] = []
    if active_company_id is not None:
        try:
            active_company_ids = [int(active_company_id)]
        except (TypeError, ValueError):
            active_company_ids = []
    if not active_company_ids:
        active_company_ids = available_company_ids

    status_definitions = await tickets_service.list_status_definitions()

    def _normalise_status_slug(value: str | None) -> str | None:
        if value in (None, ""):
            return None
        slug = str(value).strip().lower()
        if not slug:
            return None
        for character in slug:
            if not (character.isalnum() or character in {"_", "-"}):
                return None
        return slug

    def _encode_status_value(slugs: Sequence[str]) -> str:
        unique = []
        seen: set[str] = set()
        for slug in slugs:
            normalised = _normalise_status_slug(slug)
            if not normalised or normalised in seen:
                continue
            seen.add(normalised)
            unique.append(normalised)
        if not unique:
            return ""
        if len(unique) == 1:
            return unique[0]
        unique.sort()
        return ",".join(unique)

    grouped_statuses: dict[str, dict[str, Any]] = {}
    slug_to_group: dict[str, str] = {}
    for definition in status_definitions:
        label = definition.public_status
        group_key = label.casefold()
        entry = grouped_statuses.setdefault(
            group_key,
            {
                "label": label,
                "slugs": [],
            },
        )
        normalised_slug = _normalise_status_slug(definition.tech_status)
        if not normalised_slug:
            continue
        if normalised_slug not in entry["slugs"]:
            entry["slugs"].append(normalised_slug)
        slug_to_group[normalised_slug] = group_key

    status_label_map = {
        definition.tech_status: definition.public_status for definition in status_definitions
    }

    for entry in grouped_statuses.values():
        entry["slugs"].sort()
        entry["value"] = _encode_status_value(entry["slugs"])

    value_to_group: dict[str, str] = {
        entry["value"]: key
        for key, entry in grouped_statuses.items()
        if entry.get("value")
    }

    raw_status_filter = (status_filter or "").strip()
    status_filter_value: str | None = None
    selected_status_slugs: list[str] | None = None
    if raw_status_filter:
        candidate = _normalise_status_slug(raw_status_filter)
        if candidate and candidate in value_to_group:
            group_key = value_to_group[candidate]
            entry = grouped_statuses.get(group_key) or {}
            selected_status_slugs = list(entry.get("slugs") or [])
            status_filter_value = entry.get("value")
        else:
            parts = [segment for segment in raw_status_filter.split(",") if segment.strip()]
            slugs: list[str] = []
            for part in parts:
                slug = _normalise_status_slug(part)
                if not slug or slug in slugs:
                    continue
                slugs.append(slug)
            if slugs:
                selected_status_slugs = slugs
                status_filter_value = _encode_status_value(slugs)

    search_value = (search_term or "").strip()
    effective_search = search_value or None

    has_all_ticket_access = await _has_menu_page_access(request, user, "menu.tickets", write=True)
    has_platform_ticket_access = await _has_admin_technician_access(user, request)

    try:
        if has_platform_ticket_access:
            tickets = await tickets_repo.list_tickets_in_companies(
                company_ids=None,
                status=selected_status_slugs,
                search=effective_search,
                limit=200,
            )
            total_count = await tickets_repo.count_tickets_in_companies(
                company_ids=None,
                status=selected_status_slugs,
                search=effective_search,
            )
        elif has_all_ticket_access:
            tickets = await tickets_repo.list_tickets_in_companies(
                company_ids=active_company_ids,
                status=selected_status_slugs,
                search=effective_search,
                limit=200,
            )
            total_count = await tickets_repo.count_tickets_in_companies(
                company_ids=active_company_ids,
                status=selected_status_slugs,
                search=effective_search,
            )
        else:
            tickets = await tickets_repo.list_tickets_for_user(
                user_id,
                company_ids=active_company_ids or None,
                status=selected_status_slugs,
                search=effective_search,
                limit=200,
            )
            total_count = await tickets_repo.count_tickets_for_user(
                user_id,
                company_ids=active_company_ids or None,
                status=selected_status_slugs,
                search=effective_search,
            )
    except Exception as exc:  # pragma: no cover - defensive fallback
        log_error("Failed to load portal tickets", error=str(exc))
        tickets = []
        total_count = 0
        if not error_message:
            error_message = "Unable to load tickets right now. Please try again."

    status_counts: Counter[str] = Counter()
    formatted_tickets: list[dict[str, Any]] = []
    for record in tickets:
        status_value = str(record.get("status") or "open").lower()
        status_counts[status_value] += 1
        status_label = status_label_map.get(status_value) or status_value.replace("_", " ").title()
        priority_value = str(record.get("priority") or "normal")
        priority_label = priority_value.replace("_", " ").title()
        company_name = None
        company_identifier = record.get("company_id")
        try:
            company_numeric = int(company_identifier) if company_identifier is not None else None
        except (TypeError, ValueError):
            company_numeric = None
        if company_numeric is not None:
            company_entry = company_lookup.get(company_numeric) or {}
            company_name = (
                str(company_entry.get("company_name") or company_entry.get("name") or "").strip()
                or None
            )
        updated_at = record.get("updated_at")
        created_at = record.get("created_at")
        updated_iso = (
            updated_at.astimezone(timezone.utc).isoformat()
            if hasattr(updated_at, "astimezone")
            else ""
        )
        created_iso = (
            created_at.astimezone(timezone.utc).isoformat()
            if hasattr(created_at, "astimezone")
            else ""
        )
        requester_name = " ".join(
            part
            for part in (
                str(record.get("requester_first_name") or "").strip(),
                str(record.get("requester_last_name") or "").strip(),
            )
            if part
        )
        requester_label = requester_name or str(record.get("requester_email") or "").strip() or None
        formatted_tickets.append(
            {
                "id": record.get("id"),
                "subject": record.get("subject"),
                "status": status_value,
                "status_label": status_label,
                "status_badge": _PORTAL_STATUS_BADGE_MAP.get(status_value, "badge--muted"),
                "priority_label": priority_label,
                "company_name": company_name,
                "company_id": record.get("company_id"),
                "requester_label": requester_label,
                "updated_iso": updated_iso,
                "created_iso": created_iso,
            }
        )

    for slug, group_key in slug_to_group.items():
        label = grouped_statuses[group_key]["label"]
        status_label_map.setdefault(slug, label)

    for slug, count in status_counts.items():
        if slug in slug_to_group:
            continue
        label = slug.replace("_", " ").title()
        group_key = f"dynamic::{slug}"
        grouped_statuses[group_key] = {
            "label": label,
            "slugs": [slug],
            "value": _encode_status_value([slug]),
        }
        slug_to_group[slug] = group_key
        value_to_group[grouped_statuses[group_key]["value"]] = group_key
        status_label_map.setdefault(slug, label)

    summary_entries: list[dict[str, Any]] = []
    for entry in sorted(grouped_statuses.values(), key=lambda item: item["label"].lower()):
        count = sum(status_counts.get(slug, 0) for slug in entry["slugs"])
        if count <= 0:
            continue
        summary_entries.append(
            {
                "slug": entry.get("value"),
                "label": entry["label"],
                "count": count,
            }
        )

    status_options = [
        {"value": entry["value"], "label": entry["label"]}
        for entry in sorted(grouped_statuses.values(), key=lambda item: item["label"].lower())
        if entry.get("value")
    ]

    if status_filter_value is None and selected_status_slugs:
        status_filter_value = _encode_status_value(selected_status_slugs)
    if selected_status_slugs:
        selected_status_slugs = list(dict.fromkeys(selected_status_slugs))
    else:
        selected_status_slugs = None

    extra = {
        "title": "Tickets",
        "tickets": formatted_tickets,
        "tickets_total": total_count,
        "status_options": status_options,
        "status_filter": status_filter_value,
        "status_summary": summary_entries,
        "search_term": search_value,
        "filters_active": bool(status_filter_value or search_value),
        "success_message": success_message,
        "error_message": error_message,
        "form_values": form_values or {},
    }
    response = await _render_template("tickets/index.html", request, user, extra=extra)
    response.status_code = status_code
    return response


def _format_attachment_uploaded_iso(uploaded_at: datetime | None) -> str | None:
    """Normalize attachment timestamps to UTC ISO strings."""
    if not isinstance(uploaded_at, datetime):
        return None
    uploaded_dt = (
        uploaded_at.replace(tzinfo=timezone.utc)
        if uploaded_at.tzinfo is None
        else uploaded_at.astimezone(timezone.utc)
    )
    return uploaded_dt.isoformat()


def _format_user_label(user_record: Mapping[str, Any] | None) -> str:
    """Build a safe display label for a user or staff-like record."""
    if not isinstance(user_record, Mapping):
        return "System"
    first = str(user_record.get("first_name") or "").strip()
    last = str(user_record.get("last_name") or "").strip()
    name_parts = [part for part in (first, last) if part]
    if name_parts:
        return " ".join(name_parts)
    email = str(user_record.get("email") or "").strip()
    return email or "System"


async def _render_portal_ticket_detail(
    request: Request,
    user: dict[str, Any],
    *,
    ticket_id: int,
    success_message: str | None = None,
    error_message: str | None = None,
    reply_error: str | None = None,
    reply_body: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    ticket = await tickets_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    has_helpdesk_access = await _has_admin_technician_access(user, request)
    is_super_admin = bool(user.get("is_super_admin"))

    user_id = user.get("id")
    try:
        user_id_int = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        user_id_int = None

    is_requester = user_id_int is not None and ticket.get("requester_id") == user_id_int
    is_watcher = False
    if user_id_int is not None and not is_requester:
        try:
            is_watcher = await tickets_repo.is_ticket_watcher(ticket_id, user_id_int)
        except Exception as exc:  # pragma: no cover - defensive logging
            log_error("Failed to determine ticket watcher state", error=str(exc))
            is_watcher = False

    has_company_ticket_access = False
    if not (has_helpdesk_access or is_super_admin or is_requester or is_watcher):
        has_all_ticket_access = await _has_menu_page_access(request, user, "menu.tickets", write=True)
        if has_all_ticket_access:
            available_companies = await company_access.list_accessible_companies(user)
            active_company_id = getattr(request.state, "active_company_id", None)
            allowed_company_ids: set[int] = set()
            if active_company_id is not None:
                try:
                    allowed_company_ids.add(int(active_company_id))
                except (TypeError, ValueError):
                    pass
            if not allowed_company_ids:
                for entry in available_companies:
                    try:
                        allowed_company_ids.add(int(entry.get("company_id")))
                    except (TypeError, ValueError):
                        continue
            try:
                ticket_company_id = int(ticket.get("company_id"))
            except (TypeError, ValueError):
                ticket_company_id = 0
            has_company_ticket_access = ticket_company_id in allowed_company_ids

    if not (has_helpdesk_access or is_super_admin or is_requester or is_watcher or has_company_ticket_access):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    sanitized_description = sanitize_rich_text(str(ticket.get("description") or ""))
    status_definitions = await tickets_service.list_status_definitions()
    selectable_status_definitions = [
        definition
        for definition in status_definitions
        if (is_super_admin and not definition.hide_from_admins) or (not is_super_admin and not definition.hide_from_technicians)
    ]
    status_label_map = {definition.tech_status: definition.public_status for definition in status_definitions}
    available_statuses = [definition.tech_status for definition in selectable_status_definitions]
    reply_default_status = next((definition.tech_status for definition in selectable_status_definitions if definition.is_default), None)
    if not reply_default_status:
        reply_default_status = "pending" if "pending" in available_statuses else (available_statuses[0] if available_statuses else "open")
    status_value = str(ticket.get("status") or "open").lower()
    status_label = status_label_map.get(status_value) or status_value.replace("_", " ").title()
    priority_value = str(ticket.get("priority") or "normal")
    priority_label = priority_value.replace("_", " ").title()

    created_at = ticket.get("created_at")
    updated_at = ticket.get("updated_at")
    created_iso = (
        created_at.astimezone(timezone.utc).isoformat()
        if hasattr(created_at, "astimezone")
        else ""
    )
    updated_iso = (
        updated_at.astimezone(timezone.utc).isoformat()
        if hasattr(updated_at, "astimezone")
        else ""
    )
    billed_at = ticket.get("billed_at")
    billed_at_iso = (
        billed_at.astimezone(timezone.utc).isoformat()
        if hasattr(billed_at, "astimezone")
        else ""
    )

    company_record: Mapping[str, Any] | None = None
    company_name = None
    company_identifier = ticket.get("company_id")
    try:
        company_numeric = int(company_identifier) if company_identifier is not None else None
    except (TypeError, ValueError):
        company_numeric = None
    if company_numeric is not None:
        company_record = await company_repo.get_company_by_id(company_numeric)
        if isinstance(company_record, Mapping):
            company_name = (
                str(company_record.get("name") or "").strip()
                or None
            )
        else:
            company_record = None

    replies = await tickets_repo.list_replies(ticket_id, include_internal=has_helpdesk_access)
    ordered_replies = sorted(
        replies,
        key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    # Per-recipient delivery counts power the click-through delivery-status
    # popup. We only show the click trigger when there is more than one
    # recipient on the send.
    from app.services import email_recipients as _email_recipients_svc

    reply_recipient_counts: dict[int, int] = {}
    try:
        reply_ids_for_counts = [r.get("id") for r in ordered_replies if r.get("id") is not None]
        reply_recipient_counts = await _email_recipients_svc.get_recipient_count_map(reply_ids_for_counts)
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to load per-reply recipient counts", error=str(exc))
        reply_recipient_counts = {}


    related_user_ids: set[int] = set()
    for key in ("assigned_user_id", "requester_id"):
        value = ticket.get(key)
        try:
            if value is not None:
                related_user_ids.add(int(value))
        except (TypeError, ValueError):
            continue
    for reply in ordered_replies:
        author_id = reply.get("author_id")
        try:
            if author_id is not None:
                related_user_ids.add(int(author_id))
        except (TypeError, ValueError):
            continue

    user_lookup: dict[int, Mapping[str, Any]] = {}
    if related_user_ids:
        lookup_results = await asyncio.gather(
            *(user_repo.get_user_by_id(identifier) for identifier in related_user_ids),
            return_exceptions=True,
        )
        for record in lookup_results:
            if isinstance(record, Mapping) and record.get("id") is not None:
                try:
                    identifier = int(record["id"])
                except (TypeError, ValueError):
                    continue
                user_lookup[identifier] = record

    def _format_user_label(user_record: Mapping[str, Any] | None) -> str:
        if not isinstance(user_record, Mapping):
            return "System"
        first = str(user_record.get("first_name") or "").strip()
        last = str(user_record.get("last_name") or "").strip()
        name_parts = [part for part in (first, last) if part]
        if name_parts:
            return " ".join(name_parts)
        email = str(user_record.get("email") or "").strip()
        return email or "System"

    requester_record = user_lookup.get(ticket.get("requester_id"))
    requester_staff_record = None
    requester_staff_id = ticket.get("requester_staff_id")
    if requester_staff_id is not None:
        try:
            requester_staff_record = await staff_repo.get_staff_by_id(int(requester_staff_id))
        except (TypeError, ValueError):
            requester_staff_record = None
    assigned_record = user_lookup.get(ticket.get("assigned_user_id"))

    timeline_entries: list[dict[str, Any]] = []
    for reply in ordered_replies:
        sanitized_reply = sanitize_rich_text(str(reply.get("body") or ""))
        minutes_value = reply.get("minutes_spent")
        minutes_spent = minutes_value if isinstance(minutes_value, int) and minutes_value >= 0 else None
        billable_flag = bool(reply.get("is_billable"))
        labour_type_name = str(reply.get("labour_type_name") or "").strip() or None
        time_summary = tickets_service.format_reply_time_summary(
            minutes_spent,
            billable_flag,
            labour_type_name,
        )
        created_at = reply.get("created_at")
        created_iso = (
            created_at.astimezone(timezone.utc).isoformat()
            if hasattr(created_at, "astimezone")
            else ""
        )
        author_record = user_lookup.get(reply.get("author_id"))
        
        # Get email tracking status if available
        email_tracking_id = reply.get("email_tracking_id")
        email_opened_at = reply.get("email_opened_at")
        email_open_count = reply.get("email_open_count", 0)
        email_sent_at = reply.get("email_sent_at")
        has_tracking = email_tracking_id is not None
        is_email_opened = email_opened_at is not None
        try:
            recipient_count_for_reply = int(reply_recipient_counts.get(int(reply.get("id")), 0))
        except (TypeError, ValueError):
            recipient_count_for_reply = 0
        
        timeline_entries.append(
            {
                "id": reply.get("id"),
                "type": "reply",
                "author": author_record,
                "author_label": _format_user_label(author_record),
                "created_iso": created_iso,
                "body_html": sanitized_reply.html,
                "has_content": sanitized_reply.has_rich_content,
                "time_summary": time_summary,
                "is_internal": bool(reply.get("is_internal")),
                "labour_type_name": labour_type_name,
                "labour_type_code": reply.get("labour_type_code"),
                "external_reference": reply.get("external_reference"),
                "email_tracking_id": email_tracking_id,
                "email_sent_at": email_sent_at,
                "email_opened_at": email_opened_at,
                "email_open_count": email_open_count,
                "has_email_tracking": has_tracking,
                "is_email_opened": is_email_opened,
                "recipient_count": recipient_count_for_reply,
                "is_split_hidden": bool(reply.get("is_split_hidden")),
                "split_to_ticket_id": reply.get("split_to_ticket_id"),
                "split_to_ticket_number": reply.get("split_to_ticket_number"),
            }
        )
    
    # Sort timeline entries by date
    timeline_entries.sort(key=lambda e: e.get("created_iso", ""), reverse=True)

    # Find relevant knowledge base articles based on AI tag matching
    relevant_articles: list[dict[str, Any]] = []
    ticket_ai_tags = ticket.get("ai_tags") or []
    if ticket_ai_tags:
        min_matching_tags = settings.ai_tag_threshold
        relevant_articles = await knowledge_base_repo.find_relevant_articles_for_ticket(
            ticket_ai_tags=ticket_ai_tags,
            min_matching_tags=min_matching_tags,
        )

    # Get ticket watchers
    watcher_records = await tickets_repo.list_watchers(ticket_id)
    watchers = []
    for watcher in watcher_records:
        if watcher.get("user_id"):
            watcher_user = user_lookup.get(watcher.get("user_id"))
            watchers.append({
                "id": watcher.get("user_id"),
                "label": _format_user_label(watcher_user) if watcher_user else "Unknown User",
                "email": watcher.get("email"),
            })
        elif watcher.get("email"):
            watchers.append({
                "id": None,
                "label": watcher.get("email"),
                "email": watcher.get("email"),
            })

    ticket_mention_staff_options: list[dict[str, Any]] = []
    if has_helpdesk_access or is_super_admin:
        try:
            ticket_company_id = int(ticket.get("company_id")) if ticket.get("company_id") is not None else None
        except (TypeError, ValueError):
            ticket_company_id = None
        if ticket_company_id is not None:
            for staff_user in await staff_repo.list_enabled_staff_users(ticket_company_id):
                user_id_value = staff_user.get("user_id")
                if user_id_value is None:
                    continue
                try:
                    user_id_int = int(user_id_value)
                except (TypeError, ValueError):
                    continue
                label = _format_user_label(staff_user) or str(staff_user.get("email") or "").strip()
                ticket_mention_staff_options.append({
                    "id": user_id_int,
                    "label": label,
                    "email": str(staff_user.get("email") or "").strip(),
                })

    # Get ticket attachments
    attachment_records: list[Mapping[str, Any]] = []
    try:
        if has_helpdesk_access or is_super_admin:
            attachment_records = await attachments_repo.list_attachments(ticket_id)
        else:
            attachment_records = await attachments_repo.list_attachments(
                ticket_id, access_levels=("open", "closed")
            )
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to load ticket attachments", ticket_id=ticket_id, error=str(exc))
        attachment_records = []

    formatted_attachments: list[dict[str, Any]] = []
    for attachment in attachment_records:
        uploaded_at = attachment.get("uploaded_at")
        uploaded_iso = _format_attachment_uploaded_iso(uploaded_at)
        try:
            file_size = int(attachment.get("file_size", 0) or 0)
        except (TypeError, ValueError):
            file_size = 0

        formatted_attachments.append(
            {
                **attachment,
                "uploaded_iso": uploaded_iso,
                "file_size": file_size,
            }
        )

    # Get linked assets
    ticket_assets = await tickets_repo.list_ticket_assets(ticket_id)
    
    # Find relevant service statuses based on AI tag matching
    from app.services import service_status as service_status_service
    relevant_services: list[dict[str, Any]] = []
    if ticket_ai_tags:
        relevant_services = await service_status_service.find_relevant_services_for_ticket(
            ticket_ai_tags=ticket_ai_tags,
            company_id=company_numeric,
        )
    
    # Create service status lookup for consistent styling
    service_status_lookup = {entry["value"]: entry for entry in service_status_service.STATUS_DEFINITIONS}

    merged_child_tickets: list[dict[str, Any]] = []
    try:
        merged_child_tickets = await tickets_repo.list_merged_child_tickets(int(ticket_id))
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to load merged child tickets", ticket_id=ticket_id, error=str(exc))


    extra = {
        "title": f"Ticket {ticket_id}",
        "ticket": {
            **ticket,
            "status_label": status_label,
            "status_badge": _PORTAL_STATUS_BADGE_MAP.get(status_value, "badge--muted"),
            "priority_label": priority_label,
            "description_html": sanitized_description.html,
            "description_has_content": sanitized_description.has_rich_content,
            "company": company_record,
            "company_name": company_name,
            "requester": requester_record,
            "requester_label": (
                _format_user_label(requester_staff_record)
                if requester_staff_record
                else (_format_user_label(requester_record) if requester_record else None)
            ),
            "assigned_user": assigned_record,
            "assigned_label": _format_user_label(assigned_record) if assigned_record else None,
            "created_iso": created_iso,
            "updated_iso": updated_iso,
            "billed_at_iso": billed_at_iso,
        },
        "assigned_user": assigned_record,
        "ticket_replies": timeline_entries,
        "ticket_watchers": watchers,
        "ticket_mention_staff_options": ticket_mention_staff_options,
        "ticket_attachments": formatted_attachments,
        "ticket_assets": ticket_assets,
        "ticket_status_definitions": [
            {
                "tech_status": definition.tech_status,
                "tech_label": definition.tech_label,
                "public_status": definition.public_status,
                "is_default": definition.is_default,
                "hide_from_technicians": definition.hide_from_technicians,
                "hide_from_admins": definition.hide_from_admins,
            }
            for definition in status_definitions
        ],
        "ticket_reply_default_status": reply_default_status,
        "relevant_services": relevant_services,
        "service_status_lookup": service_status_lookup,
        "merged_child_tickets": merged_child_tickets,
        "can_reply": bool(has_helpdesk_access or is_super_admin or is_requester),
        "is_requester": is_requester,
        "is_watcher": is_watcher,
        "has_helpdesk_access": has_helpdesk_access,
        "relevant_kb_articles": relevant_articles,
        "success_message": success_message,
        "error_message": error_message,
        "reply_error": reply_error,
        "reply_body": reply_body or "",
    }
    response = await _render_template("tickets/detail.html", request, user, extra=extra)
    response.status_code = status_code
    return response


async def _get_ticket_dashboard_reference_data() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    expires_at = _ticket_dashboard_reference_cache.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at > now:
        return {
            "modules": list(_ticket_dashboard_reference_cache.get("modules") or []),
            "companies": list(_ticket_dashboard_reference_cache.get("companies") or []),
            "technicians": list(_ticket_dashboard_reference_cache.get("technicians") or []),
            "company_lookup": dict(_ticket_dashboard_reference_cache.get("company_lookup") or {}),
            "user_lookup": dict(_ticket_dashboard_reference_cache.get("user_lookup") or {}),
        }

    async with _ticket_dashboard_reference_lock:
        expires_at = _ticket_dashboard_reference_cache.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at > datetime.now(timezone.utc):
            return {
                "modules": list(_ticket_dashboard_reference_cache.get("modules") or []),
                "companies": list(_ticket_dashboard_reference_cache.get("companies") or []),
                "technicians": list(_ticket_dashboard_reference_cache.get("technicians") or []),
                "company_lookup": dict(_ticket_dashboard_reference_cache.get("company_lookup") or {}),
                "user_lookup": dict(_ticket_dashboard_reference_cache.get("user_lookup") or {}),
            }

        dashboard = await tickets_service.load_dashboard_state(
            status_filter=None,
            module_filter=None,
            limit=0,
            include_reference_data=True,
        )
        _ticket_dashboard_reference_cache.update(
            {
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=_TICKET_DASHBOARD_REFERENCE_TTL_SECONDS),
                "modules": list(dashboard.modules),
                "companies": list(dashboard.companies),
                "technicians": list(dashboard.technicians),
                "company_lookup": dict(dashboard.company_lookup),
                "user_lookup": dict(dashboard.user_lookup),
            }
        )
        return {
            "modules": list(dashboard.modules),
            "companies": list(dashboard.companies),
            "technicians": list(dashboard.technicians),
            "company_lookup": dict(dashboard.company_lookup),
            "user_lookup": dict(dashboard.user_lookup),
        }


async def _render_tickets_dashboard(
    request: Request,
    user: dict[str, Any],
    *,
    success_message: str | None = None,
    error_message: str | None = None,
    status_filter: list[str] | None = None,
    company_id: int | None = None,
    assigned_user_id: int | None = None,
    search: str | None = None,
    module_slug: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    # Load status definitions for sidebar and filter options (no ticket rows needed)
    dashboard = await tickets_service.load_dashboard_state(
        status_filter=None,
        module_filter=None,
        limit=0,
        include_reference_data=False,
    )
    # Global status counts for the sidebar stats (fast GROUP BY query)
    global_status_counts: dict[str, int] = await tickets_repo.count_tickets_by_status()

    tickets: list[dict[str, Any]] = []
    ticket_total = 0
    ticket_time_lookup: dict[int, dict[str, Any]] = {}
    ticket_automation_filter_lookup: dict[int, dict[str, Any]] = {}
    ticket_autoload = True

    if tickets:
        ticket_ids = [int(t.get("id")) for t in tickets if t.get("id") is not None]
        ticket_time_lookup = await tickets_repo.get_time_totals_by_ticket_ids(ticket_ids)
        ticket_automation_filter_lookup = await tickets_repo.get_automation_filter_context_by_ticket_ids(ticket_ids)

    reference_data = await _get_ticket_dashboard_reference_data()

    # Build the initial dashboard API endpoint URL with active filter params
    _dashboard_params: list[str] = []
    if status_filter:
        for s in status_filter:
            _dashboard_params.append(f"status={s}")
    if company_id is not None:
        _dashboard_params.append(f"companyId={company_id}")
    if assigned_user_id is not None:
        _dashboard_params.append(f"assignedUserId={assigned_user_id}")
    if search:
        from urllib.parse import quote as _url_quote
        _dashboard_params.append(f"search={_url_quote(search, safe='')}")
    if module_slug:
        _dashboard_params.append(f"module={module_slug}")
    dashboard_endpoint = "/api/tickets/dashboard"
    if _dashboard_params:
        dashboard_endpoint = f"{dashboard_endpoint}?{'&'.join(_dashboard_params)}"

    selectable_status_definitions = [
        definition
        for definition in dashboard.status_definitions
        if (bool(user.get("is_super_admin")) and not definition.hide_from_admins) or (not bool(user.get("is_super_admin")) and not definition.hide_from_technicians)
    ]
    def _status_definition_payload(definition: tickets_service.TicketStatusDefinition) -> dict[str, Any]:
        return {
            "tech_status": definition.tech_status,
            "tech_label": definition.tech_label,
            "public_status": definition.public_status,
            "is_default": definition.is_default,
            "hide_from_technicians": definition.hide_from_technicians,
            "hide_from_admins": definition.hide_from_admins,
        }

    status_definitions_payload = [
        _status_definition_payload(definition)
        for definition in selectable_status_definitions
    ]
    filter_status_definitions_payload = [
        _status_definition_payload(definition)
        for definition in dashboard.status_definitions
    ]
    status_label_map = {
        definition.tech_status: definition.tech_label for definition in dashboard.status_definitions
    }
    public_status_map = {
        definition.tech_status: definition.public_status for definition in dashboard.status_definitions
    }
    reply_default_status = next(
        (definition.tech_status for definition in selectable_status_definitions if definition.is_default),
        None,
    )
    if not reply_default_status:
        reply_default_status = (
            "pending"
            if "pending" in dashboard.available_statuses
            else (dashboard.available_statuses[0] if dashboard.available_statuses else "open")
        )
    labour_types = await labour_types_service.list_labour_types()
    from app.repositories import ticket_canned_responses as canned_responses_repo

    if await _is_helpdesk_technician(user, request):
        ticket_canned_responses = await canned_responses_repo.list_responses()
    else:
        ticket_canned_responses = []
    extra = {
        "title": "Ticketing workspace",
        "tickets": tickets,
        "ticket_total": ticket_total,
        "ticket_status_counts": global_status_counts,
        "ticket_available_statuses": dashboard.available_statuses,
        "ticket_status_definitions": status_definitions_payload,
        "ticket_filter_status_definitions": filter_status_definitions_payload,
        # Status visibility only controls ticket editing.  The configuration
        # editor must retain every definition so saving it cannot implicitly
        # delete statuses hidden from the current admin.
        "ticket_status_configuration_definitions": filter_status_definitions_payload,
        "ticket_status_label_map": status_label_map,
        "ticket_public_status_map": public_status_map,
        "ticket_reply_default_status": reply_default_status,
        "ticket_modules": reference_data["modules"],
        "ticket_company_options": reference_data["companies"],
        "ticket_user_options": reference_data["technicians"],
        "ticket_company_lookup": reference_data["company_lookup"],
        "ticket_user_lookup": reference_data["user_lookup"],
        "ticket_labour_types": labour_types,
        "ticket_canned_responses": ticket_canned_responses,
        "ticket_time_lookup": ticket_time_lookup,
        "ticket_automation_filter_lookup": ticket_automation_filter_lookup,
        "ticket_dashboard_now": datetime.now(timezone.utc),
        "can_bulk_delete_tickets": bool(user.get("is_super_admin")),
        "next_ticket_number": await site_settings_repo.get_next_ticket_number(),
        "success_message": success_message,
        "error_message": error_message,
        "ticket_dashboard_endpoint": dashboard_endpoint,
        "ticket_refresh_topics": ["tickets"],
        "ticket_autoload": ticket_autoload,
        "ticket_initial_status_filter": status_filter or [],
    }
    response = await _render_template("admin/tickets.html", request, user, extra=extra)
    response.status_code = status_code
    return response


def _ticket_related_safe_url(url: Any) -> str | None:
    candidate = str(url or "").strip()
    if not candidate:
        return None
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    return candidate


def _ticket_related_fallback_url(source_type: str, source_id: Any) -> str | None:
    identifier = str(source_id or "").strip()
    if not identifier:
        return None
    if source_type == "tickets":
        return f"/admin/tickets/{quote(identifier, safe='')}"
    if source_type == "assets":
        return f"/admin/assets/{quote(identifier, safe='')}"
    if source_type == "companies":
        return f"/admin/companies/{quote(identifier, safe='')}"
    if source_type == "staff":
        return f"/admin/staff/{quote(identifier, safe='')}"
    if source_type == "issues":
        return f"/admin/issues/{quote(identifier, safe='')}"
    return None


async def _load_ticket_stored_related_items(ticket_id: int, *, limit: int = 12) -> list[dict[str, str]]:
    try:
        document = await rag_index_repo.get_document_by_source(
            "tickets",
            str(ticket_id),
            rag_index_service.embedding_model(),
        )
        if not document:
            return []
        evidence_rows = await rag_relationship_repo.list_relationship_evidence(
            int(document["id"]),
            limit=limit,
        )
    except Exception as exc:  # pragma: no cover - defensive UI fallback
        log_error("Failed to load stored ticket related content", ticket_id=ticket_id, error=str(exc))
        return []

    items: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for row in evidence_rows:
        source_type = str(row.get("source_type") or "").strip()
        source_id = row.get("source_id")
        if source_type == "tickets":
            try:
                if int(source_id) == ticket_id:
                    continue
            except (TypeError, ValueError):
                pass
        url = _ticket_related_safe_url(row.get("url")) or _ticket_related_fallback_url(source_type, source_id)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        label = str(row.get("title") or f"{source_type.title()} {source_id}").strip()[:180]
        items.append({"type": source_type, "label": label, "url": url})
    return items


def _format_ticket_requester_phone(phone_number: Any) -> str | None:
    digits = re.sub(r"\D+", "", str(phone_number or ""))
    if not digits:
        return None
    if digits.startswith("61") and len(digits) == 11:
        digits = f"0{digits[2:]}"
    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    if len(digits) == 11:
        return f"{digits[:5]} {digits[5:8]} {digits[8:]}"
    return str(phone_number or "").strip() or None


async def _render_ticket_detail(
    request: Request,
    user: dict[str, Any],
    *,
    ticket_id: int,
    success_message: str | None = None,
    error_message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    ticket = await tickets_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    sanitized_description = sanitize_rich_text(str(ticket.get("description") or ""))
    ticket = {
        **ticket,
        "description_html": sanitized_description.html,
        "description_text": sanitized_description.text_content,
    }
    from app.services import slas as sla_service
    ticket_sla = (await sla_service.statuses_for_tickets([ticket_id])).get(ticket_id, {"state": "not_applicable", "label": "No SLA"})

    replies = await tickets_repo.list_replies(ticket_id)
    split_replies = await tickets_repo.list_split_replies_for_original(ticket_id)
    replies = [*replies, *split_replies]
    watchers = await tickets_repo.list_watchers(ticket_id)
    from app.services import ticket_shipment_tracking as shipment_watch_service

    shipment_watch = await shipment_watch_service.get_watch_for_ticket(ticket_id)

    related_user_ids: set[int] = set()
    for key in ("assigned_user_id", "requester_id"):
        value = ticket.get(key)
        if value:
            try:
                related_user_ids.add(int(value))
            except (TypeError, ValueError):
                continue
    for reply in replies:
        author_id = reply.get("author_id")
        if author_id:
            related_user_ids.add(int(author_id))
    for watcher in watchers:
        watcher_user_id = watcher.get("user_id")
        if watcher_user_id:
            related_user_ids.add(int(watcher_user_id))

    user_lookup: dict[int, dict[str, Any]] = {}
    if related_user_ids:
        lookup_results = await asyncio.gather(
            *(user_repo.get_user_by_id(user_id) for user_id in related_user_ids)
        )
        for record in lookup_results:
            if record and record.get("id") is not None:
                try:
                    identifier = int(record["id"])
                except (TypeError, ValueError):
                    continue
                user_lookup[identifier] = record

    company: dict[str, Any] | None = None
    ticket_company_id: int | None = None
    company_id_value = ticket.get("company_id")
    if company_id_value is not None:
        try:
            ticket_company_id = int(company_id_value)
        except (TypeError, ValueError):
            ticket_company_id = None
        else:
            company = await company_repo.get_company_by_id(ticket_company_id)

    modules = await modules_service.list_modules()

    module_info: dict[str, Any] | None = None
    module_slug = ticket.get("module_slug")
    if module_slug:
        for module in modules:
            if module.get("slug") == module_slug:
                module_info = module
                break


    ordered_replies = sorted(
        replies,
        key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    # Per-recipient delivery counts so the delivery-status badge in the admin
    # ticket detail can be rendered as a click trigger when the email had
    # more than one recipient (To/CC/BCC).
    from app.services import email_recipients as _email_recipients_svc

    admin_reply_recipient_counts: dict[int, int] = {}
    try:
        _admin_reply_ids = [r.get("id") for r in ordered_replies if r.get("id") is not None]
        admin_reply_recipient_counts = await _email_recipients_svc.get_recipient_count_map(_admin_reply_ids)
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to load per-reply recipient counts (admin)", error=str(exc))
        admin_reply_recipient_counts = {}

    from app.repositories import ticket_canned_responses as canned_responses_repo

    attachment_records: list[Mapping[str, Any]] = []
    try:
        attachment_records = await attachments_repo.list_attachments(ticket_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error(
            "Failed to load ticket attachments",
            ticket_id=ticket_id,
            error=str(exc),
        )
        attachment_records = []

    formatted_attachments: list[dict[str, Any]] = []
    for attachment in attachment_records:
        uploaded_at = attachment.get("uploaded_at")
        uploaded_iso = _format_attachment_uploaded_iso(uploaded_at)
        try:
            file_size = int(attachment.get("file_size", 0) or 0)
        except (TypeError, ValueError):
            file_size = 0

        formatted_attachments.append(
            {
                **attachment,
                "uploaded_iso": uploaded_iso,
                "file_size": file_size,
            }
        )

    total_billable_minutes = 0
    total_non_billable_minutes = 0
    enriched_replies: list[dict[str, Any]] = []
    for reply in ordered_replies:
        author_id = reply.get("author_id")
        author = user_lookup.get(author_id) if author_id else None
        sanitized_reply = sanitize_rich_text(str(reply.get("body") or ""))
        minutes_value = reply.get("minutes_spent")
        minutes_spent = minutes_value if isinstance(minutes_value, int) and minutes_value >= 0 else None
        billable_flag = bool(reply.get("is_billable"))
        if minutes_spent is not None:
            if billable_flag:
                total_billable_minutes += minutes_spent
            else:
                total_non_billable_minutes += minutes_spent
        labour_type_name = str(reply.get("labour_type_name") or "").strip() or None
        time_summary = tickets_service.format_reply_time_summary(
            minutes_spent,
            billable_flag,
            labour_type_name,
        )
        
        # Get email tracking status if available
        email_tracking_id = reply.get("email_tracking_id")
        email_opened_at = reply.get("email_opened_at")
        email_open_count = reply.get("email_open_count", 0)
        email_sent_at = reply.get("email_sent_at")
        email_delivered_at = reply.get("email_delivered_at")
        email_bounced_at = reply.get("email_bounced_at")
        smtp2go_message_id = reply.get("smtp2go_message_id")
        
        has_tracking = email_tracking_id is not None or smtp2go_message_id is not None
        is_email_opened = email_opened_at is not None
        is_email_delivered = email_delivered_at is not None
        is_email_bounced = email_bounced_at is not None
        try:
            recipient_count_for_reply = int(admin_reply_recipient_counts.get(int(reply.get("id")), 0))
        except (TypeError, ValueError):
            recipient_count_for_reply = 0

        enriched_replies.append(
            {
                **reply,
                "author": author,
                "body": sanitized_reply.html,
                "text_body": sanitized_reply.text_content,
                "minutes_spent": minutes_spent,
                "is_billable": billable_flag,
                "time_summary": time_summary,
                "labour_type_name": labour_type_name,
                "email_tracking_id": email_tracking_id,
                "email_sent_at": email_sent_at,
                "email_opened_at": email_opened_at,
                "email_open_count": email_open_count,
                "email_delivered_at": email_delivered_at,
                "email_bounced_at": email_bounced_at,
                "smtp2go_message_id": smtp2go_message_id,
                "has_email_tracking": has_tracking,
                "is_email_opened": is_email_opened,
                "is_email_delivered": is_email_delivered,
                "is_email_bounced": is_email_bounced,
                "recipient_count": recipient_count_for_reply,
                "is_split_hidden": bool(reply.get("is_split_hidden")),
                "split_to_ticket_id": reply.get("split_to_ticket_id"),
                "split_to_ticket_number": reply.get("split_to_ticket_number"),
            }
        )
    

    enriched_watchers: list[dict[str, Any]] = []
    for watcher in watchers:
        watcher_user = user_lookup.get(watcher.get("user_id"))
        enriched_watchers.append({**watcher, "user": watcher_user})

    labour_types = await labour_types_service.list_labour_types()

    status_definitions = await tickets_service.list_status_definitions()
    selectable_status_definitions = [
        definition
        for definition in status_definitions
        if (bool(user.get("is_super_admin")) and not definition.hide_from_admins) or (not bool(user.get("is_super_admin")) and not definition.hide_from_technicians)
    ]
    status_label_map = {definition.tech_status: definition.tech_label for definition in status_definitions}
    public_status_map = {definition.tech_status: definition.public_status for definition in status_definitions}
    available_statuses = [definition.tech_status for definition in selectable_status_definitions]
    reply_default_status = next((definition.tech_status for definition in selectable_status_definitions if definition.is_default), None)
    if not reply_default_status:
        reply_default_status = "pending" if "pending" in available_statuses else (available_statuses[0] if available_statuses else "open")
    ticket_status_slug = ticket.get("status") or "open"
    if ticket_status_slug not in available_statuses:
        available_statuses.append(ticket_status_slug)

    companies = await company_repo.list_companies()
    technician_users = await membership_repo.list_users_with_permission(
        HELPDESK_PERMISSION_KEY
    )
    requester_options: list[dict[str, Any]] = []
    watcher_staff_options: list[dict[str, Any]] = []
    if ticket_company_id is not None:
        requester_options = await staff_repo.list_enabled_staff_users(ticket_company_id)
        # Get all enabled staff for the company as watcher options
        watcher_staff_options = await staff_repo.list_enabled_staff_users(ticket_company_id)


    ticket_mention_staff_options = [
        {
            "id": int(option.get("user_id")),
            "label": _format_user_label(option) or str(option.get("email") or "").strip(),
            "email": str(option.get("email") or "").strip(),
        }
        for option in watcher_staff_options
        if option.get("user_id") is not None
    ]

    current_requester_id = ticket.get("requester_id")
    if isinstance(current_requester_id, int):
        existing_ids = {
            int(option.get("id"))
            for option in requester_options
            if option.get("id") is not None
        }
        if current_requester_id not in existing_ids:
            current_requester = user_lookup.get(current_requester_id)
            if current_requester:
                requester_options.append(current_requester)

        def _requester_sort_key(record: dict[str, Any]) -> tuple[str, int]:
            email_value = str(record.get("email") or "").lower()
            identifier = record.get("id")
            try:
                identifier_int = int(identifier)
            except (TypeError, ValueError):
                identifier_int = 0
            return email_value, identifier_int

        requester_options.sort(key=_requester_sort_key)

    ticket_requester_phone_display: str | None = None
    requester_staff_id = ticket.get("requester_staff_id")
    requester_user_id = ticket.get("requester_id")
    def _same_identifier(left: Any, right: Any) -> bool:
        if left is None or right is None:
            return False
        try:
            return int(left) == int(right)
        except (TypeError, ValueError):
            return str(left) == str(right)

    for requester_option in requester_options:
        if (
            _same_identifier(requester_option.get("staff_id"), requester_staff_id)
            or _same_identifier(requester_option.get("user_id"), requester_user_id)
            or _same_identifier(requester_option.get("id"), requester_user_id)
        ):
            ticket_requester_phone_display = _format_ticket_requester_phone(
                requester_option.get("mobile_phone")
            )
            break
    if ticket_requester_phone_display is None:
        requester_record = user_lookup.get(ticket.get("requester_id"))
        if requester_record:
            ticket_requester_phone_display = _format_ticket_requester_phone(
                requester_record.get("mobile_phone")
            )
    ticket_company_phone_display = _format_ticket_requester_phone(
        company.get("phone") if company else None
    )
    ticket_requester_lookup_name = ""
    for requester_option in requester_options:
        if (_same_identifier(requester_option.get("staff_id"), requester_staff_id)
                or _same_identifier(requester_option.get("user_id"), requester_user_id)
                or _same_identifier(requester_option.get("id"), requester_user_id)):
            ticket_requester_lookup_name = " ".join(filter(None, (
                str(requester_option.get("first_name") or "").strip(),
                str(requester_option.get("last_name") or "").strip(),
            )))
            break

    default_priorities = ["urgent", "high", "normal", "low"]
    current_priority = str(ticket.get("priority") or "normal")
    seen_priorities: set[str] = set()
    priority_options: list[str] = []
    for option in [*default_priorities, current_priority]:
        option_str = str(option)
        normalised = option_str.lower()
        if normalised in seen_priorities:
            continue
        seen_priorities.add(normalised)
        priority_options.append(option_str)

    ticket_assets = await tickets_repo.list_ticket_assets(ticket_id)
    ticket_suggested_assets = await tickets_repo.list_ticket_suggested_assets(ticket_id)
    asset_selection: list[int] = []
    for linked in ticket_assets:
        asset_id = linked.get("asset_id")
        try:
            asset_selection.append(int(asset_id))
        except (TypeError, ValueError):
            continue

    serialisable_ticket_assets: list[dict[str, Any]] = []
    for asset in ticket_assets:
        if not isinstance(asset, Mapping):
            continue
        asset_identifier = asset.get("asset_id")
        serialisable_ticket_assets.append(
            {
                "id": asset_identifier,
                "asset_id": asset_identifier,
                "name": str(asset.get("name") or "").strip() or (f"Asset {asset_identifier}" if asset_identifier else "Asset"),
                "serial_number": (str(asset.get("serial_number") or "").strip() or None),
                "status": (str(asset.get("status") or "").strip() or None),
                "tactical_asset_id": (str(asset.get("tactical_asset_id") or "").strip() or None),
            }
        )

    asset_options: list[dict[str, Any]] = []
    if ticket_company_id is not None:
        company_assets = await assets_repo.list_company_assets(ticket_company_id)

        def _format_asset_label(asset_row: Mapping[str, Any]) -> str:
            asset_name = str(asset_row.get("name") or "").strip() or "Asset"
            serial_value = str(asset_row.get("serial_number") or "").strip()
            status_value = str(asset_row.get("status") or "").strip()
            parts = [asset_name]
            if serial_value:
                parts.append(f"SN {serial_value}")
            if status_value:
                parts.append(status_value.title())
            return " · ".join(parts)

        for asset_row in company_assets:
            asset_id = asset_row.get("id")
            if asset_id is None:
                continue
            try:
                asset_id_int = int(asset_id)
            except (TypeError, ValueError):
                continue
            asset_options.append(
                {
                    "id": asset_id_int,
                    "label": _format_asset_label(asset_row),
                    "name": str(asset_row.get("name") or "").strip() or f"Asset {asset_id_int}",
                    "serial_number": str(asset_row.get("serial_number") or "").strip() or None,
                    "status": str(asset_row.get("status") or "").strip() or None,
                    "tactical_asset_id": str(asset_row.get("tactical_asset_id") or "").strip() or None,
                }
            )

    asset_options.sort(key=lambda option: option["label"].lower())

    ticket_related_items = await _load_ticket_stored_related_items(ticket_id)
    ticket_expenses = await expenses_repo.list_expenses(ticket_id)
    ticket_canned_responses = await canned_responses_repo.list_responses()
    ticket_expense_total = sum(Decimal(str(expense.get("amount") or 0)) for expense in ticket_expenses)

    # Find relevant knowledge base articles based on AI tag matching
    relevant_articles: list[dict[str, Any]] = []
    ticket_ai_tags = ticket.get("ai_tags") or []
    if ticket_ai_tags:
        min_matching_tags = settings.ai_tag_threshold
        relevant_articles = await knowledge_base_repo.find_relevant_articles_for_ticket(
            ticket_ai_tags=ticket_ai_tags,
            min_matching_tags=min_matching_tags,
        )

    # Find relevant service statuses based on AI tag matching
    from app.services import service_status as service_status_service
    relevant_services: list[dict[str, Any]] = []
    if ticket_ai_tags:
        relevant_services = await service_status_service.find_relevant_services_for_ticket(
            ticket_ai_tags=ticket_ai_tags,
            company_id=ticket_company_id,
        )
    
    # Create service status lookup for consistent styling
    service_status_lookup = {entry["value"]: entry for entry in service_status_service.STATUS_DEFINITIONS}

    merged_child_tickets: list[dict[str, Any]] = []
    try:
        merged_child_tickets = await tickets_repo.list_merged_child_tickets(int(ticket_id))
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to load merged child tickets", ticket_id=ticket_id, error=str(exc))


    extra = {
        "title": f"Ticket #{ticket_id}",
        "ticket": ticket,
        "ticket_sla": ticket_sla,
        "ticket_company": company,
        "ticket_module": module_info,
        "ticket_assigned_user": user_lookup.get(ticket.get("assigned_user_id")),
        "ticket_requester": user_lookup.get(ticket.get("requester_id")),
        "ticket_replies": enriched_replies,
        "ticket_watchers": enriched_watchers,
        "ticket_shipment_watch": shipment_watch,
        "ticket_attachments": formatted_attachments,
        "ticket_expenses": ticket_expenses,
        "ticket_canned_responses": ticket_canned_responses,
        "ticket_expense_total": ticket_expense_total,
        "ticket_related_auto_scan": False,
        "ticket_related_items": ticket_related_items,
        "ticket_labour_types": labour_types,
        "ticket_billable_minutes": total_billable_minutes,
        "ticket_non_billable_minutes": total_non_billable_minutes,
        "ticket_available_statuses": available_statuses,
        "ticket_selectable_status_values": [definition.tech_status for definition in selectable_status_definitions],
        "ticket_status_definitions": [
            {
                "tech_status": definition.tech_status,
                "tech_label": definition.tech_label,
                "public_status": definition.public_status,
                "is_default": definition.is_default,
                "hide_from_technicians": definition.hide_from_technicians,
                "hide_from_admins": definition.hide_from_admins,
            }
            for definition in selectable_status_definitions
        ],
        "ticket_status_label_map": status_label_map,
        "ticket_public_status_map": public_status_map,
        "ticket_reply_default_status": reply_default_status,
        "ticket_company_options": companies,
        "ticket_user_options": technician_users,
        "ticket_requester_options": requester_options,
        "ticket_requester_phone_display": ticket_requester_phone_display,
        "ticket_company_phone_display": ticket_company_phone_display,
        "ticket_requester_lookup_name": ticket_requester_lookup_name,
        "ticket_watcher_staff_options": watcher_staff_options,
        "ticket_mention_staff_options": ticket_mention_staff_options,
        "ticket_priority_options": priority_options,
        "ticket_return_url": request.url.path,
        "ticket_assets": ticket_assets,
        "ticket_suggested_assets": ticket_suggested_assets,
        "ticket_asset_options": asset_options,
        "ticket_asset_selection": asset_selection,
        "ticket_asset_linked_data": serialisable_ticket_assets,
        "can_delete_ticket": bool(user.get("is_super_admin")),
        "relevant_kb_articles": relevant_articles,
        "relevant_services": relevant_services,
        "service_status_lookup": service_status_lookup,
        "merged_child_tickets": merged_child_tickets,
        "success_message": success_message,
        "error_message": error_message,
    }
    response = await _render_template("admin/ticket_detail.html", request, user, extra=extra)
    response.status_code = status_code
    return response


def _get_current_user_id(user: Mapping[str, Any] | None) -> int | None:
    if not user:
        return None
    try:
        return int(user.get("id"))  # type: ignore[arg-type]
    except (TypeError, ValueError, AttributeError):
        return None
async def _render_modules_dashboard(
    request: Request,
    user: dict[str, Any],
    *,
    success_message: str | None = None,
    error_message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    modules = await modules_service.list_modules()
    public_base = str(settings.public_base_url or "").strip().rstrip("/")
    if not public_base:
        public_base = str(request.base_url).rstrip("/")

    module_webhook_urls = {
        "smtp2go": f"{public_base}/api/webhooks/smtp2go/events",
        "trello": f"{public_base}/api/integration-modules/trello/webhook",
    }
    extra = {
        "title": "Integration modules",
        "modules": modules,
        "module_webhook_urls": module_webhook_urls,
        "success_message": success_message,
        "error_message": error_message,
    }
    response = await _render_template("admin/modules.html", request, user, extra=extra)
    response.status_code = status_code
    return response


@app.get("/admin/modules", response_class=HTMLResponse)
async def admin_modules_page(
    request: Request,
):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    return await _render_modules_dashboard(
        request,
        current_user,
    )


@app.get("/admin/feature-packs", response_class=HTMLResponse)
async def admin_feature_packs_page(
    request: Request,
):
    """Admin UI wrapping the feature pack registry.

    Lists every loaded ``app/features/<slug>/`` pack with its current
    version, last-loaded timestamp, in-flight request count, last
    reload duration, and last error.  Each row has a Reload button
    that POSTs to ``/api/features/{slug}/reload`` (CSRF-protected,
    super-admin only) — the same API documented in
    ``docs/feature_packs.md``.
    """

    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect

    loaded = feature_registry.list()
    packs = sorted(
        [item for item in loaded if not str(item.get("slug", "")).startswith("plugin.")],
        key=lambda p: p["slug"],
    )
    plugins = await get_plugin_loader().list_admin_rows(feature_registry)

    extra = {
        "title": "Feature packs",
        "packs": packs,
        "plugins": plugins,
    }
    return await _render_template(
        "admin/feature_packs.html", request, current_user, extra=extra
    )


@app.post("/admin/modules/{slug}", response_class=HTMLResponse)
async def admin_update_module(slug: str, request: Request):
    current_user, redirect = await _require_super_admin_page(request)
    if redirect:
        return redirect
    form = await request.form()
    raw_enabled = form.get("enabled")
    enabled = False
    if raw_enabled is not None:
        if isinstance(raw_enabled, str):
            enabled = raw_enabled.strip().lower() not in {"", "0", "false", "off"}
        else:
            enabled = bool(raw_enabled)
    try:
        await modules_service.update_module(slug, enabled=enabled)
    except Exception as exc:  # pragma: no cover - defensive logging
        log_error("Failed to update integration module", slug=slug, error=str(exc))
        return await _render_modules_dashboard(
            request,
            current_user,
            error_message="Unable to update module. Please try again.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return flash_redirect("/admin/modules", f"Module {slug} updated.", "success")


def _form_bool(form: Mapping[str, Any], key: str) -> bool:
    value = form.get(key)
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "off"}
    return bool(value)


@app.get(TOTP_ENROLLMENT_PAGE_PATH, response_class=HTMLResponse)
async def totp_enrollment_page(request: Request):
    user, redirect = await _require_authenticated_user(request)
    if redirect:
        return redirect
    assert user is not None
    if not await _user_requires_totp_enrollment(user):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    context = await _build_base_context(
        request,
        user,
        extra={
            "title": "Set up two-factor authentication",
        },
    )
    return templates.TemplateResponse(context["request"], "auth/totp_enrol.html", context)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    session = await session_manager.load_session(request)
    if session:
        user = await user_repo.get_user_by_id(session.user_id)
        if user and await _user_requires_totp_enrollment(user):
            return RedirectResponse(url=TOTP_ENROLLMENT_PAGE_PATH, status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    try:
        user_count = await user_repo.count_users()
    except Exception as exc:  # pragma: no cover - defensive logging for startup issues
        log_error("Failed to determine user count during login", error=str(exc))
        user_count = 1

    if user_count == 0:
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

    context = await _build_public_context(
        request,
        extra={
            "title": "Sign in",
            "verification_success": request.query_params.get("verified") == "1",
        },
    )
    return templates.TemplateResponse(context["request"], "auth/login.html", context)


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    session = await session_manager.load_session(request)
    if session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    context = await _build_public_context(
        request,
        extra={
            "title": "Forgot password",
        },
    )
    return templates.TemplateResponse(context["request"], "auth/forgot_password.html", context)


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ""):
    session = await session_manager.load_session(request)
    if session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    context = await _build_public_context(
        request,
        extra={
            "title": "Reset password",
            "reset_token": token.strip(),
        },
    )
    return templates.TemplateResponse(context["request"], "auth/reset_password.html", context)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    session = await session_manager.load_session(request)
    if session:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    try:
        user_count = await user_repo.count_users()
    except Exception as exc:  # pragma: no cover - defensive logging for startup issues
        log_error("Failed to determine user count during registration", error=str(exc))
        user_count = 1

    is_first_user = user_count == 0

    context = await _build_public_context(
        request,
        extra={
            "title": "Create super administrator" if is_first_user else "Create your account",
            "is_first_user": is_first_user,
        },
    )
    return templates.TemplateResponse(context["request"], "auth/register.html", context)


@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Liveness and readiness probes
# ---------------------------------------------------------------------------
# ``/healthz`` is the cheap "is the process alive" check that nginx,
# systemd, and load balancers can poll constantly.  It must succeed even
# before the database is reachable.
#
# ``/readyz`` is the deeper "is this instance ready to serve traffic"
# check.  It returns 503 until startup has finished, the database is
# reachable, and every registered feature pack is in a healthy state.
# nginx uses this to decide when a blue/green instance is back online
# during a rolling deploy (see ``docs/zero_downtime_upgrades.md``).
_app_ready: bool = False

# Optional dev-only file watcher; started in ``on_startup`` when the
# ``FEATURE_PACK_WATCH`` setting is true.  Held module-level so the
# shutdown hook can cancel it.
_feature_pack_watcher: Any = None


@app.get("/healthz")
async def liveness_probe() -> dict[str, str]:
    """Liveness: the process is running and event loop is responsive."""

    return {"status": "ok"}


@app.get("/readyz")
async def readiness_probe() -> JSONResponse:
    """Readiness: startup has finished, DB is reachable, packs healthy."""

    checks: dict[str, str] = {"startup": "ok" if _app_ready else "pending"}
    ok = _app_ready

    if _app_ready:
        try:
            await db.fetch_one("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc.__class__.__name__}"
            ok = False

    if feature_registry.list() and not feature_registry.all_loaded():
        checks["feature_packs"] = "degraded"
        ok = False
    else:
        checks["feature_packs"] = "ok"

    status_code = HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "not_ready", "checks": checks},
    )
