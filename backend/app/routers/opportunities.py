from fastapi import APIRouter, Query
from app.services.opportunity_service import list_opportunities

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("")
def get_opportunities(
    keyword: str = "", opportunity_type: str = "all", region: str = "",
    organization: str = "", status: str = "", minimum_amount: float | None = None,
    maximum_amount: float | None = None, limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return list_opportunities(keyword, opportunity_type, region, organization, status, minimum_amount, maximum_amount, limit, offset)


