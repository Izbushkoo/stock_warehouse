"""Administrative views for unified warehouse RBAC management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from warehouse_service.auth.dependencies import get_session
from warehouse_service.models.unified import AppUser, WarehouseAccessGrant, Warehouse, ItemGroup

templates = Jinja2Templates(directory="src/warehouse_service/templates")
admin_router = APIRouter(prefix="/admin", tags=["admin"])


def get_current_user_from_request(request: Request) -> AppUser:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, 'user', None)


@admin_router.get("/", response_class=HTMLResponse, summary="Admin Dashboard")
def admin_dashboard(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    # Get basic stats
    user_count = len(session.exec(select(AppUser)).all())
    warehouse_count = len(session.exec(select(Warehouse)).all())
    access_grant_count = len(session.exec(select(WarehouseAccessGrant)).all())
    
    stats = {
        "users": user_count,
        "warehouses": warehouse_count,
        "access_grants": access_grant_count,
    }
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unified Warehouse Admin</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .card {{ background: #f5f5f5; padding: 20px; margin: 10px 0; border-radius: 5px; }}
            .stat {{ display: inline-block; margin: 10px 20px; }}
            .nav {{ margin: 20px 0; }}
            .nav a {{ margin-right: 20px; color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>🏭 Unified Warehouse Admin</h1>
        
        <div class="nav">
            <a href="/admin/users">👥 Users</a>
            <a href="/admin/warehouses">🏭 Warehouses</a>
            <a href="/admin/access-grants">🔐 Access Grants</a>
            <a href="/api/v1/warehouses">📡 API</a>
            <a href="/docs">📚 API Docs</a>
        </div>
        
        <div class="card">
            <h2>📊 System Statistics</h2>
            <div class="stat"><strong>Users:</strong> {stats['users']}</div>
            <div class="stat"><strong>Warehouses:</strong> {stats['warehouses']}</div>
            <div class="stat"><strong>Access Grants:</strong> {stats['access_grants']}</div>
        </div>
        
        <div class="card">
            <h2>🚀 Quick Actions</h2>
            <p>• <a href="/admin/users">Manage Users</a> - View and manage system users</p>
            <p>• <a href="/admin/warehouses">Manage Warehouses</a> - View warehouse configuration</p>
            <p>• <a href="/admin/access-grants">Manage Access</a> - Configure user permissions</p>
        </div>
        
        <div class="card">
            <h2>ℹ️ System Info</h2>
            <p><strong>Schema:</strong> Unified Warehouse Database Schema</p>
            <p><strong>RBAC:</strong> Granular access control by warehouse and item group</p>
            <p><strong>Features:</strong> Stock movements, Sales orders, Analytics, Audit trail</p>
        </div>
    </body>
    </html>
    """)


@admin_router.get("/users", response_class=HTMLResponse, summary="List Users")
def list_users(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    users = session.exec(select(AppUser).order_by(AppUser.user_email)).all()
    
    user_rows = []
    for user in users:
        # Count access grants for this user
        grants = session.exec(select(WarehouseAccessGrant).where(
            WarehouseAccessGrant.app_user_id == user.app_user_id
        )).all()
        
        user_rows.append({
            "id": str(user.app_user_id),
            "email": user.user_email,
            "display_name": user.user_display_name,
            "is_active": user.is_active,
            "grant_count": len(grants),
            "last_login": user.last_login_at.isoformat() if user.last_login_at else "Never",
        })
    
    users_html = ""
    for user in user_rows:
        status = "✅ Active" if user["is_active"] else "❌ Inactive"
        users_html += f"""
        <tr>
            <td>{user['email']}</td>
            <td>{user['display_name']}</td>
            <td>{status}</td>
            <td>{user['grant_count']}</td>
            <td>{user['last_login']}</td>
        </tr>
        """
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Users - Unified Warehouse Admin</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .nav {{ margin: 20px 0; }}
            .nav a {{ margin-right: 20px; color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/admin">🏠 Dashboard</a>
            <a href="/admin/warehouses">🏭 Warehouses</a>
            <a href="/admin/access-grants">🔐 Access Grants</a>
        </div>
        
        <h1>👥 System Users</h1>
        
        <table>
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Display Name</th>
                    <th>Status</th>
                    <th>Access Grants</th>
                    <th>Last Login</th>
                </tr>
            </thead>
            <tbody>
                {users_html}
            </tbody>
        </table>
    </body>
    </html>
    """)


@admin_router.get("/warehouses", response_class=HTMLResponse, summary="List Warehouses")
def list_warehouses(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    warehouses = session.exec(select(Warehouse).order_by(Warehouse.warehouse_code)).all()
    
    warehouse_rows = []
    for warehouse in warehouses:
        warehouse_rows.append({
            "id": str(warehouse.warehouse_id),
            "code": warehouse.warehouse_code,
            "name": warehouse.warehouse_name,
            "address": warehouse.warehouse_address or "—",
            "is_active": warehouse.is_active,
        })
    
    warehouses_html = ""
    for wh in warehouse_rows:
        status = "✅ Active" if wh["is_active"] else "❌ Inactive"
        warehouses_html += f"""
        <tr>
            <td>{wh['code']}</td>
            <td>{wh['name']}</td>
            <td>{wh['address']}</td>
            <td>{status}</td>
        </tr>
        """
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Warehouses - Unified Warehouse Admin</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .nav {{ margin: 20px 0; }}
            .nav a {{ margin-right: 20px; color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/admin">🏠 Dashboard</a>
            <a href="/admin/users">👥 Users</a>
            <a href="/admin/access-grants">🔐 Access Grants</a>
        </div>
        
        <h1>🏭 Warehouses</h1>
        
        <table>
            <thead>
                <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Address</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {warehouses_html}
            </tbody>
        </table>
    </body>
    </html>
    """)


@admin_router.get("/access-grants", response_class=HTMLResponse, summary="List Access Grants")
def list_access_grants(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    grants = session.exec(select(WarehouseAccessGrant)).all()
    
    grant_rows = []
    for grant in grants:
        user = session.get(AppUser, grant.app_user_id)
        warehouse = session.get(Warehouse, grant.warehouse_id)
        
        permissions = []
        if grant.can_read:
            permissions.append("Read")
        if grant.can_write:
            permissions.append("Write")
        if grant.can_approve:
            permissions.append("Approve")
        
        grant_rows.append({
            "user_email": user.user_email if user else "Unknown",
            "warehouse_code": warehouse.warehouse_code if warehouse else "Unknown",
            "scope_type": grant.scope_type,
            "permissions": ", ".join(permissions) if permissions else "None",
        })
    
    grants_html = ""
    for grant in grant_rows:
        grants_html += f"""
        <tr>
            <td>{grant['user_email']}</td>
            <td>{grant['warehouse_code']}</td>
            <td>{grant['scope_type']}</td>
            <td>{grant['permissions']}</td>
        </tr>
        """
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Access Grants - Unified Warehouse Admin</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .nav {{ margin: 20px 0; }}
            .nav a {{ margin-right: 20px; color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/admin">🏠 Dashboard</a>
            <a href="/admin/users">👥 Users</a>
            <a href="/admin/warehouses">🏭 Warehouses</a>
        </div>
        
        <h1>🔐 Access Grants</h1>
        
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th>Warehouse</th>
                    <th>Scope</th>
                    <th>Permissions</th>
                </tr>
            </thead>
            <tbody>
                {grants_html}
            </tbody>
        </table>
    </body>
    </html>
    """)


__all__ = ["admin_router"]
