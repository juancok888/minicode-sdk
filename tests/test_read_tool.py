"""Tests for ReadTool with text, image, PDF, and notebook file support."""

import base64
import json
import tempfile
from pathlib import Path

import pytest

from minicode.session.message import ToolContext
from minicode.tools.builtin import ReadTool


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tool_context():
    """Create a tool context for testing."""
    return ToolContext(agent_name="test", session_id="test-session")


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing."""
    text_file = temp_dir / "sample.txt"
    text_file.write_text("Hello, World!\nThis is a test file.")
    return text_file


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    py_file = temp_dir / "sample.py"
    py_file.write_text('def hello():\n    print("Hello!")\n')
    return py_file


@pytest.fixture
def sample_png_file(temp_dir):
    """Create a minimal valid PNG file for testing.

    This creates a 1x1 pixel red PNG image.
    """
    # Minimal valid 1x1 red PNG image bytes.
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk
        b"\x00\x00\x00\x01"  # width: 1
        b"\x00\x00\x00\x01"  # height: 1
        b"\x08\x02"  # bit depth: 8, color type: 2 (RGB)
        b"\x00\x00\x00"  # compression, filter, interlace
        b"\x90wS\xde"  # CRC
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND chunk
    )
    png_file = temp_dir / "sample.png"
    png_file.write_bytes(png_bytes)
    return png_file


@pytest.fixture
def sample_jpg_file(temp_dir):
    """Create a minimal valid JPEG file for testing.

    This creates a minimal JPEG image header.
    """
    # Minimal valid JPEG file header and footer.
    jpg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
    jpg_file = temp_dir / "sample.jpg"
    jpg_file.write_bytes(jpg_bytes)
    return jpg_file


# Text File Reading Tests


@pytest.mark.asyncio
async def test_read_text_file(sample_text_file, tool_context):
    """Test reading a plain text file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_text_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "text"
    assert "Hello, World!" in result["data"]
    # Compare resolved paths to handle symlinks (e.g., /var -> /private/var on macOS).
    assert result["path"] == str(sample_text_file.resolve())
    assert result["size"] > 0


@pytest.mark.asyncio
async def test_read_python_file(sample_python_file, tool_context):
    """Test reading a Python source file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_python_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "text"
    assert "def hello():" in result["data"]


@pytest.mark.asyncio
async def test_read_file_with_encoding(temp_dir, tool_context):
    """Test reading a file with specific encoding."""
    # Create a file with UTF-8 content.
    utf8_file = temp_dir / "utf8.txt"
    utf8_file.write_text("你好，世界！", encoding="utf-8")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(utf8_file), "encoding": "utf-8"},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "text"
    assert "你好，世界！" in result["data"]


@pytest.mark.asyncio
async def test_read_file_not_found(tool_context):
    """Test reading a nonexistent file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": "/nonexistent/file.txt"},
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_read_missing_path_parameter(tool_context):
    """Test reading without path parameter."""
    tool = ReadTool()
    result = await tool.execute({}, tool_context)

    assert result["success"] is False
    assert "required" in result["error"].lower()


