"""Celery tasks for user lifecycle management and cleanup."""

from celery import Celery
from sqlmodel import Session

from warehouse_service.config import get_settings
from warehouse_service.db.engine import get_engine
from warehouse_service.auth.user_lifecycle import UserLifecycleService
from warehouse_service.tasks.celery_app import celery


@celery.task(name="cleanup_old_deleted_users")
def cleanup_old_deleted_users(days_threshold: int = 30):
    """
    Permanently delete users and their resources that have been soft deleted for more than threshold days.
    
    Args:
        days_threshold: Number of days after soft deletion to permanently delete (default: 30)
    """
    settings = get_settings()
    engine = get_engine()
    
    with Session(engine) as session:
        lifecycle_service = UserLifecycleService(session)
        
        # Get users eligible for permanent deletion
        eligible_users = lifecycle_service.get_users_for_permanent_deletion(days_threshold)
        
        deleted_count = 0
        for user in eligible_users:
            try:
                success = lifecycle_service.permanently_delete_user(user.app_user_id)
                if success:
                    deleted_count += 1
                    print(f"Permanently deleted user: {user.user_email}")
                else:
                    print(f"Failed to delete user: {user.user_email}")
            except Exception as e:
                print(f"Error deleting user {user.user_email}: {str(e)}")
                # Continue with other users even if one fails
                continue
    
    print(f"Cleanup completed. Permanently deleted {deleted_count} users and their resources.")
    return {"deleted_users": deleted_count, "threshold_days": days_threshold}


@celery.task(name="deactivate_user_with_resources")
def deactivate_user_with_resources(user_id: str, deactivated_by: str, reason: str = None):
    """
    Celery task to deactivate user and soft delete all their resources.
    
    Args:
        user_id: UUID string of user to deactivate
        deactivated_by: UUID string of user performing the deactivation
        reason: Optional reason for deactivation
    """
    from uuid import UUID
    
    settings = get_settings()
    engine = get_engine()
    
    with Session(engine) as session:
        lifecycle_service = UserLifecycleService(session)
        
        try:
            user_uuid = UUID(user_id)
            deactivated_by_uuid = UUID(deactivated_by)
            
            success = lifecycle_service.deactivate_user(user_uuid, deactivated_by_uuid, reason)
            
            if success:
                print(f"Successfully deactivated user {user_id} and soft deleted their resources")
                return {"success": True, "user_id": user_id, "reason": reason}
            else:
                print(f"Failed to deactivate user {user_id} - user not found")
                return {"success": False, "error": "User not found", "user_id": user_id}
                
        except ValueError as e:
            print(f"Invalid UUID format: {str(e)}")
            return {"success": False, "error": f"Invalid UUID format: {str(e)}", "user_id": user_id}
        except Exception as e:
            print(f"Error deactivating user {user_id}: {str(e)}")
            return {"success": False, "error": str(e), "user_id": user_id}


@celery.task(name="reactivate_user_with_resources")
def reactivate_user_with_resources(user_id: str, reactivated_by: str):
    """
    Celery task to reactivate user and restore all their soft deleted resources.
    
    Args:
        user_id: UUID string of user to reactivate
        reactivated_by: UUID string of user performing the reactivation
    """
    from uuid import UUID
    
    settings = get_settings()
    engine = get_engine()
    
    with Session(engine) as session:
        lifecycle_service = UserLifecycleService(session)
        
        try:
            user_uuid = UUID(user_id)
            reactivated_by_uuid = UUID(reactivated_by)
            
            success = lifecycle_service.reactivate_user(user_uuid, reactivated_by_uuid)
            
            if success:
                print(f"Successfully reactivated user {user_id} and restored their resources")
                return {"success": True, "user_id": user_id}
            else:
                print(f"Failed to reactivate user {user_id} - user not found")
                return {"success": False, "error": "User not found", "user_id": user_id}
                
        except ValueError as e:
            print(f"Invalid UUID format: {str(e)}")
            return {"success": False, "error": f"Invalid UUID format: {str(e)}", "user_id": user_id}
        except Exception as e:
            print(f"Error reactivating user {user_id}: {str(e)}")
            return {"success": False, "error": str(e), "user_id": user_id}