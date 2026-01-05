from fastapi import APIRouter, Depends, Query

from ..domain import PricingListResponse, ModelPricingResponse
from ..domain.pricing import PricingConfig
from .deps import require_admin

router = APIRouter(prefix="/api/pricing", tags=["pricing"], dependencies=[Depends(require_admin)])


@router.get("/models", response_model=PricingListResponse)
async def get_model_pricing(region: str = Query(default="ap-northeast-2")) -> PricingListResponse:
    pricing_list = PricingConfig.get_all_pricing(region)

    return PricingListResponse(
        region=region,
        models=[
            ModelPricingResponse(
                model_id=pricing.model_id,
                region=pricing.region,
                input_price=str(pricing.input_price_per_million),
                output_price=str(pricing.output_price_per_million),
                cache_write_price=str(pricing.cache_write_price_per_million),
                cache_read_price=str(pricing.cache_read_price_per_million),
                effective_date=pricing.effective_date.isoformat(),
            )
            for pricing in pricing_list
        ],
    )


@router.post("/reload", status_code=204)
async def reload_pricing() -> None:
    PricingConfig.reload()
