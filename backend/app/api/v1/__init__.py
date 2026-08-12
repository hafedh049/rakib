from fastapi import APIRouter

from app.api.v1 import (
    admin_ml,
    auth,
    complaints,
    departments,
    events,
    kb,
    rules,
    users,
)

api_router = APIRouter()
api_router.include_router(admin_ml.router)
api_router.include_router(auth.router)
api_router.include_router(complaints.router)
api_router.include_router(departments.router)
api_router.include_router(events.router)
api_router.include_router(kb.router)
api_router.include_router(rules.router)
api_router.include_router(users.router)

__all__ = ["api_router"]
