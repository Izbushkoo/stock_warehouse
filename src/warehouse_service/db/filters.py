"""Database query filters for soft delete and other common filters."""

from typing import TypeVar, Type
from sqlalchemy import and_
from sqlmodel import SQLModel, select, Select

T = TypeVar('T', bound=SQLModel)


def exclude_soft_deleted(query: Select[T]) -> Select[T]:
    """
    Add filter to exclude soft deleted records from query.
    
    Args:
        query: SQLModel select query
        
    Returns:
        Query with soft delete filter applied
    """
    # Get the model class from the query
    model_class = query.column_descriptions[0]['type']
    
    # Check if model has deleted_at field
    if hasattr(model_class, 'deleted_at'):
        return query.where(model_class.deleted_at.is_(None))
    
    return query


def only_soft_deleted(query: Select[T]) -> Select[T]:
    """
    Add filter to only include soft deleted records from query.
    
    Args:
        query: SQLModel select query
        
    Returns:
        Query with soft delete filter applied to show only deleted records
    """
    # Get the model class from the query
    model_class = query.column_descriptions[0]['type']
    
    # Check if model has deleted_at field
    if hasattr(model_class, 'deleted_at'):
        return query.where(model_class.deleted_at.is_not(None))
    
    return query


def active_warehouses_only(query: Select[T]) -> Select[T]:
    """
    Filter query to only include active warehouses.
    
    Args:
        query: SQLModel select query
        
    Returns:
        Query filtered for active warehouses only
    """
    from warehouse_service.models.unified import Warehouse
    
    # Get the model class from the query
    model_class = query.column_descriptions[0]['type']
    
    if model_class == Warehouse:
        return query.where(
            and_(
                Warehouse.is_active.is_(True),
                Warehouse.deleted_at.is_(None)
            )
        )
    
    return query


def active_items_only(query: Select[T]) -> Select[T]:
    """
    Filter query to only include active items.
    
    Args:
        query: SQLModel select query
        
    Returns:
        Query filtered for active items only
    """
    from warehouse_service.models.unified import Item
    
    # Get the model class from the query
    model_class = query.column_descriptions[0]['type']
    
    if model_class == Item:
        return query.where(
            and_(
                Item.item_status == "active",
                Item.deleted_at.is_(None)
            )
        )
    
    return query


def user_created_resources(query: Select[T], user_id: str) -> Select[T]:
    """
    Filter query to only include resources created by specific user.
    
    Args:
        query: SQLModel select query
        user_id: UUID string of the user
        
    Returns:
        Query filtered for user's created resources
    """
    # Get the model class from the query
    model_class = query.column_descriptions[0]['type']
    
    # Check different created_by field names
    if hasattr(model_class, 'created_by'):
        return query.where(model_class.created_by == user_id)
    elif hasattr(model_class, 'created_by_user_id'):
        return query.where(model_class.created_by_user_id == user_id)
    
    return query


def apply_standard_filters(query: Select[T], include_deleted: bool = False) -> Select[T]:
    """
    Apply standard filters to a query (exclude soft deleted, active only, etc.).
    
    Args:
        query: SQLModel select query
        include_deleted: Whether to include soft deleted records
        
    Returns:
        Query with standard filters applied
    """
    if not include_deleted:
        query = exclude_soft_deleted(query)
    
    # Apply model-specific active filters
    query = active_warehouses_only(query)
    query = active_items_only(query)
    
    return query