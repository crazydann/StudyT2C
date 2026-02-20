# services/db/__init__.py
"""
DB access layer modules (split from db_service.py).
Only internal imports should use these modules directly.

External code should continue to import from services.db_service
(which re-exports public functions).
"""