@pytest.mark.asyncio
async def test_read_directory_not_file(temp_dir, tool_context):
    """Test reading a directory instead of a file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(temp_dir)},
        tool_context,
    )

    assert result["success"] is False
    assert "not a file" in result["error"].lower()


@pytest.mark.asyncio
async def test_read_text_file_too_large(temp_dir, tool_context):
    """Test reading a text file that exceeds size limit."""
    large_file = temp_dir / "large.txt"
    # Create a file larger than MAX_FILE_SIZE (10 MB).
    large_file.write_bytes(b"x" * (11 * 1024 * 1024))

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(large_file)},
        tool_context,
    )

    assert result["success"] is False
    assert "too large" in result["error"].lower()


# Image File Reading Tests


@pytest.mark.asyncio
async def test_read_png_file(sample_png_file, tool_context):
    """Test reading a PNG image file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_png_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/png"
    # Compare resolved paths to handle symlinks (e.g., /var -> /private/var on macOS).
    assert result["path"] == str(sample_png_file.resolve())
    assert result["size"] > 0

    # Verify base64 data is valid.
    decoded = base64.b64decode(result["data"])
    assert decoded.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_read_jpg_file(sample_jpg_file, tool_context):
    """Test reading a JPEG image file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_jpg_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/jpeg"

    # Verify base64 data is valid.
    decoded = base64.b64decode(result["data"])
    assert decoded.startswith(b"\xff\xd8")


@pytest.mark.asyncio
async def test_read_jpeg_extension(temp_dir, tool_context):
    """Test reading a file with .jpeg extension."""
    jpeg_file = temp_dir / "sample.jpeg"
    # Copy minimal JPEG bytes.
    jpeg_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\xff\xd9")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(jpeg_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_read_gif_file(temp_dir, tool_context):
    """Test reading a GIF image file."""
    # Minimal valid GIF89a bytes.
    gif_bytes = b"GIF89a\x01\x00\x01\x00\x00\x00\x00;\x00"
    gif_file = temp_dir / "sample.gif"
    gif_file.write_bytes(gif_bytes)

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(gif_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/gif"


@pytest.mark.asyncio
async def test_read_webp_file(temp_dir, tool_context):
    """Test reading a WebP image file."""
    # Minimal WebP file header.
    webp_bytes = b"RIFF\x00\x00\x00\x00WEBP"
    webp_file = temp_dir / "sample.webp"
    webp_file.write_bytes(webp_bytes)

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(webp_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/webp"


@pytest.mark.asyncio
async def test_read_bmp_file(temp_dir, tool_context):
    """Test reading a BMP image file."""
    # Minimal BMP file header.
    bmp_bytes = b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    bmp_file = temp_dir / "sample.bmp"
    bmp_file.write_bytes(bmp_bytes)

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(bmp_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/bmp"


@pytest.mark.asyncio
async def test_read_image_case_insensitive_extension(temp_dir, tool_context):
    """Test reading image with uppercase extension."""
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"
    png_file = temp_dir / "sample.PNG"
    png_file.write_bytes(png_bytes)

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(png_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "image"
    assert result["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_read_image_file_too_large(temp_dir, tool_context):
    """Test reading an image file that exceeds size limit."""
    large_image = temp_dir / "large.png"
    # Create a file larger than MAX_IMAGE_SIZE (20 MB).
    large_image.write_bytes(b"\x89PNG" + b"x" * (21 * 1024 * 1024))

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(large_image)},
        tool_context,
    )

    assert result["success"] is False
    assert "too large" in result["error"].lower()


# Tool Properties Tests


def test_read_tool_properties():
    """Test ReadTool properties."""
    tool = ReadTool()
    assert tool.name == "read_file"
    assert len(tool.description) > 0
    assert "image" in tool.description.lower()
    assert "path" in tool.parameters_schema["properties"]


def test_read_tool_supported_extensions():
    """Test that supported image extensions are correctly defined."""
    tool = ReadTool()
    expected_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    assert tool.SUPPORTED_IMAGE_EXTENSIONS == expected_extensions


def test_read_tool_mime_types():
    """Test that MIME types are correctly defined."""
    tool = ReadTool()
    assert tool.IMAGE_MIME_TYPES[".png"] == "image/png"
    assert tool.IMAGE_MIME_TYPES[".jpg"] == "image/jpeg"
    assert tool.IMAGE_MIME_TYPES[".jpeg"] == "image/jpeg"
    assert tool.IMAGE_MIME_TYPES[".gif"] == "image/gif"
    assert tool.IMAGE_MIME_TYPES[".webp"] == "image/webp"
    assert tool.IMAGE_MIME_TYPES[".bmp"] == "image/bmp"


# Helper Method Tests


def test_is_image_file():
    """Test _is_image_file helper method."""
    tool = ReadTool()

    assert tool._is_image_file(Path("test.png")) is True
    assert tool._is_image_file(Path("test.PNG")) is True
    assert tool._is_image_file(Path("test.jpg")) is True
    assert tool._is_image_file(Path("test.jpeg")) is True
    assert tool._is_image_file(Path("test.gif")) is True
    assert tool._is_image_file(Path("test.webp")) is True
    assert tool._is_image_file(Path("test.bmp")) is True
    assert tool._is_image_file(Path("test.txt")) is False
    assert tool._is_image_file(Path("test.py")) is False
    assert tool._is_image_file(Path("test.pdf")) is False


def test_get_image_mime_type():
    """Test _get_image_mime_type helper method."""
    tool = ReadTool()

    assert tool._get_image_mime_type(Path("test.png")) == "image/png"
    assert tool._get_image_mime_type(Path("test.PNG")) == "image/png"
    assert tool._get_image_mime_type(Path("test.jpg")) == "image/jpeg"
    assert tool._get_image_mime_type(Path("test.unknown")) == "application/octet-stream"


def test_is_pdf_file():
    """Test _is_pdf_file helper method."""
    tool = ReadTool()

    assert tool._is_pdf_file(Path("test.pdf")) is True
    assert tool._is_pdf_file(Path("test.PDF")) is True
    assert tool._is_pdf_file(Path("test.txt")) is False
    assert tool._is_pdf_file(Path("test.png")) is False


# PDF Reading Tests


@pytest.mark.asyncio
async def test_read_pdf_without_pymupdf(temp_dir, tool_context, monkeypatch):
    """Test reading PDF when PyMuPDF is not installed."""
    # Create a fake PDF file.
    pdf_file = temp_dir / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")

    # Mock PDF_SUPPORT to False.
    import minicode.tools.builtin.read as read_module
    monkeypatch.setattr(read_module, "PDF_SUPPORT", False)

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(pdf_file)},
        tool_context,
    )

    assert result["success"] is False
    assert "PDF support is not available" in result["error"]
    assert "PyMuPDF" in result["error"]


@pytest.mark.asyncio
async def test_read_pdf_file_not_found(tool_context):
    """Test reading a nonexistent PDF file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": "/nonexistent/file.pdf"},
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


