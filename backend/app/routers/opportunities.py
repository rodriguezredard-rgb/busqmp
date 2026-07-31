from fastapi import APIRouter, Query, Response
from app.services.opportunity_service import count_opportunities, list_categories, list_opportunities

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("/categories")
def get_categories(search: str = "", limit: int = Query(200, ge=1, le=500)):
    return list_categories(search, limit)


@router.get("")
def get_opportunities(
    response: Response,
    keyword: str = "", opportunity_type: str = "all", region: str = "",
    organization: str = "", status: str = "", minimum_amount: float | None = None,
    maximum_amount: float | None = None, limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    response.headers["X-Total-Count"] = str(count_opportunities(
        keyword, opportunity_type, region, organization, status, minimum_amount, maximum_amount,
    ))
    return list_opportunities(keyword, opportunity_type, region, organization, status, minimum_amount, maximum_amount, limit, offset)


