"""Retry logic testleri."""

import pytest

from src.core.retry import with_retry


class TestRetry:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Başarılı çağrıda retry yapılmaz."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self):
        """İlk çağrı başarısız, ikinci başarılı."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Tüm denemeler başarısız olursa exception fırlatılır."""
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01)
        async def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            await fn()
        assert call_count == 3  # 1 ilk + 2 retry

    @pytest.mark.asyncio
    async def test_non_retryable_exception_not_retried(self):
        """Retryable olmayan exception'da retry yapılmaz."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def fn():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await fn()
        assert call_count == 1
