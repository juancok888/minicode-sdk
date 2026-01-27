# minicode Tests

This directory contains the test suite for minicode.

## Test Organization

- **Unit Tests**: Mock-based tests that don't require network access
- **Integration Tests**: Tests that make real API calls and network requests

## Running Tests

### Run All Unit Tests (Default)

```bash
pytest
```

This excludes integration tests by default:

```bash
pytest -m "not integration"
```

### Run Integration Tests

Integration tests make real network requests and may be slow. Run them with:

```bash
pytest -m integration
```

### Run Specific Test Files

```bash
# Unit tests only
pytest tests/test_web_tools.py

# Integration tests
pytest tests/test_web_tools_integration.py
```

### Run Specific Tests

```bash
# Run a specific integration test
pytest tests/test_web_tools_integration.py::test_websearch_anime_query -v -s

# Run with output visible
pytest tests/test_web_tools_integration.py::test_webfetch_real_page -v -s
```

## Test Markers

Tests are marked with pytest markers:

- `@pytest.mark.integration` - Tests that make real network requests
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.asyncio` - Async tests (auto-detected)

### Excluding Slow/Integration Tests

```bash
# Skip integration tests
pytest -m "not integration"

# Skip slow tests
pytest -m "not slow"

# Skip both
pytest -m "not integration and not slow"
```

## Test Coverage

### Unit Tests (`test_web_tools.py`)

- **WebFetch**: URL validation, format conversion, timeout handling, error handling
- **WebSearch**: Query validation, backend selection, Exa API mocking
- **17 test cases** - All use mocks, no network requests

### Integration Tests (`test_web_tools_integration.py`)

- **Real API Calls**: Tests make actual requests to Exa API and web servers
- **Use Cases**:
  - Search and fetch workflows
  - Multiple format conversions
  - Anime news search (original use case)
- **10 test cases** - All marked with `@pytest.mark.integration`

## Writing New Tests

### Unit Tests (Recommended for CI)

```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.mark.asyncio
async def test_my_feature(tool_context):
    tool = MyTool()

    # Mock external dependencies
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await tool.execute(params, tool_context)

    assert result["success"] is True
```

### Integration Tests (Run Manually)

```python
import pytest

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
@pytest.mark.slow
async def test_real_api_call(tool_context):
    """Test with real API call.

    This test makes actual network requests and should be run manually
    or with appropriate rate limiting in CI.
    """
    tool = WebSearchTool()
    result = await tool.execute({"query": "test"}, tool_context)

    assert result["success"] is True
```

## CI/CD Recommendations

### GitHub Actions Example

```yaml
# Fast unit tests (run on every push)
- name: Run unit tests
  run: pytest -m "not integration" --cov=minicode

# Integration tests (run on schedule or manually)
- name: Run integration tests
  if: github.event_name == 'schedule'
  run: pytest -m integration --maxfail=3
```

## Test Data

Integration tests use these real endpoints:

- **Exa API**: `https://mcp.exa.ai/mcp` (requires no auth key)
- **Test Pages**:
  - `https://example.com` (stable test page)
  - `https://www.python.org` (Python official site)
  - Anime news sites (for search validation)

## Troubleshooting

### Integration Tests Failing

If integration tests fail:

1. **Network Issues**: Check internet connection
2. **Rate Limiting**: Exa API may rate limit requests
3. **API Changes**: APIs may change their response format
4. **Timeouts**: Increase timeout values for slow connections

### Slow Tests

If tests are slow:

```bash
# Skip slow tests during development
pytest -m "not slow"

# Run with pytest-xdist for parallel execution
pip install pytest-xdist
pytest -n auto
```

## Test Statistics

- **Total Tests**: 85 (75 unit + 10 integration)
- **Coverage**: ~95% for web tools
- **Average Runtime**:
  - Unit tests: ~0.3s
  - Integration tests: ~5-10s per test
