import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.proxy.router import ProxyRouter
from src.proxy.adapter_base import Adapter, AdapterResponse, AdapterError
from src.proxy.context import RequestContext
from src.proxy.dependencies import ProxyDependencies, set_proxy_deps
from src.domain import AnthropicRequest, ErrorType, RETRYABLE_ERRORS, RoutingStrategy
from src.proxy.circuit_breaker import CircuitBreaker

@pytest.fixture
def mock_circuit_breaker():
    cb = Mock(spec=CircuitBreaker)
    # Default behavior: closed (is_open=False)
    cb.is_open.return_value = False
    return cb

@pytest.fixture
def mock_plan_adapter():
    adapter = Mock(spec=Adapter)
    adapter.invoke = AsyncMock()
    return adapter

@pytest.fixture
def mock_bedrock_adapter():
    adapter = Mock(spec=Adapter)
    adapter.invoke = AsyncMock()
    return adapter

@pytest.fixture
def proxy_router(mock_plan_adapter, mock_bedrock_adapter):
    return ProxyRouter(mock_plan_adapter, mock_bedrock_adapter)

@pytest.fixture
def request_context():
    ctx = Mock(spec=RequestContext)
    ctx.user_id = uuid4()
    ctx.access_key_id = uuid4()
    ctx.has_bedrock_key = True # Default to having a key
    ctx.routing_strategy = RoutingStrategy.PLAN_FIRST
    return ctx

@pytest.fixture
def anthropic_request():
    return Mock(spec=AnthropicRequest)

@pytest.fixture(autouse=True)
def setup_dependencies(mock_circuit_breaker):
    deps = ProxyDependencies(circuit_breaker=mock_circuit_breaker)
    set_proxy_deps(deps)
    yield
    # No explicit teardown needed as dependencies are reset per test or handled by fixture scope usually, 
    # but here we rely on the fixture re-setting it for the next test.

@pytest.mark.asyncio
async def test_circuit_open_no_bedrock_key(proxy_router, request_context, anthropic_request, mock_circuit_breaker, mock_plan_adapter, mock_bedrock_adapter):
    """Circuit Open + Bedrock key 없음 → 즉시 503 반환"""
    mock_circuit_breaker.is_open.return_value = True
    request_context.has_bedrock_key = False
    
    response = await proxy_router.route(request_context, anthropic_request)
    
    assert response.status_code == 503
    assert response.error_type == "overloaded_error"
    mock_plan_adapter.invoke.assert_not_called()
    mock_bedrock_adapter.invoke.assert_not_called()

@pytest.mark.asyncio
async def test_plan_success(proxy_router, request_context, anthropic_request, mock_circuit_breaker, mock_plan_adapter, mock_bedrock_adapter):
    """Plan 성공 → record_success 호출, Bedrock 미호출"""
    mock_circuit_breaker.is_open.return_value = False
    mock_plan_adapter.invoke.return_value = AdapterResponse(
        response=Mock(), usage=Mock()
    )
    
    response = await proxy_router.route(request_context, anthropic_request)
    
    assert response.success is True
    assert response.provider == "plan"
    assert response.is_fallback is False
    mock_circuit_breaker.record_success.assert_called_with(str(request_context.access_key_id))
    mock_bedrock_adapter.invoke.assert_not_called()

@pytest.mark.asyncio
async def test_plan_failure_retryable(proxy_router, request_context, anthropic_request, mock_circuit_breaker, mock_plan_adapter, mock_bedrock_adapter):
    """Plan 실패 (retryable=True, error_type=RETRYABLE) → Bedrock 호출"""
    mock_circuit_breaker.is_open.return_value = False
    error_type = list(RETRYABLE_ERRORS)[0]
    mock_plan_adapter.invoke.return_value = AdapterError(
        error_type=error_type, status_code=429, message="Rate limit", retryable=True
    )
    mock_bedrock_adapter.invoke.return_value = AdapterResponse(
        response=Mock(), usage=Mock()
    )
    
    # Ensure bedrock key is available
    request_context.has_bedrock_key = True

    response = await proxy_router.route(request_context, anthropic_request)
    
    assert response.success is True
    assert response.provider == "bedrock"
    assert response.is_fallback is True
    mock_circuit_breaker.record_failure.assert_called_with(str(request_context.access_key_id), error_type)
    mock_bedrock_adapter.invoke.assert_called_once()

@pytest.mark.asyncio
async def test_plan_failure_non_retryable_flag(proxy_router, request_context, anthropic_request, mock_circuit_breaker, mock_plan_adapter, mock_bedrock_adapter):
    """Plan 실패 (retryable=False, error_type=RETRYABLE) → Bedrock 미호출"""
    mock_circuit_breaker.is_open.return_value = False
    error_type = list(RETRYABLE_ERRORS)[0] # Even if error type is retryable
    mock_plan_adapter.invoke.return_value = AdapterError(
        error_type=error_type, status_code=400, message="Bad Request", retryable=False
    )
    
    response = await proxy_router.route(request_context, anthropic_request)
    
    assert response.success is False
    assert response.provider == "plan"
    assert response.is_fallback is False
    mock_bedrock_adapter.invoke.assert_not_called()

