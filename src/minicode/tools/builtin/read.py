"""Built-in read file tool."""

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from minicode.session.message import ToolContext
from minicode.tools.base import BaseTool

# Optional PDF support via PyMuPDF.
try:
    import fitz  # PyMuPDF

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


class ReadTool(BaseTool):
    """Tool for reading file contents.

    This tool allows the agent to read files from the filesystem.
    Supports text files, image files (PNG, JPG, GIF, WebP), PDF files,
    and Jupyter notebooks (.ipynb).

    Note: For production use, consider adding:
    - Path validation/sanitization
    - Access control based on allowed directories
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB default limit
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB for images
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB for PDFs
    MAX_NOTEBOOK_SIZE = 50 * 1024 * 1024  # 50 MB for notebooks
    PDF_DPI = 150  # DPI for rendering PDF pages to images

    # Supported image extensions.
    SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
    }

    # MIME type mapping for images.
    IMAGE_MIME_TYPES: Dict[str, str] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "read_file"

    @property
    def description(self) -> str:
        """Get the tool description."""
        pdf_note = " PDF files are rendered as images page by page." if PDF_SUPPORT else ""
        return (
            "Read the contents of a file. "
            "Supports text files, images (PNG, JPG, GIF, WebP, BMP), PDF files, "
            "and Jupyter notebooks (.ipynb). "
            "For text files, returns the content as text. "
            "For images, returns base64-encoded data with MIME type. "
            "For notebooks, returns cells with their outputs in a structured format."
            f"{pdf_note}"
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """Get the parameters schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (absolute or relative)",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
            },
            "required": ["path"],
        }

    def _is_image_file(self, file_path: Path) -> bool:
        """Check if the file is a supported image format.

        Args:
            file_path: Path to the file.

        Returns:
            True if the file is a supported image format.
        """
        return file_path.suffix.lower() in self.SUPPORTED_IMAGE_EXTENSIONS

    def _get_image_mime_type(self, file_path: Path) -> str:
        """Get the MIME type for an image file.

        Args:
            file_path: Path to the image file.

        Returns:
            MIME type string.
        """
        suffix = file_path.suffix.lower()
        return self.IMAGE_MIME_TYPES.get(suffix, "application/octet-stream")

    def _is_pdf_file(self, file_path: Path) -> bool:
        """Check if the file is a PDF.

        Args:
            file_path: Path to the file.

        Returns:
            True if the file is a PDF.
        """
        return file_path.suffix.lower() == ".pdf"

    def _is_notebook_file(self, file_path: Path) -> bool:
        """Check if the file is a Jupyter notebook.

        Args:
            file_path: Path to the file.

        Returns:
            True if the file is a Jupyter notebook.
        """
        return file_path.suffix.lower() == ".ipynb"

    async def _read_image(self, file_path: Path) -> Dict[str, Any]:
        """Read an image file and return base64-encoded data.

        Args:
            file_path: Path to the image file.

        Returns:
            Dictionary containing success status and image data.
        """
        file_size = file_path.stat().st_size
        if file_size > self.MAX_IMAGE_SIZE:
            return {
                "success": False,
                "error": (
                    f"Image file too large: {file_size} bytes "
                    f"(max: {self.MAX_IMAGE_SIZE})"
                ),
            }

        with open(file_path, "rb") as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode("utf-8")
        mime_type = self._get_image_mime_type(file_path)

        return {
            "success": True,
            "type": "image",
            "mime_type": mime_type,
            "data": base64_data,
            "path": str(file_path),
            "size": file_size,
        }

    async def _read_text(
        self, file_path: Path, encoding: str
    ) -> Dict[str, Any]:
        """Read a text file and return its contents.

        Args:
            file_path: Path to the text file.
            encoding: Character encoding to use.

        Returns:
            Dictionary containing success status and file content.
        """
        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return {
                "success": False,
                "error": (
                    f"File too large: {file_size} bytes "
                    f"(max: {self.MAX_FILE_SIZE})"
                ),
            }

        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        return {
            "success": True,
            "type": "text",
            "data": content,
            "path": str(file_path),
            "size": len(content),
        }

    async def _read_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Read a PDF file and return pages as images.

        Each page is rendered as a PNG image at the configured DPI.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dictionary containing success status and page images.
        """
        if not PDF_SUPPORT:
            return {
                "success": False,
                "error": (
                    "PDF support is not available. "
                    "Install PyMuPDF: pip install 'minicode-sdk[pdf]'"
                ),
            }

        file_size = file_path.stat().st_size
        if file_size > self.MAX_PDF_SIZE:
            return {
                "success": False,
                "error": (
                    f"PDF file too large: {file_size} bytes "
                    f"(max: {self.MAX_PDF_SIZE})"
                ),
            }

        try:
            doc = fitz.open(file_path)
            pages: List[Dict[str, Any]] = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                # Render page to image at specified DPI.
                mat = fitz.Matrix(self.PDF_DPI / 72, self.PDF_DPI / 72)
                pix = page.get_pixmap(matrix=mat)
                # Convert to PNG bytes.
                png_data = pix.tobytes("png")
                base64_data = base64.b64encode(png_data).decode("utf-8")

                pages.append({
                    "page": page_num + 1,
                    "mime_type": "image/png",
                    "data": base64_data,
                })

            doc.close()

            return {
                "success": True,
                "type": "pdf",
                "path": str(file_path),
                "size": file_size,
                "page_count": len(pages),
                "pages": pages,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read PDF: {e}",
            }

    def _format_notebook_output(self, output: Dict[str, Any]) -> str:
        """Format a single notebook cell output.

        Args:
            output: The output dictionary from a notebook cell.

        Returns:
            Formatted output string.
        """
        output_type = output.get("output_type", "")

        if output_type == "stream":
            # stdout/stderr output.
            text = output.get("text", [])
            if isinstance(text, list):
                return "".join(text)
            return str(text)

        elif output_type == "execute_result" or output_type == "display_data":
            # Data output (text/plain, text/html, etc.).
            data = output.get("data", {})
            # Prefer text/plain for simplicity.
            if "text/plain" in data:
                text = data["text/plain"]
                if isinstance(text, list):
                    return "".join(text)
                return str(text)
            # Fallback to first available.
            for key, value in data.items():
                if isinstance(value, list):
                    return "".join(value)
                return str(value)

        elif output_type == "error":
            # Error output.
            ename = output.get("ename", "Error")
            evalue = output.get("evalue", "")
            return f"{ename}: {evalue}"

        return ""

    def _format_notebook_cell(
        self, cell: Dict[str, Any], cell_index: int
    ) -> str:
        """Format a single notebook cell.

        Args:
            cell: The cell dictionary from a notebook.
            cell_index: The index of the cell (0-based).

        Returns:
            Formatted cell string matching Claude Code Read tool format.
        """
        cell_type = cell.get("cell_type", "code")
        source = cell.get("source", [])

        # Join source if it's a list.
        if isinstance(source, list):
            source_text = "".join(source)
        else:
            source_text = str(source)

        # Build cell content.
        cell_id = f"cell-{cell_index}"
        parts = []

        if cell_type == "markdown":
            # Markdown cells include cell_type tag.
            parts.append(
                f'<cell id="{cell_id}"><cell_type>markdown</cell_type>'
                f'{source_text}</cell id="{cell_id}">'
            )
        else:
            # Code cells don't include cell_type tag.
            parts.append(f'<cell id="{cell_id}">{source_text}</cell id="{cell_id}">')

            # Add outputs for code cells.
            outputs = cell.get("outputs", [])
            if outputs:
                output_texts = []
                for output in outputs:
                    output_text = self._format_notebook_output(output)
                    if output_text:
                        output_texts.append(output_text)
                if output_texts:
                    # Add newline before outputs, then the output content.
                    parts.append("\n" + "\n".join(output_texts))

        return "".join(parts)

    async def _read_notebook(self, file_path: Path) -> Dict[str, Any]:
        """Read a Jupyter notebook and return formatted content.

        Output format matches Claude Code Read tool:
        - Each cell wrapped in <cell id="cell-N">...</cell id="cell-N">
        - Markdown cells include <cell_type>markdown</cell_type>
        - Code cell outputs follow the cell closing tag

        Args:
            file_path: Path to the notebook file.

        Returns:
            Dictionary containing success status and formatted notebook content.
        """
        file_size = file_path.stat().st_size
        if file_size > self.MAX_NOTEBOOK_SIZE:
            return {
                "success": False,
                "error": (
                    f"Notebook file too large: {file_size} bytes "
                    f"(max: {self.MAX_NOTEBOOK_SIZE})"
                ),
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            cells = notebook.get("cells", [])
            formatted_cells = []

            for i, cell in enumerate(cells):
                formatted_cell = self._format_notebook_cell(cell, i)
                formatted_cells.append(formatted_cell)

            # Join cells with newline.
            content = "\n".join(formatted_cells)

            return {
                "success": True,
                "type": "notebook",
                "data": content,
                "path": str(file_path),
                "size": file_size,
                "cell_count": len(cells),
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid notebook JSON: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read notebook: {e}",
            }

    async def execute(
        self,
        params: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the read file operation.

        Args:
            params: Tool parameters containing 'path' and optional 'encoding'.
            context: Tool execution context.

        Returns:
            Dictionary containing success status and file content or error.
        """
        path = params.get("path")
        encoding = params.get("encoding", "utf-8")

        if not path:
            return {
                "success": False,
                "error": "Path parameter is required",
            }

        try:
            file_path = Path(path).expanduser().resolve()

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                }

            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"Not a file: {path}",
                }

            # Route to appropriate reader based on file type.
            if self._is_pdf_file(file_path):
                return await self._read_pdf(file_path)
            elif self._is_image_file(file_path):
                return await self._read_image(file_path)
            elif self._is_notebook_file(file_path):
                return await self._read_notebook(file_path)
            else:
                return await self._read_text(file_path, encoding)

        except UnicodeDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to decode file with encoding '{encoding}': {e}",
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied: {path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {e}",
            }
