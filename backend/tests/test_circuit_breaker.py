import pytest
from unittest.mock import patch, AsyncMock

from app.resilience import AsyncCircuitBreaker, CircuitState, CircuitOpenError


async def async_success():
    return "ok"


async def async_fail():
    raise RuntimeError("fail")


@pytest.fixture
def breaker():
    return AsyncCircuitBreaker("test", fail_max=3, reset_timeout=0.5)


@pytest.mark.asyncio
async def test_initial_state_is_closed(breaker):
    assert breaker.state == CircuitState.CLOSED
    assert breaker.fail_count == 0


@pytest.mark.asyncio
async def test_success_resets_fail_count(breaker):
    # Accumulate 2 failures (below threshold)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)
    assert breaker.fail_count == 2

    # Success resets count
    result = await breaker.call(async_success)
    assert result == "ok"
    assert breaker.fail_count == 0
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_fail_max(breaker):
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)

    assert breaker.state == CircuitState.OPEN
    assert breaker.fail_count == 3


@pytest.mark.asyncio
async def test_open_circuit_raises_without_calling(breaker):
    # Open the circuit
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)

    # Verify it raises CircuitOpenError without calling underlying func
    mock_func = AsyncMock()
    with pytest.raises(CircuitOpenError) as exc_info:
        await breaker.call(mock_func)

    assert exc_info.value.name == "test"
    assert exc_info.value.fail_count == 3
    mock_func.assert_not_called()


@pytest.mark.asyncio
async def test_half_open_after_cooldown(breaker):
    # Open the circuit
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)
    assert breaker.state == CircuitState.OPEN

    # Simulate cooldown expiry via time mock
    with patch("app.resilience.time.monotonic") as mock_time:
        # Return a time far in the future
        mock_time.return_value = breaker._last_failure_time + breaker.reset_timeout + 1
        assert breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_success_closes(breaker):
    # Open the circuit
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)

    # Transition to HALF_OPEN
    breaker._state = CircuitState.HALF_OPEN

    # Successful probe closes
    result = await breaker.call(async_success)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.fail_count == 0


@pytest.mark.asyncio
async def test_half_open_failure_reopens(breaker):
    # Open the circuit
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)

    # Transition to HALF_OPEN
    breaker._state = CircuitState.HALF_OPEN
    old_failure_time = breaker._last_failure_time

    # Failed probe reopens and resets timer (D-04)
    with patch("app.resilience.time.monotonic", return_value=old_failure_time + 10):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)

    assert breaker.state == CircuitState.OPEN
    assert breaker._last_failure_time == old_failure_time + 10


@pytest.mark.asyncio
async def test_circuit_open_error_not_counted(breaker):
    # Accumulate 2 failures
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(async_fail)
    assert breaker.fail_count == 2

    # CircuitOpenError from nested call doesn't increment count
    async def raises_circuit_error():
        raise CircuitOpenError("inner", 0)

    with pytest.raises(CircuitOpenError):
        await breaker.call(raises_circuit_error)

    assert breaker.fail_count == 2  # unchanged


@pytest.mark.asyncio
async def test_last_failure_time_tracked(breaker):
    assert breaker._last_failure_time is None

    with pytest.raises(RuntimeError):
        await breaker.call(async_fail)

    assert breaker._last_failure_time is not None


def test_singletons_exist():
    from app.resilience import vnstock_breaker, cafef_breaker, gemini_breaker

    assert isinstance(vnstock_breaker, AsyncCircuitBreaker)
    assert isinstance(cafef_breaker, AsyncCircuitBreaker)
    assert isinstance(gemini_breaker, AsyncCircuitBreaker)
    assert vnstock_breaker.name == "vnstock"
    assert cafef_breaker.name == "cafef"
    assert gemini_breaker.name == "gemini"
