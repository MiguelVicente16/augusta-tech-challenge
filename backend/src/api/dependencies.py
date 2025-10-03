"""
FastAPI dependencies

Centralized dependency injection to avoid circular imports.
"""

from ..database.service import DatabaseService

# Global database service instance (set by main.py on startup)
_db_service: DatabaseService = None


def set_db_service(db_service: DatabaseService):
    """Set the global database service instance"""
    global _db_service
    _db_service = db_service


def get_db_service() -> DatabaseService:
    """Dependency for getting database service"""
    return _db_service