# PDF tests that require PyMuPDF installed.
try:
    import fitz  # noqa: F401
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create a minimal valid PDF file for testing using PyMuPDF."""
    if not HAS_PYMUPDF:
        pytest.skip("PyMuPDF not installed")

    import fitz

    # Create a simple PDF with one page.
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    page.insert_text((10, 50), "Test PDF")
    pdf_path = temp_dir / "sample.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF not installed")
@pytest.mark.asyncio
async def test_read_pdf_file(sample_pdf_file, tool_context):
    """Test reading a valid PDF file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_pdf_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "pdf"
    assert result["page_count"] == 1
    assert len(result["pages"]) == 1

    # Check page structure.
    page = result["pages"][0]
    assert page["page"] == 1
    assert page["mime_type"] == "image/png"
    assert len(page["data"]) > 0

    # Verify base64 data is valid PNG.
    decoded = base64.b64decode(page["data"])
    assert decoded.startswith(b"\x89PNG")


@pytest.fixture
def sample_multipage_pdf_file(temp_dir):
    """Create a multi-page PDF file for testing."""
    if not HAS_PYMUPDF:
        pytest.skip("PyMuPDF not installed")

    import fitz

    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=100, height=100)
        page.insert_text((10, 50), f"Page {i + 1}")
    pdf_path = temp_dir / "multipage.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF not installed")
@pytest.mark.asyncio
async def test_read_multipage_pdf(sample_multipage_pdf_file, tool_context):
    """Test reading a multi-page PDF file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_multipage_pdf_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "pdf"
    assert result["page_count"] == 3
    assert len(result["pages"]) == 3

    # Verify each page.
    for i, page in enumerate(result["pages"]):
        assert page["page"] == i + 1
        assert page["mime_type"] == "image/png"
        assert len(page["data"]) > 0


@pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF not installed")
@pytest.mark.asyncio
async def test_read_pdf_file_too_large(temp_dir, tool_context):
    """Test reading a PDF file that exceeds size limit."""
    large_pdf = temp_dir / "large.pdf"
    # Create a file larger than MAX_PDF_SIZE (50 MB).
    large_pdf.write_bytes(b"%PDF-1.4" + b"x" * (51 * 1024 * 1024))

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(large_pdf)},
        tool_context,
    )

    assert result["success"] is False
    assert "too large" in result["error"].lower()


# Jupyter Notebook Reading Tests


@pytest.fixture
def sample_notebook_file(temp_dir):
    """Create a sample Jupyter notebook for testing."""
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Test Notebook\n", "\n", "This is a test."],
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [
                    {
                        "name": "stdout",
                        "output_type": "stream",
                        "text": ["Hello, World!\n"],
                    }
                ],
                "source": ['print("Hello, World!")'],
            },
            {
                "cell_type": "code",
                "execution_count": 2,
                "metadata": {},
                "outputs": [
                    {
                        "data": {"text/plain": ["42"]},
                        "execution_count": 2,
                        "metadata": {},
                        "output_type": "execute_result",
                    }
                ],
                "source": ["x = 42\n", "x"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    notebook_file = temp_dir / "sample.ipynb"
    notebook_file.write_text(json.dumps(notebook), encoding="utf-8")
    return notebook_file


@pytest.mark.asyncio
async def test_read_notebook_file(sample_notebook_file, tool_context):
    """Test reading a Jupyter notebook file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": str(sample_notebook_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["type"] == "notebook"
    assert result["cell_count"] == 3
    assert result["path"] == str(sample_notebook_file.resolve())

    # Check content format.
    content = result["data"]

    # Check markdown cell format.
    assert '<cell id="cell-0"><cell_type>markdown</cell_type>' in content
    assert "# Test Notebook" in content
    assert '</cell id="cell-0">' in content

    # Check code cell format (no cell_type tag).
    assert '<cell id="cell-1">' in content
    assert 'print("Hello, World!")' in content
    assert '</cell id="cell-1">' in content

    # Check output follows cell.
    assert "Hello, World!" in content

    # Check execute_result output.
    assert "42" in content


