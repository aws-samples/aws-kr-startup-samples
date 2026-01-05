from dataclasses import dataclass
from uuid import UUID

from ..domain import RoutingStrategy


@dataclass
class RequestContext:
    """Authenticated request context."""

    request_id: str
    user_id: UUID
    access_key_id: UUID
    access_key_prefix: str
    bedrock_region: str
    bedrock_model: str
    has_bedrock_key: bool
    routing_strategy: RoutingStrategy = RoutingStrategy.PLAN_FIRST
