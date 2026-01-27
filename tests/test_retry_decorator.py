"""Tests for retry decorator utilities."""

import asyncio
import time
from typing import List

import pytest

from minicode.utils import retry, retry_with_exponential_backoff


class TestRetryDecorator:
    """Test cases for the retry decorator."""

    def test_retry_success_on_first_attempt(self):
        """Test that function succeeds on first attempt without retry."""
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.1)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test that function succeeds after some failures."""
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.1)
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_successful_function()

        assert result == "success"
        assert call_count == 3

    def test_retry_max_retries_exceeded(self):
        """Test that exception is raised after max retries exceeded."""
        call_count = 0

        @retry(max_retries=2, wait_seconds=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure {call_count}")

        with pytest.raises(ValueError, match="Failure 3"):
            always_failing_function()

        assert call_count == 3  # Initial attempt + 2 retries

    def test_retry_with_specific_exceptions(self):
        """Test that only specified exceptions trigger retry."""
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.1, exceptions=(ValueError,))
        def function_with_wrong_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong exception type")

        with pytest.raises(TypeError):
            function_with_wrong_exception()

        assert call_count == 1  # Should not retry on TypeError

    def test_retry_with_multiple_exception_types(self):
        """Test retry with multiple exception types."""
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.1, exceptions=(ValueError, TypeError))
        def function_with_multiple_exceptions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First error")
            elif call_count == 2:
                raise TypeError("Second error")
            return "success"

        result = function_with_multiple_exceptions()

        assert result == "success"
        assert call_count == 3

    def test_retry_backoff_factor(self):
        """Test that backoff factor increases wait time correctly."""
        wait_times: List[float] = []
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.1, backoff_factor=2.0)
        def function_for_backoff_test():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                start = time.time()
                raise ValueError("Retry")
            return "success"

        start_time = time.time()
        result = function_for_backoff_test()
        total_time = time.time() - start_time

        assert result == "success"
        assert call_count == 4
        # With backoff_factor=2.0: 0.1, 0.2, 0.4 = 0.7 total
        assert total_time >= 0.7
        assert total_time < 1.0  # Some tolerance for execution time

    def test_retry_on_retry_callback(self):
        """Test that on_retry callback is called correctly."""
        retry_info: List[tuple] = []

        def on_retry_callback(exception, retry_count, max_retries):
            retry_info.append((str(exception), retry_count, max_retries))

        call_count = 0

        @retry(max_retries=2, wait_seconds=0.05, on_retry=on_retry_callback)
        def function_with_callback():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Error {call_count}")
            return "success"

        result = function_with_callback()

        assert result == "success"
        assert len(retry_info) == 2
        assert retry_info[0] == ("Error 1", 1, 2)
        assert retry_info[1] == ("Error 2", 2, 2)

    def test_retry_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @retry(max_retries=3)
        def documented_function():
            """This is a documented function."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    def test_retry_with_args_and_kwargs(self):
        """Test that decorated function accepts args and kwargs."""
        call_count = 0

        @retry(max_retries=2, wait_seconds=0.05)
        def function_with_params(x, y, z=10):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return x + y + z

        result = function_with_params(1, 2, z=3)

        assert result == 6
        assert call_count == 2


class TestRetryDecoratorAsync:
    """Test cases for retry decorator with async functions."""

    @pytest.mark.asyncio
    async def test_async_retry_success_on_first_attempt(self):
        """Test that async function succeeds on first attempt."""
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.1)
        async def async_successful_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "success"

        result = await async_successful_function()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """Test that async function succeeds after failures."""
        call_count = 0

        @retry(max_retries=3, wait_seconds=0.05)
        async def async_eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            await asyncio.sleep(0.01)
            return "success"

        result = await async_eventually_successful()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_max_retries_exceeded(self):
        """Test that exception is raised after max retries for async function."""
        call_count = 0

        @retry(max_retries=2, wait_seconds=0.05)
        async def async_always_failing():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure {call_count}")

        with pytest.raises(ValueError, match="Failure 3"):
            await async_always_failing()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_with_args(self):
        """Test async function with arguments."""
        call_count = 0

        @retry(max_retries=2, wait_seconds=0.05)
        async def async_function_with_params(x, y):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            await asyncio.sleep(0.01)
            return x * y

        result = await async_function_with_params(3, 4)

        assert result == 12
        assert call_count == 2


class TestExponentialBackoffDecorator:
    """Test cases for exponential backoff decorator."""

    def test_exponential_backoff_success(self):
        """Test exponential backoff decorator success case."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3, initial_wait=0.05)
        def function_with_exponential_backoff():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = function_with_exponential_backoff()

        assert result == "success"
        assert call_count == 3

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing is correct."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3, initial_wait=0.1, max_wait=1.0)
        def function_for_timing_test():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "success"

        start_time = time.time()
        result = function_for_timing_test()
        elapsed = time.time() - start_time

        assert result == "success"
        # Wait times: 0.1, 0.2, 0.4 = 0.7 total
        assert elapsed >= 0.7
        assert elapsed < 1.2

    def test_exponential_backoff_max_wait_cap(self):
        """Test that max_wait caps the exponential growth."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=5, initial_wait=0.1, max_wait=0.3)
        def function_with_max_wait():
            nonlocal call_count
            call_count += 1
            if call_count < 6:
                raise ValueError("Retry")
            return "success"

        start_time = time.time()
        result = function_with_max_wait()
        elapsed = time.time() - start_time

        assert result == "success"
        # Wait times: 0.1, 0.2, 0.3 (capped), 0.3 (capped), 0.3 (capped) = 1.2 total
        assert elapsed >= 1.2
        assert elapsed < 1.8

    @pytest.mark.asyncio
    async def test_async_exponential_backoff(self):
        """Test exponential backoff with async function."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3, initial_wait=0.05)
        async def async_function_with_backoff():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            await asyncio.sleep(0.01)
            return "success"

        result = await async_function_with_backoff()

        assert result == "success"
        assert call_count == 3


class TestRetryEdgeCases:
    """Test edge cases and error conditions."""

    def test_retry_with_zero_wait(self):
        """Test retry with zero wait time."""
        call_count = 0

        @retry(max_retries=2, wait_seconds=0.0)
        def function_with_zero_wait():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = function_with_zero_wait()

        assert result == "success"
        assert call_count == 3

    def test_retry_with_zero_retries(self):
        """Test retry with max_retries=0 (only one attempt)."""
        call_count = 0

        @retry(max_retries=0, wait_seconds=0.1)
        def function_with_no_retries():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            function_with_no_retries()

        assert call_count == 1  # Only initial attempt, no retries

    def test_retry_returns_none(self):
        """Test that retry works when function returns None."""
        call_count = 0

        @retry(max_retries=2, wait_seconds=0.05)
        def function_returning_none():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return None

        result = function_returning_none()

        assert result is None
        assert call_count == 2
