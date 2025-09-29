#!/usr/bin/env python3
"""
Скрипт для предоставления системных прав администратора пользователю.
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from warehouse_service.db import session_scope
from warehouse_service.models.unified import AppUser, Permission
from warehouse_service.auth.permissions_v2 import ResourceType, PermissionLevel
from sqlmodel import select


def grant_system_admin(user_email: str):
    """Предоставить системные права администратора пользователю."""
    
    with session_scope() as session:
        # Найти пользователя по email
        user = session.exec(
            select(AppUser).where(AppUser.user_email == user_email)
        ).first()
        
        if not user:
            print(f"❌ Пользователь с email {user_email} не найден")
            return False
        
        print(f"✅ Найден пользователь: {user.user_display_name} ({user.user_email})")
        
        # Проверить, есть ли уже системные права
        existing_permission = session.exec(
            select(Permission).where(
                Permission.app_user_id == user.app_user_id,
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.is_active == True
            )
        ).first()
        
        if existing_permission:
            print(f"✅ У пользователя уже есть системные права: {existing_permission.permission_level}")
            return True
        
        # Создать системное разрешение
        # Используем специальный UUID для системного ресурса
        system_resource_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        
        permission = Permission(
            app_user_id=user.app_user_id,
            resource_type=ResourceType.SYSTEM.value,
            resource_id=system_resource_id,
            permission_level=PermissionLevel.ADMIN.value,
            granted_by=user.app_user_id,  # Самоназначение для первого админа
            granted_at=datetime.utcnow(),
            is_active=True
        )
        
        session.add(permission)
        session.commit()
        
        print(f"✅ Системные права администратора предоставлены пользователю {user_email}")
        return True


def list_system_admins():
    """Показать всех системных администраторов."""
    
    with session_scope() as session:
        # Найти всех пользователей с системными правами
        admins = session.exec(
            select(AppUser, Permission).join(Permission).where(
                Permission.resource_type == ResourceType.SYSTEM.value,
                Permission.permission_level.in_([PermissionLevel.ADMIN.value, PermissionLevel.OWNER.value]),
                Permission.is_active == True
            )
        ).all()
        
        if not admins:
            print("❌ Системные администраторы не найдены")
            return
        
        print("✅ Системные администраторы:")
        for user, permission in admins:
            print(f"  - {user.user_display_name} ({user.user_email}) - {permission.permission_level}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python grant_system_admin.py <email>           # Предоставить права")
        print("  python grant_system_admin.py --list            # Показать админов")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_system_admins()
    else:
        email = sys.argv[1]
        grant_system_admin(email)