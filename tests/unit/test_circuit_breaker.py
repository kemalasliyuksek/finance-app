"""Circuit breaker testleri."""

import asyncio

import pytest

from src.core.circuit_breaker import CircuitBreaker, CircuitState
from src.core.exceptions import BinanceAPIError


class TestCircuitBreaker:
    def _make_cb(self, threshold=3, timeout=1.0):
        return CircuitBreaker(name="test", failure_threshold=threshold, recovery_timeout=timeout)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        cb = self._make_cb()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self):
        cb = self._make_cb()
        result = await cb.call(self._success_fn)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failures_trip_to_open(self):
        cb = self._make_cb(threshold=3)

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(self._fail_fn)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self):
        cb = self._make_cb(threshold=2)

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(self._fail_fn)

        with pytest.raises(BinanceAPIError, match="Circuit breaker açık"):
            await cb.call(self._success_fn)

    @pytest.mark.asyncio
    async def test_recovery_to_half_open(self):
        cb = self._make_cb(threshold=2, timeout=0.1)

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(self._fail_fn)

        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes(self):
        cb = self._make_cb(threshold=2, timeout=0.1)

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(self._fail_fn)

        await asyncio.sleep(0.15)
        result = await cb.call(self._success_fn)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        cb = self._make_cb(threshold=2, timeout=0.1)

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(self._fail_fn)

        await asyncio.sleep(0.15)
        with pytest.raises(ValueError):
            await cb.call(self._fail_fn)

        assert cb.state == CircuitState.OPEN

    @staticmethod
    async def _success_fn():
        return "ok"

    @staticmethod
    async def _fail_fn():
        raise ValueError("test error")