@pytest.mark.asyncio
async def test_read_notebook_with_error_output(temp_dir, tool_context):
    """Test reading a notebook with error output."""
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [
                    {
                        "ename": "ValueError",
                        "evalue": "invalid value",
                        "output_type": "error",
                        "traceback": [],
                    }
                ],
                "source": ["raise ValueError('invalid value')"],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    notebook_file = temp_dir / "error.ipynb"
    notebook_file.write_text(json.dumps(notebook), encoding="utf-8")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(notebook_file)},
        tool_context,
    )

    assert result["success"] is True
    content = result["data"]
    assert "ValueError: invalid value" in content


@pytest.mark.asyncio
async def test_read_notebook_empty_cells(temp_dir, tool_context):
    """Test reading a notebook with empty cells."""
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    notebook_file = temp_dir / "empty.ipynb"
    notebook_file.write_text(json.dumps(notebook), encoding="utf-8")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(notebook_file)},
        tool_context,
    )

    assert result["success"] is True
    assert result["cell_count"] == 1
    assert '<cell id="cell-0">' in result["data"]


@pytest.mark.asyncio
async def test_read_notebook_invalid_json(temp_dir, tool_context):
    """Test reading an invalid notebook file."""
    invalid_notebook = temp_dir / "invalid.ipynb"
    invalid_notebook.write_text("not valid json {{{", encoding="utf-8")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(invalid_notebook)},
        tool_context,
    )

    assert result["success"] is False
    assert "Invalid notebook JSON" in result["error"]


@pytest.mark.asyncio
async def test_read_notebook_not_found(tool_context):
    """Test reading a nonexistent notebook file."""
    tool = ReadTool()
    result = await tool.execute(
        {"path": "/nonexistent/file.ipynb"},
        tool_context,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_is_notebook_file():
    """Test _is_notebook_file helper method."""
    tool = ReadTool()

    assert tool._is_notebook_file(Path("test.ipynb")) is True
    assert tool._is_notebook_file(Path("test.IPYNB")) is True
    assert tool._is_notebook_file(Path("test.txt")) is False
    assert tool._is_notebook_file(Path("test.py")) is False
    assert tool._is_notebook_file(Path("test.json")) is False


@pytest.mark.asyncio
async def test_read_notebook_with_display_data(temp_dir, tool_context):
    """Test reading a notebook with display_data output."""
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [
                    {
                        "data": {
                            "text/plain": ["<Figure>"],
                            "text/html": ["<img src='data:...'>"],
                        },
                        "metadata": {},
                        "output_type": "display_data",
                    }
                ],
                "source": ["plt.show()"],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    notebook_file = temp_dir / "display.ipynb"
    notebook_file.write_text(json.dumps(notebook), encoding="utf-8")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(notebook_file)},
        tool_context,
    )

    assert result["success"] is True
    # Should prefer text/plain.
    assert "<Figure>" in result["data"]


@pytest.mark.asyncio
async def test_read_notebook_source_as_string(temp_dir, tool_context):
    """Test reading a notebook where source is a string instead of list."""
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": "x = 1",  # String instead of list.
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    notebook_file = temp_dir / "string_source.ipynb"
    notebook_file.write_text(json.dumps(notebook), encoding="utf-8")

    tool = ReadTool()
    result = await tool.execute(
        {"path": str(notebook_file)},
        tool_context,
    )

    assert result["success"] is True
    assert "x = 1" in result["data"]
