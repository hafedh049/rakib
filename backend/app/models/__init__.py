"""Beanie document registry.

Every Document class must be listed in ALL_DOCUMENTS or Beanie will not build its
indexes. Later phases append to this list as their models land.
"""

from beanie import Document

from app.models.analysis_trace import AnalysisTrace
from app.models.complaint import Complaint
from app.models.counter import Counter
from app.models.department import Department
from app.models.refresh_token import RefreshToken
from app.models.rule import Rule
from app.models.user import Role, User, role_at_least

ALL_DOCUMENTS: list[type[Document]] = [
    User,
    RefreshToken,
    Department,
    Complaint,
    Counter,
    Rule,
    AnalysisTrace,
]

__all__ = [
    "ALL_DOCUMENTS",
    "AnalysisTrace",
    "Complaint",
    "Counter",
    "Department",
    "RefreshToken",
    "Role",
    "Rule",
    "User",
    "role_at_least",
]
