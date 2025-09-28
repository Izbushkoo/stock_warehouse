"""Administrative views for RBAC management."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from warehouse_service.db.engine import session_scope
from warehouse_service.models import Permission, Role

TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


def get_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session


@admin_router.get("/roles", response_class=HTMLResponse, summary="Список ролей")
def list_roles(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    roles = session.exec(select(Role).order_by(Role.name)).all()
    role_rows = []
    for role in roles:
        permissions = list(role.permissions or [])
        users = list(role.users or [])
        role_rows.append(
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permission_count": len(permissions),
                "user_count": len(users),
                "updated_at": role.updated_at.isoformat() if role.updated_at else None,
            }
        )

    return TEMPLATES.TemplateResponse(
        "admin/roles/list.html",
        {
            "request": request,
            "title": "Роли",
            "roles": role_rows,
        },
    )


@admin_router.get(
    "/roles/{role_id}",
    response_class=HTMLResponse,
    summary="Детали роли",
)
def role_detail(
    role_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    role = session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    permissions = [
        {
            "id": assignment.permission.id if assignment.permission else None,
            "scope": assignment.permission.scope if assignment.permission else "—",
            "action": assignment.permission.action if assignment.permission else "—",
            "description": assignment.permission.description if assignment.permission else None,
            "assigned_at": assignment.created_at.isoformat()
            if assignment.created_at
            else None,
        }
        for assignment in sorted(
            list(role.permissions or []),
            key=lambda item: (
                item.permission.scope if item.permission else "",
                item.permission.action if item.permission else "",
            ),
        )
    ]

    members = [
        {
            "id": membership.user.id if membership.user else None,
            "email": membership.user.email if membership.user else "—",
            "assigned_at": membership.created_at.isoformat()
            if membership.created_at
            else None,
        }
        for membership in sorted(
            list(role.users or []),
            key=lambda item: (item.user.email if item.user else ""),
        )
    ]

    role_payload = {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }

    return TEMPLATES.TemplateResponse(
        "admin/roles/detail.html",
        {
            "request": request,
            "title": f"Роль · {role.name}",
            "role": role_payload,
            "permissions": permissions,
            "members": members,
        },
    )


@admin_router.get(
    "/permissions",
    response_class=HTMLResponse,
    summary="Список разрешений",
)
def list_permissions(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    permissions = session.exec(
        select(Permission).order_by(Permission.scope, Permission.action)
    ).all()
    permission_rows = []
    for permission in permissions:
        roles = list(permission.roles or [])
        permission_rows.append(
            {
                "id": permission.id,
                "scope": permission.scope,
                "action": permission.action,
                "description": permission.description,
                "role_count": len(roles),
                "updated_at": permission.updated_at.isoformat()
                if permission.updated_at
                else None,
            }
        )

    return TEMPLATES.TemplateResponse(
        "admin/permissions/list.html",
        {
            "request": request,
            "title": "Разрешения",
            "permissions": permission_rows,
        },
    )


__all__ = ["admin_router"]
