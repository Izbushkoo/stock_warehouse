"""API routes for catalog (item group) management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from warehouse_service.auth.dependencies import get_current_user, get_session
from warehouse_service.auth.permissions_v2 import (
    PermissionManager, ResourceType, PermissionLevel,
    require_system_admin
)
from warehouse_service.models.unified import AppUser, ItemGroup, Warehouse

router = APIRouter(prefix="/api/catalogs", tags=["Catalog Management"])


class CreateCatalogRequest(BaseModel):
    """Request to create new catalog (item group)."""
    code: str
    name: str
    description: Optional[str] = None


class UpdateCatalogRequest(BaseModel):
    """Request to update catalog."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CatalogResponse(BaseModel):
    """Catalog response model."""
    item_group_id: str
    item_group_code: str
    item_group_name: str
    item_group_description: Optional[str]
    is_active: bool
    created_at: str
    created_by: str
    warehouses_count: int


@router.get("/", response_model=List[CatalogResponse])
async def list_catalogs(
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all catalogs accessible to current user."""
    pm = PermissionManager(session)
    
    print(f"User {current_user.user_email} requesting catalogs")
    print(f"Is system admin: {pm.is_system_admin(current_user.app_user_id)}")
    
    if pm.is_system_admin(current_user.app_user_id):
        # System admin sees all catalogs
        catalogs = session.exec(select(ItemGroup)).all()
        print(f"System admin - found {len(catalogs)} catalogs")
    else:
        # Regular user sees only catalogs they have access to
        catalogs = pm.get_user_item_groups(current_user.app_user_id)
        print(f"Regular user - found {len(catalogs)} accessible catalogs")
    
    result = []
    for catalog in catalogs:
        # Count warehouses in this catalog
        warehouses_count = len(session.exec(
            select(Warehouse).where(Warehouse.item_group_id == catalog.item_group_id)
        ).all())
        
        result.append(CatalogResponse(
            item_group_id=str(catalog.item_group_id),
            item_group_code=catalog.item_group_code,
            item_group_name=catalog.item_group_name,
            item_group_description=catalog.item_group_description,
            is_active=catalog.is_active,
            created_at=catalog.created_at.isoformat(),
            created_by=str(catalog.created_by),
            warehouses_count=warehouses_count
        ))
    
    return result


@router.post("/", response_model=CatalogResponse)
async def create_catalog(
    request: CreateCatalogRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create new catalog. Only system admins can create catalogs."""
    pm = PermissionManager(session)
    
    if not pm.can_create_item_group(current_user.app_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can create catalogs"
        )
    
    # Check if code already exists
    existing = session.exec(
        select(ItemGroup).where(ItemGroup.item_group_code == request.code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Catalog with code '{request.code}' already exists"
        )
    
    # Create catalog
    catalog = ItemGroup(
        item_group_code=request.code,
        item_group_name=request.name,
        item_group_description=request.description,
        is_active=True,
        created_by=current_user.app_user_id
    )
    
    session.add(catalog)
    session.commit()
    session.refresh(catalog)
    
    # Automatically grant OWNER permission to creator (unless they're system admin)
    if not pm.is_system_admin(current_user.app_user_id):
        pm.grant_permission(
            user_id=current_user.app_user_id,
            resource_type=ResourceType.ITEM_GROUP,
            resource_id=catalog.item_group_id,
            permission_level=PermissionLevel.OWNER,
            granted_by=current_user.app_user_id  # Self-granted
        )
        session.commit()
    
    return CatalogResponse(
        item_group_id=str(catalog.item_group_id),
        item_group_code=catalog.item_group_code,
        item_group_name=catalog.item_group_name,
        item_group_description=catalog.item_group_description,
        is_active=catalog.is_active,
        created_at=catalog.created_at.isoformat(),
        created_by=str(catalog.created_by),
        warehouses_count=0
    )


@router.get("/{catalog_id}")
async def get_catalog(
    catalog_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get catalog details."""
    catalog = session.get(ItemGroup, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog not found"
        )
    
    pm = PermissionManager(session)
    
    # Check if user has access to this catalog
    if not pm.is_system_admin(current_user.app_user_id):
        if not pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, catalog_id, PermissionLevel.READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this catalog"
            )
    
    # Get warehouses in this catalog
    warehouses = session.exec(
        select(Warehouse).where(Warehouse.item_group_id == catalog_id)
    ).all()
    
    return {
        "catalog": {
            "item_group_id": str(catalog.item_group_id),
            "item_group_code": catalog.item_group_code,
            "item_group_name": catalog.item_group_name,
            "item_group_description": catalog.item_group_description,
            "is_active": catalog.is_active,
            "created_at": catalog.created_at.isoformat(),
            "created_by": str(catalog.created_by)
        },
        "warehouses": [
            {
                "warehouse_id": str(w.warehouse_id),
                "warehouse_code": w.warehouse_code,
                "warehouse_name": w.warehouse_name,
                "warehouse_address": w.warehouse_address,
                "is_active": w.is_active
            }
            for w in warehouses
        ]
    }


@router.put("/{catalog_id}")
async def update_catalog(
    catalog_id: UUID,
    request: UpdateCatalogRequest,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update catalog. Requires ADMIN permission on catalog."""
    catalog = session.get(ItemGroup, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog not found"
        )
    
    pm = PermissionManager(session)
    
    # Check permissions
    if not pm.is_system_admin(current_user.app_user_id):
        if not pm.has_permission(current_user.app_user_id, ResourceType.ITEM_GROUP, catalog_id, PermissionLevel.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required to update catalog"
            )
    
    # Update fields
    if request.name is not None:
        catalog.item_group_name = request.name
    if request.description is not None:
        catalog.item_group_description = request.description
    if request.is_active is not None:
        catalog.is_active = request.is_active
    
    session.add(catalog)
    session.commit()
    session.refresh(catalog)
    
    return {
        "message": "Catalog updated successfully",
        "catalog": {
            "item_group_id": str(catalog.item_group_id),
            "item_group_code": catalog.item_group_code,
            "item_group_name": catalog.item_group_name,
            "item_group_description": catalog.item_group_description,
            "is_active": catalog.is_active
        }
    }


@router.delete("/{catalog_id}")
async def delete_catalog(
    catalog_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Soft delete catalog. Only system admins can delete catalogs."""
    catalog = session.get(ItemGroup, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog not found"
        )
    
    pm = PermissionManager(session)
    
    if not pm.is_system_admin(current_user.app_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can delete catalogs"
        )
    
    # Check if catalog has warehouses
    warehouses_count = len(session.exec(
        select(Warehouse).where(Warehouse.item_group_id == catalog_id)
    ).all())
    
    if warehouses_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete catalog with {warehouses_count} warehouses. Delete warehouses first."
        )
    
    # Soft delete
    from datetime import datetime
    catalog.deleted_at = datetime.utcnow()
    catalog.deleted_by = current_user.app_user_id
    catalog.is_active = False
    
    session.add(catalog)
    session.commit()
    
    return {
        "message": f"Catalog '{catalog.item_group_name}' has been deleted"
    }


@router.post("/{catalog_id}/warehouses")
async def create_warehouse_in_catalog(
    catalog_id: UUID,
    warehouse_code: str,
    warehouse_name: str,
    warehouse_address: Optional[str] = None,
    current_user: AppUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create warehouse in catalog. Requires WRITE permission on catalog."""
    catalog = session.get(ItemGroup, catalog_id)
    if not catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog not found"
        )
    
    pm = PermissionManager(session)
    
    # Check permissions
    if not pm.can_create_warehouse(current_user.app_user_id, catalog_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create warehouse in this catalog"
        )
    
    # Check if warehouse code already exists
    existing = session.exec(
        select(Warehouse).where(Warehouse.warehouse_code == warehouse_code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Warehouse with code '{warehouse_code}' already exists"
        )
    
    # Create warehouse
    warehouse = Warehouse(
        warehouse_code=warehouse_code,
        warehouse_name=warehouse_name,
        warehouse_address=warehouse_address,
        item_group_id=catalog_id,
        is_active=True,
        created_by=current_user.app_user_id
    )
    
    session.add(warehouse)
    session.commit()
    session.refresh(warehouse)
    
    return {
        "message": "Warehouse created successfully",
        "warehouse": {
            "warehouse_id": str(warehouse.warehouse_id),
            "warehouse_code": warehouse.warehouse_code,
            "warehouse_name": warehouse.warehouse_name,
            "warehouse_address": warehouse.warehouse_address,
            "item_group_id": str(warehouse.item_group_id),
            "is_active": warehouse.is_active
        }
    }