"""Retry decorator for handling transient failures.

This module provides decorators for automatic retry logic with configurable
wait times and maximum retry attempts. Supports both sync and async functions.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_retries: int = 3,
    wait_seconds: float = 1.0,
    backoff_factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, int], None]] = None,
) -> Callable[[F], F]:
    """Decorator to retry a function when it raises specified exceptions.

    This decorator works with both synchronous and asynchronous functions.
    It will retry the function up to `max_retries` times when it raises
    one of the specified exceptions, waiting `wait_seconds` between attempts.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
                    Total attempts = max_retries + 1 (initial attempt).
        wait_seconds: Initial wait time in seconds between retries (default: 1.0).
        backoff_factor: Multiplier for wait time after each retry (default: 1.0).
                       If > 1.0, implements exponential backoff.
                       wait_time = wait_seconds * (backoff_factor ** retry_count)
        exceptions: Tuple of exception types to catch and retry (default: (Exception,)).
        on_retry: Optional callback function called before each retry.
                 Signature: on_retry(exception, retry_count, max_retries)

    Returns:
        Decorated function that will retry on failure.

    Example:
        >>> @retry(max_retries=3, wait_seconds=2.0)
        ... def unstable_function():
        ...     if random.random() < 0.5:
        ...         raise ValueError("Random failure")
        ...     return "Success"

        >>> @retry(max_retries=5, wait_seconds=1.0, backoff_factor=2.0)
        ... async def unstable_async_function():
        ...     response = await api_call()
        ...     return response

        >>> @retry(
        ...     max_retries=3,
        ...     exceptions=(ConnectionError, TimeoutError),
        ...     on_retry=lambda e, r, m: print(f"Retry {r}/{m}: {e}")
        ... )
        ... def network_call():
        ...     return requests.get("https://api.example.com")
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):
            # Async function
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                current_wait = wait_seconds

                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        # If this was the last attempt, raise the exception
                        if attempt == max_retries:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                            raise

                        # Call retry callback if provided
                        if on_retry:
                            on_retry(e, attempt + 1, max_retries)

                        # Log retry attempt
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_wait:.2f} seconds..."
                        )

                        # Wait before retry
                        await asyncio.sleep(current_wait)

                        # Apply backoff factor for next iteration
                        current_wait *= backoff_factor

                # This should never be reached, but added for type safety
                if last_exception:
                    raise last_exception
                raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")

            return async_wrapper  # type: ignore

        else:
            # Sync function
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                current_wait = wait_seconds

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        # If this was the last attempt, raise the exception
                        if attempt == max_retries:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                            raise

                        # Call retry callback if provided
                        if on_retry:
                            on_retry(e, attempt + 1, max_retries)

                        # Log retry attempt
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_wait:.2f} seconds..."
                        )

                        # Wait before retry
                        time.sleep(current_wait)

                        # Apply backoff factor for next iteration
                        current_wait *= backoff_factor

                # This should never be reached, but added for type safety
                if last_exception:
                    raise last_exception
                raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")

            return sync_wrapper  # type: ignore

    return decorator


def retry_with_exponential_backoff(
    max_retries: int = 5,
    initial_wait: float = 1.0,
    max_wait: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Convenience decorator for exponential backoff retry strategy.

    This is a specialized version of the retry decorator with exponential
    backoff (factor = 2.0) and a maximum wait time cap.

    Args:
        max_retries: Maximum number of retry attempts (default: 5).
        initial_wait: Initial wait time in seconds (default: 1.0).
        max_wait: Maximum wait time in seconds, caps exponential growth (default: 60.0).
        exceptions: Tuple of exception types to catch and retry.

    Returns:
        Decorated function with exponential backoff retry logic.

    Example:
        >>> @retry_with_exponential_backoff(max_retries=5)
        ... async def api_call():
        ...     response = await http_client.get("https://api.example.com")
        ...     return response
        # Wait times: 1s, 2s, 4s, 8s, 16s
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        if attempt == max_retries:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                            raise

                        # Calculate exponential backoff with max cap
                        wait_time = min(initial_wait * (2**attempt), max_wait)

                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {wait_time:.2f} seconds..."
                        )

                        await asyncio.sleep(wait_time)

                if last_exception:
                    raise last_exception
                raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        if attempt == max_retries:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                            raise

                        # Calculate exponential backoff with max cap
                        wait_time = min(initial_wait * (2**attempt), max_wait)

                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {wait_time:.2f} seconds..."
                        )

                        time.sleep(wait_time)

                if last_exception:
                    raise last_exception
                raise RuntimeError(f"Unexpected state in retry logic for {func.__name__}")

            return sync_wrapper  # type: ignore

    return decorator
