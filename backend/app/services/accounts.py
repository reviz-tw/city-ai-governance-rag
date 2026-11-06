"""Workspace admission and roles, independent of Google identity verification."""
import time
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from app.core.config import settings
from app.services import audit, store


def bootstrap():
    now = time.time()
    with store.session() as db:
        if db.get(store.AccountInitialization, 1):
            return
        admins = {s.strip().lower() for s in settings.ADMIN_EMAILS}
        editors = {s.strip().lower() for s in settings.EDITOR_EMAILS}
        emails = {s.strip().lower() for s in settings.LOGIN_ALLOWED_EMAILS} | admins | editors
        for email in emails:
            if email and not db.get(store.WorkspaceAccount, email):
                db.add(store.WorkspaceAccount(
                    email=email,
                    role='admin' if email in admins else 'editor' if email in editors else 'reader',
                    created_at=now,
                    last_active_at=now,
                    updated_at=now,
                    updated_by='system:bootstrap',
                ))
        db.add(store.AccountInitialization(id=1))
        db.commit()


def _is_idle(account: store.WorkspaceAccount, now: float) -> bool:
    max_idle_seconds = settings.ACCOUNT_MAX_IDLE_DAYS * 86400
    last_seen = account.last_active_at if account.last_active_at is not None else account.created_at
    if last_seen is None:
        return False
    return (now - last_seen) > max_idle_seconds


def _can_disable_account(db, account: store.WorkspaceAccount) -> bool:
    if account.role != 'admin':
        return True
    active_admins = list(db.scalars(
        select(store.WorkspaceAccount).where(
            store.WorkspaceAccount.active.is_(True),
            store.WorkspaceAccount.role == 'admin',
        )
    ))
    return len(active_admins) > 1


def disable_idle_accounts() -> list[str]:
    """Disable accounts exceeding ACCOUNT_MAX_IDLE_DAYS while preserving the last active admin."""
    now = time.time()
    disabled: list[str] = []
    with store.session() as db:
        accounts_list = list(db.scalars(
            select(store.WorkspaceAccount)
            .where(store.WorkspaceAccount.active.is_(True))
            .order_by(store.WorkspaceAccount.email)
            .with_for_update()
        ))
        for account in accounts_list:
            if _is_idle(account, now) and _can_disable_account(db, account):
                last_seen = account.last_active_at if account.last_active_at is not None else account.created_at
                account.active = False
                account.updated_at = now
                account.updated_by = 'system:idle-policy'
                db.flush()
                disabled.append(account.email)
                audit.record(
                    'account.idle_disabled',
                    actor='system:idle-policy',
                    target=account.email,
                    details={'role': account.role, 'last_active_at': last_seen, 'max_idle_days': settings.ACCOUNT_MAX_IDLE_DAYS},
                )
        if disabled:
            db.commit()
    return disabled


def touch_login(email: str):
    now = time.time()
    norm = email.strip().lower()
    with store.session() as db:
        account = db.get(store.WorkspaceAccount, norm)
        if account and account.active:
            account.last_active_at = now
            db.commit()


def role_for(email):
    now = time.time()
    norm = email.strip().lower()
    with store.session() as db:
        account = db.get(store.WorkspaceAccount, norm)
        if not account or not account.active:
            return None
        if _is_idle(account, now) and _can_disable_account(db, account):
            last_seen = account.last_active_at if account.last_active_at is not None else account.created_at
            account.active = False
            account.updated_at = now
            account.updated_by = 'system:idle-policy'
            db.commit()
            audit.record(
                'account.idle_disabled',
                actor='system:idle-policy',
                target=account.email,
                details={'role': account.role, 'last_active_at': last_seen, 'max_idle_days': settings.ACCOUNT_MAX_IDLE_DAYS},
            )
            return None
        role = account.role
        if account.last_active_at is None or (now - account.last_active_at) >= 300:
            account.last_active_at = now
            db.commit()
        return role


def require_admin():
    from app.services.auth import require_user
    user = require_user()
    if not user.admin:
        audit.record('auth.admin.denied', actor=user.email, status='denied')
        raise HTTPException(403, 'Administrator role required')
    return user


class AccountInput(BaseModel):
    email: str = Field(max_length=320)
    role: Literal['reader', 'editor', 'admin'] = 'reader'
    active: bool = True

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        import re
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Invalid email address')
        return value


class AccountUpdate(BaseModel):
    role: Literal['reader', 'editor', 'admin']
    active: bool


router = APIRouter(prefix='/api/accounts')


def serialize(account):
    return dict(
        email=account.email,
        role=account.role,
        active=account.active,
        created_at=account.created_at,
        last_active_at=account.last_active_at,
        updated_at=account.updated_at,
        updated_by=account.updated_by,
    )


@router.get('')
def list_accounts():
    require_admin()
    with store.session() as db:
        return [serialize(a) for a in db.scalars(select(store.WorkspaceAccount).order_by(store.WorkspaceAccount.email))]


@router.get('/audit-logs')
def get_audit_logs(limit: int = Query(100, ge=1, le=500), action: str | None = Query(None, max_length=80)):
    require_admin()
    return audit.list_logs(limit=limit, action=action)


@router.post('', status_code=201)
def create_account(body: AccountInput):
    actor = require_admin()
    now = time.time()
    with store.session() as db:
        if db.get(store.WorkspaceAccount, body.email):
            raise HTTPException(409, 'Account already exists')
        account = store.WorkspaceAccount(
            **body.model_dump(),
            created_at=now,
            last_active_at=now,
            updated_at=now,
            updated_by=actor.email,
        )
        db.add(account)
        db.commit()
        result = serialize(account)
    audit.record(
        'account.created',
        actor=actor.email,
        target=body.email,
        details={'role': body.role, 'active': body.active},
    )
    return result


def mutate(email, body=None):
    actor = require_admin()
    email = email.strip().lower()
    now = time.time()
    with store.session() as db:
        # Serialize administrator mutations to preserve at least one active admin.
        accounts = list(db.scalars(select(store.WorkspaceAccount).order_by(store.WorkspaceAccount.email).with_for_update()))
        account = next((a for a in accounts if a.email == email), None)
        if not account:
            raise HTTPException(404, 'Account not found')
        previous_role, previous_active = account.role, account.active
        removing_admin = body is None or not body.active or body.role != 'admin'
        if account.active and account.role == 'admin' and removing_admin:
            if sum(a.active and a.role == 'admin' for a in accounts) <= 1:
                raise HTTPException(409, 'Keep at least one active administrator')
        if actor.email.lower() == email and removing_admin:
            raise HTTPException(409, 'Cannot remove your own access or administrator role')
        if body is None:
            db.delete(account)
            result = {'deleted': True}
        else:
            account.role, account.active = body.role, body.active
            account.updated_at = now
            account.updated_by = actor.email
            if body.active:
                account.last_active_at = now
            result = serialize(account)
        db.commit()
    if body is None:
        audit.record(
            'account.deleted',
            actor=actor.email,
            target=email,
            details={'previous_role': previous_role, 'previous_active': previous_active},
        )
    else:
        action = 'account.deactivated' if previous_active and not body.active else 'account.updated'
        audit.record(
            action,
            actor=actor.email,
            target=email,
            details={
                'previous_role': previous_role,
                'role': body.role,
                'previous_active': previous_active,
                'active': body.active,
            },
        )
    return result


@router.patch('/{email}')
def update_account(email: str, body: AccountUpdate):
    return mutate(email, body)


@router.delete('/{email}')
def delete_account(email: str):
    return mutate(email)
