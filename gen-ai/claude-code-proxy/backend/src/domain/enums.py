from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class KeyStatus(str, Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"


class RoutingStrategy(str, Enum):
    PLAN_FIRST = "plan_first"
    BEDROCK_ONLY = "bedrock_only"


class ErrorType(str, Enum):
    # Plan errors
    RATE_LIMIT = "rate_limit"
    USAGE_LIMIT = "usage_limit"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    # Bedrock errors
    BEDROCK_AUTH_ERROR = "bedrock_auth_error"
    BEDROCK_QUOTA_EXCEEDED = "bedrock_quota_exceeded"
    BEDROCK_VALIDATION = "bedrock_validation"
    BEDROCK_MODEL_ERROR = "bedrock_model_error"
    BEDROCK_UNAVAILABLE = "bedrock_unavailable"


# Errors that trigger circuit breaker
CIRCUIT_TRIGGERS = {ErrorType.RATE_LIMIT, ErrorType.SERVER_ERROR}

# Errors that allow fallback to Bedrock
RETRYABLE_ERRORS = {
    ErrorType.RATE_LIMIT,
    ErrorType.USAGE_LIMIT,
    ErrorType.SERVER_ERROR,
    ErrorType.TIMEOUT,
    ErrorType.NETWORK_ERROR,
}
