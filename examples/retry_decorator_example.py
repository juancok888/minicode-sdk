#!/usr/bin/env python3
"""Examples of using the retry decorator.

This module demonstrates various use cases for the retry decorator,
including synchronous functions, async functions, custom exceptions,
exponential backoff, and retry callbacks.
"""

import asyncio
import random
from typing import Dict

from minicode.utils import retry, retry_with_exponential_backoff


# Example 1: Basic retry with sync function
@retry(max_retries=3, wait_seconds=1.0)
def unstable_api_call() -> str:
    """Simulates an unreliable API call that randomly fails.

    Returns:
        str: Success message if the call succeeds.

    Raises:
        ConnectionError: If the random API call fails.
    """
    if random.random() < 0.7:  # 70% chance of failure
        raise ConnectionError("API connection failed")
    return "API call successful!"


# Example 2: Retry with exponential backoff
@retry_with_exponential_backoff(max_retries=5, initial_wait=1.0, max_wait=30.0)
def rate_limited_api() -> Dict:
    """Simulates an API with rate limiting that needs exponential backoff.

    Returns:
        Dict: API response data.

    Raises:
        Exception: If rate limit is exceeded.
    """
    if random.random() < 0.8:  # 80% chance of rate limit
        raise Exception("Rate limit exceeded")
    return {"status": "success", "data": [1, 2, 3]}


# Example 3: Async function with retry
@retry(max_retries=3, wait_seconds=0.5)
async def async_database_query(query: str) -> list:
    """Simulates an async database query that might fail.

    Args:
        query: SQL query string.

    Returns:
        list: Query results.

    Raises:
        RuntimeError: If database connection fails.
    """
    await asyncio.sleep(0.1)  # Simulate network delay
    if random.random() < 0.6:  # 60% chance of failure
        raise RuntimeError("Database connection timeout")
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


# Example 4: Retry with specific exceptions only
@retry(max_retries=3, wait_seconds=1.0, exceptions=(ConnectionError, TimeoutError))
def network_operation() -> str:
    """Retries only on network-related exceptions.

    Returns:
        str: Operation result.

    Raises:
        ValueError: Not retried (different exception type).
        ConnectionError: Retried up to max_retries times.
    """
    error_type = random.choice(["connection", "timeout", "validation"])

    if error_type == "connection":
        raise ConnectionError("Network connection failed")
    elif error_type == "timeout":
        raise TimeoutError("Request timed out")
    elif error_type == "validation":
        raise ValueError("Invalid input data")  # Won't be retried

    return "Operation completed"


# Example 5: Retry with custom callback
def log_retry(exception: Exception, retry_count: int, max_retries: int) -> None:
    """Custom callback to log retry attempts.

    Args:
        exception: The exception that triggered the retry.
        retry_count: Current retry attempt number (1-indexed).
        max_retries: Maximum number of retries configured.
    """
    print(f"⚠️  Retry {retry_count}/{max_retries}: {type(exception).__name__}: {exception}")


@retry(max_retries=3, wait_seconds=1.0, on_retry=log_retry)
def operation_with_logging() -> str:
    """Function with custom retry logging.

    Returns:
        str: Success message.
    """
    if random.random() < 0.7:
        raise RuntimeError("Temporary failure")
    return "Success with logging!"


# Example 6: Retry with backoff factor
@retry(max_retries=4, wait_seconds=0.5, backoff_factor=2.0)
def operation_with_backoff() -> str:
    """Function with custom backoff factor.

    Wait times will be: 0.5s, 1.0s, 2.0s, 4.0s

    Returns:
        str: Success message.
    """
    if random.random() < 0.8:
        raise Exception("Retry with increasing backoff")
    return "Backoff strategy worked!"


# Example 7: Real-world example - Web scraping
@retry_with_exponential_backoff(
    max_retries=5, initial_wait=2.0, max_wait=60.0, exceptions=(ConnectionError, TimeoutError)
)
async def scrape_website(url: str) -> str:
    """Scrape a website with exponential backoff on failures.

    Args:
        url: Website URL to scrape.

    Returns:
        str: Scraped content.

    Raises:
        ConnectionError: If connection fails after all retries.
    """
    await asyncio.sleep(0.2)  # Simulate HTTP request

    # Simulate various failure modes
    failure_type = random.random()
    if failure_type < 0.3:
        raise ConnectionError(f"Failed to connect to {url}")
    elif failure_type < 0.5:
        raise TimeoutError(f"Request to {url} timed out")

    return f"<html>Content from {url}</html>"


# Example 8: Database transaction with retry
@retry(max_retries=3, wait_seconds=1.0, exceptions=(RuntimeError,))
async def execute_transaction(transaction_id: str) -> bool:
    """Execute a database transaction with automatic retry on deadlock.

    Args:
        transaction_id: Unique transaction identifier.

    Returns:
        bool: True if transaction succeeded.

    Raises:
        RuntimeError: If transaction fails after retries.
    """
    await asyncio.sleep(0.1)

    # Simulate deadlock scenario
    if random.random() < 0.6:
        raise RuntimeError(f"Deadlock detected for transaction {transaction_id}")

    print(f"Transaction {transaction_id} committed successfully")
    return True


async def main():
    """Run all examples."""
    print("=" * 60)
    print("RETRY DECORATOR EXAMPLES")
    print("=" * 60)

    # Example 1: Basic retry
    print("\n1. Basic retry with sync function:")
    try:
        result = unstable_api_call()
        print(f"   ✅ {result}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Example 2: Exponential backoff
    print("\n2. Exponential backoff:")
    try:
        result = rate_limited_api()
        print(f"   ✅ {result}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Example 3: Async function
    print("\n3. Async database query:")
    try:
        result = await async_database_query("SELECT * FROM users")
        print(f"   ✅ Query returned {len(result)} rows")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Example 4: Specific exceptions
    print("\n4. Retry with specific exceptions:")
    try:
        result = network_operation()
        print(f"   ✅ {result}")
    except ConnectionError as e:
        print(f"   ❌ Connection failed: {e}")
    except TimeoutError as e:
        print(f"   ❌ Timeout: {e}")
    except ValueError as e:
        print(f"   ❌ Validation error (not retried): {e}")

    # Example 5: Custom logging
    print("\n5. Retry with custom logging:")
    try:
        result = operation_with_logging()
        print(f"   ✅ {result}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Example 6: Backoff factor
    print("\n6. Custom backoff factor:")
    try:
        result = operation_with_backoff()
        print(f"   ✅ {result}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Example 7: Web scraping
    print("\n7. Web scraping with exponential backoff:")
    try:
        content = await scrape_website("https://example.com")
        print(f"   ✅ Scraped {len(content)} characters")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Example 8: Database transaction
    print("\n8. Database transaction with retry:")
    try:
        success = await execute_transaction("txn-12345")
        print(f"   ✅ Transaction completed: {success}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
