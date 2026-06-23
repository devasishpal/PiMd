"""Reference DOCX loader — Pandoc-style template support.

Loads an existing ``.docx`` file and extracts its styles, headers,
footers, sections, numbering definitions, and page settings so that
new documents can be based on them.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from docx import Document as DocxDocument
from docx.oxml.ns import qn

logger = logging.getLogger("pimd")


class ReferenceDocError(Exception):
    """Raised when a reference document cannot be loaded or validated."""


class ReferenceDoc:
    """Load, validate, and inspect a reference DOCX template.

    Parameters
    ----------
    path : str | Path
        Path to the ``.docx`` file to use as a reference.

    Raises
    ------
    ReferenceDocError
        If the file does not exist, is not a valid DOCX, or is corrupted.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._doc: DocxDocument | None = None
        self._styles: list[str] | None = None
        self._sections: list[dict[str, Any]] | None = None
        self._numbering: list[dict[str, Any]] | None = None
        self._metadata: dict[str, str | None] | None = None
        self._headers: list[str] | None = None
        self._footers: list[str] | None = None
        self._page_settings: dict[str, Any] | None = None
        self._validate()
        self._load()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    @property
    def doc(self) -> DocxDocument:
        if self._doc is None:
            self._doc = DocxDocument(str(self._path))
        return self._doc

    @property
    def styles(self) -> list[str]:
        if self._styles is None:
            self._styles = self._extract_styles()
        return self._styles

    @property
    def metadata(self) -> dict[str, str | None]:
        if self._metadata is None:
            self._metadata = self._extract_metadata()
        return self._metadata

    @property
    def sections(self) -> list[dict[str, Any]]:
        if self._sections is None:
            self._sections = self._extract_sections()
        return self._sections

    @property
    def headers(self) -> list[str]:
        if self._headers is None:
            self._headers = self._extract_headers_footers("header")
        return self._headers

    @property
    def footers(self) -> list[str]:
        if self._footers is None:
            self._footers = self._extract_headers_footers("footer")
        return self._footers

    @property
    def numbering(self) -> list[dict[str, Any]]:
        if self._numbering is None:
            self._numbering = self._extract_numbering()
        return self._numbering

    @property
    def page_settings(self) -> dict[str, Any]:
        if self._page_settings is None:
            self._page_settings = self._extract_page_settings()
        return self._page_settings

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------

    def has_style(self, style_name: str) -> bool:
        """Check if a named style exists in the reference document."""
        return style_name in self.styles

    def get_style_names(self) -> list[str]:
        """Return a sorted list of all style names."""
        return sorted(self.styles)

    def inspect(self) -> dict[str, Any]:
        """Return a comprehensive inspection dictionary.

        Useful for the ``pimd template inspect`` CLI command.
        """
        return {
            "path": str(self._path.resolve()),
            "styles": self.get_style_names(),
            "style_count": len(self.styles),
            "headers": self.headers,
            "footers": self.footers,
            "sections": self.sections,
            "page_settings": self.page_settings,
            "metadata": self.metadata,
            "numbering_definitions": len(self.numbering),
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        path = self._path
        if not path.exists():
            raise ReferenceDocError(f"Reference DOCX not found: {path}")
        if not path.is_file():
            raise ReferenceDocError(f"Not a file: {path}")
        if path.suffix.lower() not in (".docx", ".dotx"):
            raise ReferenceDocError(
                f"Expected .docx or .dotx file, got: {path.suffix}"
            )
        try:
            with ZipFile(path) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise ReferenceDocError(
                        f"Not a valid DOCX (missing word/document.xml): {path}"
                    )
        except ReferenceDocError:
            raise
        except Exception as exc:
            raise ReferenceDocError(
                f"Corrupted or unreadable DOCX file: {path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Lazy-load the python-docx document on first access."""
        pass  # doc property handles lazy loading

    # ------------------------------------------------------------------
    # Extraction methods
    # ------------------------------------------------------------------

    def _extract_styles(self) -> list[str]:
        try:
            doc = self.doc
            return [s.name for s in doc.styles if s.name is not None]
        except Exception as exc:
            logger.warning("Failed to extract styles from reference doc: %s", exc)
            return []

    def _extract_metadata(self) -> dict[str, str | None]:
        try:
            cp = self.doc.core_properties
            return {
                "title": cp.title,
                "author": cp.author,
                "subject": cp.subject,
                "keywords": cp.keywords,
                "category": cp.category,
                "comments": cp.comments,
            }
        except Exception as exc:
            logger.warning("Failed to extract metadata: %s", exc)
            return {}

    def _extract_sections(self) -> list[dict[str, Any]]:
        sections_data: list[dict[str, Any]] = []
        try:
            for section in self.doc.sections:
                sections_data.append({
                    "page_width": self._emu_to_mm(section.page_width),
                    "page_height": self._emu_to_mm(section.page_height),
                    "top_margin": self._emu_to_mm(section.top_margin),
                    "bottom_margin": self._emu_to_mm(section.bottom_margin),
                    "left_margin": self._emu_to_mm(section.left_margin),
                    "right_margin": self._emu_to_mm(section.right_margin),
                    "orientation": self._get_orientation(section),
                })
        except Exception as exc:
            logger.warning("Failed to extract sections: %s", exc)
        return sections_data

    def _extract_headers_footers(self, kind: str) -> list[str]:
        results: list[str] = []
        try:
            doc = self.doc
            for section in doc.sections:
                hf = getattr(section, kind, None)
                if hf is None:
                    results.append("")
                    continue
                texts: list[str] = []
                for para in hf.paragraphs:
                    texts.append(para.text)
                results.append("\n".join(texts))
        except Exception as exc:
            logger.warning("Failed to extract %ss: %s", kind, exc)
        return results

    def _extract_numbering(self) -> list[dict[str, Any]]:
        numbering_list: list[dict[str, Any]] = []
        try:
            doc = self.doc
            num_part = doc.part.numbering_part
            if num_part is None:
                return numbering_list
            num_element = num_part._element
            for abstract_num in num_element.findall(qn("w:abstractNum")):
                num_id = abstract_num.get(qn("w:abstractNumId"))
                numbering_list.append({
                    "id": num_id,
                    "type": "abstract",
                })
            for num in num_element.findall(qn("w:num")):
                num_id = num.get(qn("w:numId"))
                abstract_ref = num.find(qn("w:abstractNumId"))
                abstract_id = abstract_ref.get(qn("w:val")) if abstract_ref is not None else None
                numbering_list.append({
                    "id": num_id,
                    "abstract_id": abstract_id,
                    "type": "concrete",
                })
        except Exception as exc:
            logger.warning("Failed to extract numbering: %s", exc)
        return numbering_list

    def _extract_page_settings(self) -> dict[str, Any]:
        settings: dict[str, Any] = {}
        try:
            sections = self.doc.sections
            if sections:
                section = sections[0]
                settings["page_width"] = self._emu_to_mm(section.page_width)
                settings["page_height"] = self._emu_to_mm(section.page_height)
                settings["orientation"] = self._get_orientation(section)
                settings["top_margin"] = self._emu_to_mm(section.top_margin)
                settings["bottom_margin"] = self._emu_to_mm(section.bottom_margin)
                settings["left_margin"] = self._emu_to_mm(section.left_margin)
                settings["right_margin"] = self._emu_to_mm(section.right_margin)
        except Exception as exc:
            logger.warning("Failed to extract page settings: %s", exc)
        return settings

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _emu_to_mm(emu: int | None) -> float:
        if emu is None:
            return 0.0
        return round(emu / 36000, 2)  # 1 mm = 36000 EMU

    @staticmethod
    def _get_orientation(section: Any) -> str:
        try:
            sect_pr = section._sectPr
            pg_sz = sect_pr.find(qn("w:pgSz"))
            if pg_sz is not None:
                orient = pg_sz.get(qn("w:orient"))
                if orient == "landscape":
                    return "landscape"
            return "portrait"
        except Exception:
            return "portrait"

    def __repr__(self) -> str:
        return f"ReferenceDoc({self._path.name}, {len(self.styles)} styles)"


# ======================================================================
# Validation helpers
# ======================================================================


def validate_reference_doc(path: str | Path) -> dict[str, Any]:
    """Validate a reference DOCX file.

    Returns a dict with ``valid``, ``warnings``, and ``errors`` keys.
    Never raises — all issues are captured in the result dict.

    Parameters
    ----------
    path : str | Path
        Path to the ``.docx`` file to validate.

    Returns
    -------
    dict
        ``{"valid": bool, "errors": list[str], "warnings": list[str]}``
    """
    result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}

    try:
        ref = ReferenceDoc(path)

        if not ref.styles:
            result["warnings"].append("No styles found in reference document")

        if not ref.sections:
            result["warnings"].append("No sections found in reference document")

        required = ["Normal", "Heading 1"]
        for style_name in required:
            if not ref.has_style(style_name):
                result["warnings"].append(
                    f"Common style '{style_name}' not found in reference document"
                )

        meta = ref.metadata
        if not meta.get("title"):
            pass  # title is optional

    except ReferenceDocError as exc:
        result["valid"] = False
        result["errors"].append(str(exc))
    except Exception as exc:
        result["valid"] = False
        result["errors"].append(f"Unexpected error: {exc}")

    if not result["valid"]:
        result["warnings"] = []

    return result


# ======================================================================
# Template packaging (Phase 13)
# ======================================================================


def install_template_package(archive_path: str | Path) -> Path:
    """Install a packaged template from a ``.zip`` archive.

    Expected archive structure::

        template/
        ├── reference.docx
        ├── template.toml (optional)
        └── preview.png (optional)

    The archive is extracted to ``~/.pimd/templates/<name>/``.

    Parameters
    ----------
    archive_path : str | Path
        Path to the ``.zip`` archive.

    Returns
    -------
    Path
        The destination directory where the template was installed.

    Raises
    ------
    ReferenceDocError
        If the archive is invalid, missing ``reference.docx``, or
        cannot be extracted.
    """
    import shutil
    import tempfile
    import zipfile

    archive = Path(archive_path)
    if not archive.exists():
        raise ReferenceDocError(f"Archive not found: {archive}")
    if archive.suffix.lower() not in (".zip",):
        raise ReferenceDocError(f"Expected a .zip file, got: {archive.suffix}")

    # Determine template name from archive filename
    template_name = archive.stem

    # Extract to temp directory first
    tmp_dir = Path(tempfile.mkdtemp(prefix="pimd_tpl_"))
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            # Check if files are in a subdirectory
            namelist = zf.namelist()
            # Find reference.docx
            ref_candidates = [n for n in namelist if n.endswith("reference.docx")]
            if not ref_candidates:
                raise ReferenceDocError(
                    f"Archive must contain a 'reference.docx' file. "
                    f"Found: {namelist[:20]}"
                )

            # Determine the common prefix
            ref_path = ref_candidates[0]
            prefix = ref_path.rsplit("reference.docx", 1)[0] if "reference.docx" in ref_path else ""

            zf.extractall(tmp_dir)

        # Find the extracted reference.docx
        extracted_ref = tmp_dir / ref_path
        if not extracted_ref.exists():
            raise ReferenceDocError(
                "Could not find reference.docx in extracted archive"
            )

        # Validate it's a real DOCX
        try:
            ref_doc = ReferenceDoc(extracted_ref)
        except ReferenceDocError as exc:
            raise ReferenceDocError(
                f"Invalid reference.docx in archive: {exc}"
            ) from exc

        # Create destination directory
        install_dir = Path.home() / ".pimd" / "templates" / template_name
        install_dir.mkdir(parents=True, exist_ok=True)

        # Copy reference.docx
        shutil.copy2(extracted_ref, install_dir / "reference.docx")

        # Copy template.toml if present
        toml_src = tmp_dir / prefix / "template.toml"
        if toml_src.exists():
            shutil.copy2(toml_src, install_dir / "template.toml")

        # Copy preview.png if present
        png_src = tmp_dir / prefix / "preview.png"
        if png_src.exists():
            shutil.copy2(png_src, install_dir / "preview.png")

        logger.info(
            "Template '%s' installed to %s (%d styles)",
            template_name,
            install_dir,
            len(ref_doc.styles),
        )

    except ReferenceDocError:
        raise
    except Exception as exc:
        raise ReferenceDocError(f"Failed to install template: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return install_dir
