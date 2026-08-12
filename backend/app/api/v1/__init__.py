from fastapi import APIRouter

from app.api.v1 import auth, complaints, departments, rules, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(complaints.router)
api_router.include_router(departments.router)
api_router.include_router(rules.router)
api_router.include_router(users.router)

__all__ = ["api_router"]
