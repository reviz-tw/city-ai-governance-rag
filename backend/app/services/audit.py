"""Unified security & administrative audit logging (Cloud Logging JSON + durable DB table)."""
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import logging
import time
import uuid
from fastapi import Request
from sqlalchemy import select
from app.services import store

logger = logging.getLogger("city-governance-audit")

request_context: ContextVar[dict | None] = ContextVar("audit_request_context", default=None)


def client_ip(request: Request | None) -> str:
    if request is None:
        ctx = request_context.get()
        return (ctx or {}).get("source_ip", "")
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:100]
    if request.client and request.client.host:
        return str(request.client.host)[:100]
    return ""


def request_path(request: Request | None) -> str:
    if request is None:
        ctx = request_context.get()
        return (ctx or {}).get("path", "")
    return str(request.scope.get("path", ""))[:300]


def record(
    action: str,
    *,
    actor: str | None = None,
    target: str = "",
    status: str = "succeeded",
    details: dict | None = None,
    request: Request | None = None,
    persist: bool = True,
) -> dict:
    """Emit a single-format UTC structured audit event and persist to audit_logs."""
    if actor is None:
        from app.services.auth import current_user
        user = current_user.get()
        actor = user.email if user else "anonymous"
    now = time.time()
    iso_utc = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ip = client_ip(request)
    path = request_path(request)
    safe_details = dict(details or {})
    entry_id = uuid.uuid4().hex
    canonical = json.dumps(
        {
            "id": entry_id,
            "timestamp_utc": iso_utc,
            "created_at": round(now, 6),
            "action": action,
            "actor": actor,
            "target": target,
            "status": status,
            "source_ip": ip,
            "path": path,
            "details": safe_details,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload = {
        "event": "security_audit",
        "id": entry_id,
        "timestamp_utc": iso_utc,
        "created_at": round(now, 6),
        "action": action,
        "actor": actor,
        "target": target,
        "status": status,
        "source_ip": ip,
        "path": path,
        "details": safe_details,
        "entry_hash": digest,
    }
    logger.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    if persist:
        try:
            with store.session() as db:
                db.add(
                    store.AuditLog(
                        id=entry_id,
                        action=action[:80],
                        actor=actor[:320],
                        target=str(target)[:320],
                        status=status[:30],
                        source_ip=ip[:100],
                        path=path[:300],
                        details=safe_details,
                        entry_hash=digest,
                        created_at=now,
                    )
                )
                db.commit()
        except Exception as exc:
            logger.warning(json.dumps({"event": "security_audit_persist_warning", "error": type(exc).__name__}))
    return payload


def list_logs(limit: int = 100, action: str | None = None) -> list[dict]:
    limit = max(1, min(limit, 500))
    with store.session() as db:
        stmt = select(store.AuditLog).order_by(store.AuditLog.created_at.desc()).limit(limit)
        if action:
            stmt = stmt.where(store.AuditLog.action == action)
        rows = list(db.scalars(stmt))
        return [
            {
                "id": r.id,
                "timestamp_utc": datetime.fromtimestamp(r.created_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "created_at": r.created_at,
                "action": r.action,
                "actor": r.actor,
                "target": r.target,
                "status": r.status,
                "source_ip": r.source_ip,
                "path": r.path,
                "details": r.details,
                "entry_hash": r.entry_hash,
            }
            for r in rows
        ]
