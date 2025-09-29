#!/usr/bin/env python3
"""Initialize Celery Beat database tables."""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy_celery_beat.models import ModelBase
from warehouse_service.config import get_settings

def main():
    """Initialize Celery Beat tables."""
    settings = get_settings()
    
    # Create engine with schema translation
    engine = create_engine(
        settings.database.url,
        execution_options={"schema_translate_map": {"celery_schema": "celery_schema"}}
    )
    
    print("Creating Celery Beat tables...")
    
    # Create all tables
    ModelBase.metadata.create_all(engine, checkfirst=True)
    
    print("Celery Beat tables created successfully!")

if __name__ == "__main__":
    main()