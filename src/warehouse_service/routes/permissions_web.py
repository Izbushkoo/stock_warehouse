"""Web routes for permission management interface."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from warehouse_service.auth.dependencies import get_current_user, get_session
from warehouse_service.auth.permissions_v2 import PermissionManager, ResourceType, PermissionLevel
from warehouse_service.models.unified import AppUser, ItemGroup, Warehouse


router = APIRouter(prefix="/admin/permissions", tags=["permissions-web"])
templates = Jinja2Templates(directory="src/warehouse_service/templates")


@router.get("/", response_class=HTMLResponse, summary="Permissions Dashboard")
def permissions_dashboard(
    request: Request,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Main permissions management dashboard."""
    
    pm = PermissionManager(session)
    
    # Check if user is system admin
    is_system_admin = pm.is_system_admin(current_user.app_user_id)
    
    # Get user's item groups
    item_groups = pm.get_user_item_groups(current_user.app_user_id)
    item_groups_data = []
    
    for ig in item_groups:
        permission_level = "read"
        if pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.OWNER):
            permission_level = "owner"
        elif pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.ADMIN):
            permission_level = "admin"
        elif pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, ig.item_group_id, PermissionLevel.WRITE):
            permission_level = "write"
        
        item_groups_data.append({
            "item_group_id": str(ig.item_group_id),
            "item_group_code": ig.item_group_code,
            "item_group_name": ig.item_group_name,
            "permission_level": permission_level
        })
    
    # Get user's warehouses
    warehouses = pm.get_user_warehouses(current_user.app_user_id)
    warehouses_data = []
    
    for w in warehouses:
        permission_level = "read"
        if pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, w.warehouse_id, PermissionLevel.ADMIN):
            permission_level = "admin"
        elif pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, w.warehouse_id, PermissionLevel.WRITE):
            permission_level = "write"
        
        warehouses_data.append({
            "warehouse_id": str(w.warehouse_id),
            "warehouse_code": w.warehouse_code,
            "warehouse_name": w.warehouse_name,
            "item_group_id": str(w.item_group_id),
            "permission_level": permission_level
        })
    
    return templates.TemplateResponse("admin/permissions/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "is_system_admin": is_system_admin,
        "item_groups": item_groups_data,
        "warehouses": warehouses_data
    })


@router.get("/item-groups/{item_group_id}", response_class=HTMLResponse, summary="Item Group Details")
def item_group_details(
    item_group_id: UUID,
    request: Request,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """View item group details and warehouses."""
    
    pm = PermissionManager(session)
    
    # Check permission
    if not pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, item_group_id, PermissionLevel.READ):
        return RedirectResponse("/admin/permissions/", status_code=302)
    
    # Get item group
    item_group = session.get(ItemGroup, item_group_id)
    if not item_group:
        return RedirectResponse("/admin/permissions/", status_code=302)
    
    # Get warehouses in this item group
    warehouses = pm.get_user_warehouses(current_user.app_user_id, item_group_id)
    
    # Check if user can manage this item group
    can_manage = pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, item_group_id, PermissionLevel.ADMIN)
    can_create_warehouses = pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, item_group_id, PermissionLevel.WRITE)
    
    return templates.TemplateResponse("admin/permissions/item_group_details.html", {
        "request": request,
        "current_user": current_user,
        "item_group": item_group,
        "warehouses": warehouses,
        "can_manage": can_manage,
        "can_create_warehouses": can_create_warehouses
    })


@router.get("/item-groups/{item_group_id}/manage", response_class=HTMLResponse, summary="Manage Item Group")
def manage_item_group(
    item_group_id: UUID,
    request: Request,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Manage item group permissions and warehouses."""
    
    pm = PermissionManager(session)
    
    # Check admin permission
    if not pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, item_group_id, PermissionLevel.ADMIN):
        return RedirectResponse(f"/admin/permissions/item-groups/{item_group_id}", status_code=302)
    
    # Get item group
    item_group = session.get(ItemGroup, item_group_id)
    if not item_group:
        return RedirectResponse("/admin/permissions/", status_code=302)
    
    # Get permissions for this item group
    permissions = pm.get_resource_permissions(ResourceType.ITEM_GROUP, item_group_id)
    
    # Get warehouses
    warehouses = pm.get_user_warehouses(current_user.app_user_id, item_group_id)
    
    return templates.TemplateResponse("admin/permissions/manage_item_group.html", {
        "request": request,
        "current_user": current_user,
        "item_group": item_group,
        "permissions": permissions,
        "warehouses": warehouses
    })


@router.get("/warehouses/{warehouse_id}/manage", response_class=HTMLResponse, summary="Manage Warehouse")
def manage_warehouse(
    warehouse_id: UUID,
    request: Request,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Manage warehouse permissions."""
    
    pm = PermissionManager(session)
    
    # Check admin permission
    if not pm.has_permission(current_user.app_user_id, ResourceType.WAREHOUSE, warehouse_id, PermissionLevel.ADMIN):
        return RedirectResponse("/admin/permissions/", status_code=302)
    
    # Get warehouse
    warehouse = session.get(Warehouse, warehouse_id)
    if not warehouse:
        return RedirectResponse("/admin/permissions/", status_code=302)
    
    # Get permissions for this warehouse
    permissions = pm.get_resource_permissions(ResourceType.WAREHOUSE, warehouse_id)
    
    return templates.TemplateResponse("admin/permissions/manage_warehouse.html", {
        "request": request,
        "current_user": current_user,
        "warehouse": warehouse,
        "permissions": permissions
    })