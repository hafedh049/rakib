from typing import Annotated, Any

from fastapi import APIRouter, Query, Response

from app.deps import AgentUser, SupervisorUser
from app.services import analytics_service, reporting_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

Window = Annotated[int, Query(ge=1, le=365, description="Fenetre en jours")]


@router.get("/overview")
async def overview(_: AgentUser, days: Window = 30) -> dict[str, Any]:
    return await analytics_service.overview(days)


@router.get("/by-category")
async def by_category(_: AgentUser, days: Window = 30) -> list[dict[str, Any]]:
    return await analytics_service.by_category(days)


@router.get("/volume")
async def volume(_: AgentUser, days: Window = 30) -> list[dict[str, Any]]:
    return await analytics_service.volume_by_day(days)


@router.get("/agents")
async def agents(_: SupervisorUser, days: Window = 30) -> list[dict[str, Any]]:
    return await analytics_service.agents(days)


@router.get("/engine")
async def engine(_: SupervisorUser) -> dict[str, Any]:
    return await analytics_service.engine_report()


@router.get("/rules")
async def rules(_: SupervisorUser, days: Window = 30) -> list[dict[str, Any]]:
    return await analytics_service.rules_report(days)


@router.get("/kb")
async def kb(_: SupervisorUser) -> list[dict[str, Any]]:
    return await analytics_service.kb_report()


@router.get("/supervision")
async def supervision(_: AgentUser) -> dict[str, Any]:
    return await analytics_service.supervision_board()


# ------------------------------------------------------------- BCT reporting
@router.get("/declaration/{year}")
async def declaration(year: int, _: SupervisorUser) -> dict[str, Any]:
    """The ROGS760 annual declaration, as data (Annexe 3)."""
    return await reporting_service.collect(year)


@router.get("/declaration/{year}/xml")
async def declaration_xml(year: int, _: SupervisorUser) -> Response:
    """The same declaration in the transmission format Annexe 2 fixes: XML."""
    report = await reporting_service.collect(year)
    return Response(
        content=reporting_service.to_xml(report),
        media_type="application/xml",
        headers={
            "Content-Disposition":
                f'attachment; filename="{report["code"]}_{year}.xml"'
        },
    )
