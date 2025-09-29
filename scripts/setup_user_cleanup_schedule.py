#!/usr/bin/env python3
"""Script to setup periodic user cleanup schedule in Celery Beat."""

import sys
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlmodel import Session
from warehouse_service.config import get_settings
from warehouse_service.db.engine import get_engine

# Import Celery Beat models
try:
    from sqlalchemy_celery_beat.models import PeriodicTask, CrontabSchedule
    from sqlalchemy_celery_beat.session import SessionManager
except ImportError:
    print("Error: sqlalchemy_celery_beat not installed")
    sys.exit(1)


def setup_user_cleanup_schedule():
    """Setup periodic task for user cleanup."""
    
    settings = get_settings()
    
    # Create session manager for Celery Beat
    session_manager = SessionManager()
    session = session_manager.create_session(settings.database_url, schema='celery_schema')
    
    try:
        # Create crontab schedule for daily cleanup at 2 AM
        crontab_schedule = CrontabSchedule(
            minute='0',
            hour='2',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='UTC'
        )
        
        # Check if schedule already exists
        existing_schedule = session.query(CrontabSchedule).filter_by(
            minute='0',
            hour='2',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='UTC'
        ).first()
        
        if existing_schedule:
            crontab_schedule = existing_schedule
            print("Using existing crontab schedule")
        else:
            session.add(crontab_schedule)
            session.commit()
            session.refresh(crontab_schedule)
            print("Created new crontab schedule for daily 2 AM")
        
        # Create periodic task for user cleanup
        task_name = "Daily User Cleanup"
        existing_task = session.query(PeriodicTask).filter_by(name=task_name).first()
        
        if existing_task:
            print(f"Periodic task '{task_name}' already exists")
            # Update the task
            existing_task.task = 'cleanup_old_deleted_users'
            existing_task.crontab = crontab_schedule
            existing_task.args = '[30]'  # 30 days threshold
            existing_task.kwargs = '{}'
            existing_task.enabled = True
            existing_task.description = 'Automatically cleanup users and resources soft deleted more than 30 days ago'
            session.add(existing_task)
        else:
            # Create new task
            periodic_task = PeriodicTask(
                name=task_name,
                task='cleanup_old_deleted_users',
                crontab=crontab_schedule,
                args='[30]',  # 30 days threshold
                kwargs='{}',
                enabled=True,
                description='Automatically cleanup users and resources soft deleted more than 30 days ago'
            )
            session.add(periodic_task)
            print(f"Created new periodic task: {task_name}")
        
        session.commit()
        
        print("✅ User cleanup schedule setup completed!")
        print("📅 Schedule: Daily at 2:00 AM UTC")
        print("🗑️  Cleanup threshold: 30 days")
        print("📋 Task: cleanup_old_deleted_users")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error setting up user cleanup schedule: {str(e)}")
        raise
    finally:
        session.close()


def list_cleanup_schedules():
    """List all user cleanup related schedules."""
    
    settings = get_settings()
    
    # Create session manager for Celery Beat
    session_manager = SessionManager()
    session = session_manager.create_session(settings.database_url, schema='celery_schema')
    
    try:
        # Find all cleanup related tasks
        cleanup_tasks = session.query(PeriodicTask).filter(
            PeriodicTask.task.like('%cleanup%')
        ).all()
        
        if not cleanup_tasks:
            print("No cleanup tasks found")
            return
        
        print("Current cleanup schedules:")
        print("=" * 50)
        
        for task in cleanup_tasks:
            print(f"Name: {task.name}")
            print(f"Task: {task.task}")
            print(f"Enabled: {task.enabled}")
            print(f"Args: {task.args}")
            print(f"Description: {task.description}")
            if task.crontab:
                print(f"Schedule: {task.crontab}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Error listing cleanup schedules: {str(e)}")
        raise
    finally:
        session.close()


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_cleanup_schedules()
    else:
        setup_user_cleanup_schedule()


if __name__ == "__main__":
    main()