"""Workspace admission and roles, independent of Google identity verification."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from app.core.config import settings
from app.services import store


def bootstrap():
    with store.session() as db:
        if db.get(store.AccountInitialization, 1):
            return
        admins = {s.strip().lower() for s in settings.ADMIN_EMAILS}
        editors = {s.strip().lower() for s in settings.EDITOR_EMAILS}
        emails = {s.strip().lower() for s in settings.LOGIN_ALLOWED_EMAILS} | admins | editors
        for email in emails:
            if email and not db.get(store.WorkspaceAccount, email):
                db.add(store.WorkspaceAccount(email=email, role='admin' if email in admins else 'editor' if email in editors else 'reader'))
        db.add(store.AccountInitialization(id=1))
        db.commit()


def role_for(email):
    with store.session() as db:
        account = db.get(store.WorkspaceAccount, email.strip().lower())
        return account.role if account and account.active else None


def require_admin():
    from app.services.auth import require_user
    user = require_user()
    if not user.admin:
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
    return dict(email=account.email, role=account.role, active=account.active)


@router.get('')
def list_accounts():
    require_admin()
    with store.session() as db:
        return [serialize(a) for a in db.scalars(select(store.WorkspaceAccount).order_by(store.WorkspaceAccount.email))]


@router.post('', status_code=201)
def create_account(body: AccountInput):
    require_admin()
    with store.session() as db:
        if db.get(store.WorkspaceAccount, body.email):
            raise HTTPException(409, 'Account already exists')
        account = store.WorkspaceAccount(**body.model_dump())
        db.add(account)
        db.commit()
        return serialize(account)


def mutate(email, body=None):
    actor = require_admin()
    email = email.strip().lower()
    with store.session() as db:
        # Serialize administrator mutations to preserve at least one active admin.
        accounts = list(db.scalars(select(store.WorkspaceAccount).order_by(store.WorkspaceAccount.email).with_for_update()))
        account = next((a for a in accounts if a.email == email), None)
        if not account:
            raise HTTPException(404, 'Account not found')
        removing_admin = body is None or not body.active or body.role != 'admin'
        if account.active and account.role == 'admin' and removing_admin:
            if sum(a.active and a.role == 'admin' for a in accounts) <= 1:
                raise HTTPException(409, 'Keep at least one active administrator')
        if actor.email.lower() == email and removing_admin:
            raise HTTPException(409, 'Cannot remove your own access or administrator role')
        if body is None:
            db.delete(account)
        else:
            account.role, account.active = body.role, body.active
        db.commit()
        return serialize(account) if body else {'deleted': True}


@router.patch('/{email}')
def update_account(email: str, body: AccountUpdate):
    return mutate(email, body)


@router.delete('/{email}')
def delete_account(email: str):
    return mutate(email)