@pytest.mark.asyncio
async def test_plan_failure_non_retryable_error_type(proxy_router, request_context, anthropic_request, mock_circuit_breaker, mock_plan_adapter, mock_bedrock_adapter):
    """Plan 실패 (retryable=True, error_type=non-retryable) → Bedrock 미호출"""
    mock_circuit_breaker.is_open.return_value = False
    error_type = ErrorType.CLIENT_ERROR # Not in RETRYABLE_ERRORS
    mock_plan_adapter.invoke.return_value = AdapterError(
        error_type=error_type, status_code=400, message="Bad Request", retryable=True
    )
    
    response = await proxy_router.route(request_context, anthropic_request)
    
    assert response.success is False
    assert response.provider == "plan"
    assert response.is_fallback is False
    mock_bedrock_adapter.invoke.assert_not_called()

@pytest.mark.asyncio
async def test_circuit_open_bedrock_success(proxy_router, request_context, anthropic_request, mock_circuit_breaker, mock_plan_adapter, mock_bedrock_adapter):
    """Circuit Open + Bedrock 성공 시 is_fallback이 False인지 확인 (Plan 시도 안함)"""
    mock_circuit_breaker.is_open.return_value = True
    request_context.has_bedrock_key = True
    mock_bedrock_adapter.invoke.return_value = AdapterResponse(
        response=Mock(), usage=Mock()
    )
    
    response = await proxy_router.route(request_context, anthropic_request)
    
    assert response.success is True
    assert response.provider == "bedrock"
    assert response.is_fallback is False # Important: Plan was NOT attempted
    mock_plan_adapter.invoke.assert_not_called()
    mock_bedrock_adapter.invoke.assert_called_once()

@pytest.mark.asyncio
async def test_bedrock_only_routes_directly_to_bedrock(proxy_router, request_context, anthropic_request, mock_plan_adapter, mock_bedrock_adapter):
    """bedrock_only → Bedrock만 호출"""
    request_context.routing_strategy = RoutingStrategy.BEDROCK_ONLY
    request_context.has_bedrock_key = True
    mock_bedrock_adapter.invoke.return_value = AdapterResponse(
        response=Mock(), usage=Mock()
    )

    response = await proxy_router.route(request_context, anthropic_request)

    assert response.success is True
    assert response.provider == "bedrock"
    assert response.is_fallback is False
    mock_plan_adapter.invoke.assert_not_called()
    mock_bedrock_adapter.invoke.assert_called_once()

@pytest.mark.asyncio
async def test_bedrock_only_without_key_returns_503(proxy_router, request_context, anthropic_request, mock_plan_adapter, mock_bedrock_adapter):
    """bedrock_only + Bedrock key 없음 → 503"""
    request_context.routing_strategy = RoutingStrategy.BEDROCK_ONLY
    request_context.has_bedrock_key = False

    response = await proxy_router.route(request_context, anthropic_request)

    assert response.success is False
    assert response.status_code == 503
    assert response.error_type == "api_error"
    mock_plan_adapter.invoke.assert_not_called()
    mock_bedrock_adapter.invoke.assert_not_called()


# ============================================================================
# Kent Beck style: Bedrock Only with None PlanAdapter
# ============================================================================

@pytest.fixture
def proxy_router_without_plan_adapter(mock_bedrock_adapter):
    """PlanAdapter 없이 ProxyRouter 생성 (Bedrock Only 전용)"""
    return ProxyRouter(None, mock_bedrock_adapter)


@pytest.mark.asyncio
async def test_bedrock_only_works_with_none_plan_adapter(
    proxy_router_without_plan_adapter, request_context, anthropic_request, mock_bedrock_adapter
):
    """Bedrock Only 라우팅은 plan_adapter=None으로도 정상 동작한다"""
    # Arrange
    request_context.routing_strategy = RoutingStrategy.BEDROCK_ONLY
    request_context.has_bedrock_key = True
    mock_bedrock_adapter.invoke.return_value = AdapterResponse(
        response=Mock(), usage=Mock()
    )

    # Act
    response = await proxy_router_without_plan_adapter.route(request_context, anthropic_request)

    # Assert
    assert response.success is True
    assert response.provider == "bedrock"
    assert response.is_fallback is False
    mock_bedrock_adapter.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_bedrock_only_with_none_plan_adapter_returns_503_without_bedrock_key(
    proxy_router_without_plan_adapter, request_context, anthropic_request, mock_bedrock_adapter
):
    """Bedrock Only + plan_adapter=None + Bedrock key 없음 → 503"""
    # Arrange
    request_context.routing_strategy = RoutingStrategy.BEDROCK_ONLY
    request_context.has_bedrock_key = False

    # Act
    response = await proxy_router_without_plan_adapter.route(request_context, anthropic_request)

    # Assert
    assert response.success is False
    assert response.status_code == 503
    assert response.error_type == "api_error"
    mock_bedrock_adapter.invoke.assert_not_called()


@pytest.mark.asyncio
async def test_bedrock_only_with_none_plan_adapter_handles_bedrock_error(
    proxy_router_without_plan_adapter, request_context, anthropic_request, mock_bedrock_adapter
):
    """Bedrock Only + plan_adapter=None + Bedrock 실패 → 에러 반환"""
    # Arrange
    request_context.routing_strategy = RoutingStrategy.BEDROCK_ONLY
    request_context.has_bedrock_key = True
    mock_bedrock_adapter.invoke.return_value = AdapterError(
        error_type=ErrorType.SERVER_ERROR, status_code=500, message="Bedrock error", retryable=True
    )

    # Act
    response = await proxy_router_without_plan_adapter.route(request_context, anthropic_request)

    # Assert
    assert response.success is False
    assert response.provider == "bedrock"
    assert response.status_code == 500
    mock_bedrock_adapter.invoke.assert_called_once()
