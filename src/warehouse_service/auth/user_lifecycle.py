"""User lifecycle management including soft delete and restoration."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, select

from warehouse_service.models.unified import (
    AppUser, Warehouse, ItemGroup, Item, SalesOrder, ReturnOrder
)


class UserLifecycleService:
    """Service for managing user lifecycle including soft delete and restoration."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def deactivate_user(self, user_id: UUID, deactivated_by: UUID, reason: Optional[str] = None) -> bool:
        """
        Deactivate user and soft delete all their created resources.
        
        Args:
            user_id: ID of user to deactivate
            deactivated_by: ID of user performing the deactivation
            reason: Optional reason for deactivation
            
        Returns:
            True if successful, False if user not found
        """
        user = self.session.get(AppUser, user_id)
        if not user:
            return False
        
        now = datetime.utcnow()
        
        # Deactivate the user
        user.is_active = False
        user.updated_at = now
        
        # Soft delete all resources created by this user
        self._soft_delete_user_resources(user_id, deactivated_by, now)
        
        self.session.add(user)
        self.session.commit()
        
        return True
    
    def reactivate_user(self, user_id: UUID, reactivated_by: UUID) -> bool:
        """
        Reactivate user and restore all their soft deleted resources.
        
        Args:
            user_id: ID of user to reactivate
            reactivated_by: ID of user performing the reactivation
            
        Returns:
            True if successful, False if user not found
        """
        user = self.session.get(AppUser, user_id)
        if not user:
            return False
        
        now = datetime.utcnow()
        
        # Reactivate the user
        user.is_active = True
        user.updated_at = now
        
        # Restore all soft deleted resources created by this user
        self._restore_user_resources(user_id, now)
        
        self.session.add(user)
        self.session.commit()
        
        return True
    
    def get_users_for_permanent_deletion(self, days_threshold: int = 30) -> List[AppUser]:
        """
        Get users that have been deactivated for more than the threshold and should be permanently deleted.
        
        Args:
            days_threshold: Number of days after deactivation to consider for permanent deletion
            
        Returns:
            List of users eligible for permanent deletion
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Find users who have been inactive and have soft deleted resources older than threshold
        users = self.session.exec(
            select(AppUser).where(
                AppUser.is_active.is_(False),
                AppUser.updated_at < cutoff_date
            )
        ).all()
        
        # Filter users who have soft deleted resources older than threshold
        eligible_users = []
        for user in users:
            has_old_deleted_resources = self._has_old_deleted_resources(user.app_user_id, cutoff_date)
            if has_old_deleted_resources:
                eligible_users.append(user)
        
        return eligible_users
    
    def permanently_delete_user(self, user_id: UUID) -> bool:
        """
        Permanently delete user and all their soft deleted resources.
        
        Args:
            user_id: ID of user to permanently delete
            
        Returns:
            True if successful, False if user not found
        """
        user = self.session.get(AppUser, user_id)
        if not user:
            return False
        
        # Permanently delete all soft deleted resources
        self._permanently_delete_user_resources(user_id)
        
        # Delete the user
        self.session.delete(user)
        self.session.commit()
        
        return True
    
    def _soft_delete_user_resources(self, user_id: UUID, deleted_by: UUID, deleted_at: datetime):
        """Soft delete all resources created by the user."""
        
        # Soft delete warehouses
        self.session.execute(
            text("""
                UPDATE warehouse 
                SET deleted_at = :deleted_at, deleted_by = :deleted_by 
                WHERE created_by = :user_id AND deleted_at IS NULL
            """),
            {"user_id": str(user_id), "deleted_by": str(deleted_by), "deleted_at": deleted_at}
        )
        
        # Soft delete item groups
        self.session.execute(
            text("""
                UPDATE item_group 
                SET deleted_at = :deleted_at, deleted_by = :deleted_by 
                WHERE created_by = :user_id AND deleted_at IS NULL
            """),
            {"user_id": str(user_id), "deleted_by": str(deleted_by), "deleted_at": deleted_at}
        )
        
        # Soft delete items
        self.session.execute(
            text("""
                UPDATE item 
                SET deleted_at = :deleted_at, deleted_by = :deleted_by 
                WHERE created_by = :user_id AND deleted_at IS NULL
            """),
            {"user_id": str(user_id), "deleted_by": str(deleted_by), "deleted_at": deleted_at}
        )
        
        # Soft delete sales orders
        self.session.execute(
            text("""
                UPDATE sales_order 
                SET deleted_at = :deleted_at, deleted_by = :deleted_by 
                WHERE created_by_user_id = :user_id AND deleted_at IS NULL
            """),
            {"user_id": str(user_id), "deleted_by": str(deleted_by), "deleted_at": deleted_at}
        )
        
        # Soft delete return orders
        self.session.execute(
            text("""
                UPDATE return_order 
                SET deleted_at = :deleted_at, deleted_by = :deleted_by 
                WHERE created_by_user_id = :user_id AND deleted_at IS NULL
            """),
            {"user_id": str(user_id), "deleted_by": str(deleted_by), "deleted_at": deleted_at}
        )
    
    def _restore_user_resources(self, user_id: UUID, updated_at: datetime):
        """Restore all soft deleted resources created by the user."""
        
        # Restore warehouses
        self.session.execute(
            text("""
                UPDATE warehouse 
                SET deleted_at = NULL, deleted_by = NULL, updated_at = :updated_at 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id), "updated_at": updated_at}
        )
        
        # Restore item groups
        self.session.execute(
            text("""
                UPDATE item_group 
                SET deleted_at = NULL, deleted_by = NULL, updated_at = :updated_at 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id), "updated_at": updated_at}
        )
        
        # Restore items
        self.session.execute(
            text("""
                UPDATE item 
                SET deleted_at = NULL, deleted_by = NULL, updated_at = :updated_at 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id), "updated_at": updated_at}
        )
        
        # Restore sales orders
        self.session.execute(
            text("""
                UPDATE sales_order 
                SET deleted_at = NULL, deleted_by = NULL, updated_at = :updated_at 
                WHERE created_by_user_id = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id), "updated_at": updated_at}
        )
        
        # Restore return orders
        self.session.execute(
            text("""
                UPDATE return_order 
                SET deleted_at = NULL, deleted_by = NULL, updated_at = :updated_at 
                WHERE created_by_user_id = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id), "updated_at": updated_at}
        )
    
    def _has_old_deleted_resources(self, user_id: UUID, cutoff_date: datetime) -> bool:
        """Check if user has soft deleted resources older than cutoff date."""
        
        # Check warehouses
        result = self.session.execute(
            text("""
                SELECT 1 FROM warehouse 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL AND deleted_at < :cutoff_date 
                LIMIT 1
            """),
            {"user_id": str(user_id), "cutoff_date": cutoff_date}
        ).first()
        
        if result:
            return True
        
        # Check item groups
        result = self.session.execute(
            text("""
                SELECT 1 FROM item_group 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL AND deleted_at < :cutoff_date 
                LIMIT 1
            """),
            {"user_id": str(user_id), "cutoff_date": cutoff_date}
        ).first()
        
        if result:
            return True
        
        # Check items
        result = self.session.execute(
            text("""
                SELECT 1 FROM item 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL AND deleted_at < :cutoff_date 
                LIMIT 1
            """),
            {"user_id": str(user_id), "cutoff_date": cutoff_date}
        ).first()
        
        if result:
            return True
        
        # Check sales orders
        result = self.session.execute(
            text("""
                SELECT 1 FROM sales_order 
                WHERE created_by_user_id = :user_id AND deleted_at IS NOT NULL AND deleted_at < :cutoff_date 
                LIMIT 1
            """),
            {"user_id": str(user_id), "cutoff_date": cutoff_date}
        ).first()
        
        if result:
            return True
        
        # Check return orders
        result = self.session.execute(
            text("""
                SELECT 1 FROM return_order 
                WHERE created_by_user_id = :user_id AND deleted_at IS NOT NULL AND deleted_at < :cutoff_date 
                LIMIT 1
            """),
            {"user_id": str(user_id), "cutoff_date": cutoff_date}
        ).first()
        
        return result is not None
    
    def _permanently_delete_user_resources(self, user_id: UUID):
        """Permanently delete all soft deleted resources created by the user."""
        
        # Delete return orders first (due to foreign key constraints)
        self.session.execute(
            text("""
                DELETE FROM return_order 
                WHERE created_by_user_id = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id)}
        )
        
        # Delete sales orders
        self.session.execute(
            text("""
                DELETE FROM sales_order 
                WHERE created_by_user_id = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id)}
        )
        
        # Delete items
        self.session.execute(
            text("""
                DELETE FROM item 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id)}
        )
        
        # Delete warehouses
        self.session.execute(
            text("""
                DELETE FROM warehouse 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id)}
        )
        
        # Delete item groups
        self.session.execute(
            text("""
                DELETE FROM item_group 
                WHERE created_by = :user_id AND deleted_at IS NOT NULL
            """),
            {"user_id": str(user_id)}
        )