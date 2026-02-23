#!/usr/bin/env python3
"""
Build Word (.docx) documents from the spec suite markdown files.

Produces 3 documents:
  - SPEC_INDEX.docx                              (standalone index)
  - Domain_Specifications_DS-01_to_DS-06.docx    (6 domain specs)
  - Implementation_Specifications_IS-01_to_IS-12.docx (12 impl specs)

Two-stage pipeline:
  1. Pandoc converts concatenated markdown → .docx (headings, tables, code)
  2. python-docx post-processes wide tables onto landscape pages

Usage:
    python3 docs/specs/build_docx.py

Dependencies:
    - pandoc (apt install pandoc)
    - python-docx (pip install python-docx)
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches


# --- Configuration -----------------------------------------------------------

SPEC_DIR = Path(__file__).resolve().parent

# Ordered lists of input markdown files
DS_FILES = [
    "DS-01_Well_Production_Data.md",
    "DS-02_MODFLOW96_Model.md",
    "DS-03_Stream_Depletion_Analysis.md",
    "DS-04_Year_Chaining.md",
    "DS-05_Quality_Assurance.md",
    "DS-06_Regulatory_Compliance.md",
]

IS_FILES = [
    "IS-01_Project_Scaffold.md",
    "IS-02_CSV_Ingestion_Table2.md",
    "IS-03_Table1_Chaining.md",
    "IS-04_WEL_File_Management.md",
    "IS-05_MODFLOW_Execution.md",
    "IS-06_Post_Processor.md",
    "IS-07_Stream_Depletion_Library.md",
    "IS-08_Table3_Generation.md",
    "IS-09_Tables4_5_Generation.md",
    "IS-10_Test_Suite_Layers_0_1.md",
    "IS-11_Validation_Framework.md",
    "IS-12_Provenance_Compliance.md",
]

# Output document definitions: (output_filename, title, input_files, include_toc)
DOCUMENTS = [
    (
        "SPEC_INDEX.docx",
        "Buckman Wellfield Pipeline — Specification Index",
        ["SPEC_INDEX.md"],
        False,
    ),
    (
        "Domain_Specifications_DS-01_to_DS-06.docx",
        "Buckman Wellfield Pipeline — Domain Specifications (DS-01 to DS-06)",
        DS_FILES,
        True,
    ),
    (
        "Implementation_Specifications_IS-01_to_IS-12.docx",
        "Buckman Wellfield Pipeline — Implementation Specifications (IS-01 to IS-12)",
        IS_FILES,
        True,
    ),
]

# Tables with this many columns or more get landscape pages
WIDE_TABLE_THRESHOLD = 5


# --- Stage 1: Pandoc conversion ----------------------------------------------


def concatenate_markdown(filenames: list[str]) -> str:
    """
    Read and concatenate markdown files with page breaks between them.

    Args:
        filenames: List of .md filenames in docs/specs/.

    Returns:
        Combined markdown string with \\newpage separators.
    """
    sections = []
    for fname in filenames:
        path = SPEC_DIR / fname
        if not path.exists():
            print(f"  WARNING: {fname} not found, skipping")
            continue
        sections.append(path.read_text(encoding="utf-8"))
    return "\n\n\\newpage\n\n".join(sections)


def run_pandoc(md_text: str, output_path: Path, title: str, include_toc: bool) -> None:
    """
    Convert markdown text to .docx via pandoc.

    Args:
        md_text: Combined markdown content.
        output_path: Where to write the .docx file.
        title: Document title metadata.
        include_toc: Whether to include a table of contents.

    Raises:
        RuntimeError: If pandoc is not found or returns an error.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(md_text)
        tmp_path = Path(tmp.name)

    cmd = [
        "pandoc",
        str(tmp_path),
        "-o", str(output_path),
        "--from", "markdown",
        "--to", "docx",
        f"--metadata=title:{title}",
    ]
    if include_toc:
        cmd.extend(["--toc", "--toc-depth=2"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("pandoc not found — install with: sudo apt install pandoc")
    except subprocess.TimeoutExpired:
        raise RuntimeError("pandoc conversion timed out (120s)")
    finally:
        tmp_path.unlink(missing_ok=True)


# --- Stage 2: python-docx landscape post-processing --------------------------


def set_landscape_for_wide_tables(docx_path: Path) -> int:
    """
    Post-process a .docx file to put wide tables on landscape pages.

    For each table with >= WIDE_TABLE_THRESHOLD columns:
      - The section containing the table is set to landscape (11" x 8.5")

    This modifies the file in place.

    Args:
        docx_path: Path to the .docx file.

    Returns:
        Number of tables converted to landscape.
    """
    doc = Document(str(docx_path))
    landscape_count = 0

    for table in doc.tables:
        # Count columns from the first row
        if not table.rows:
            continue
        num_cols = len(table.rows[0].cells)

        if num_cols >= WIDE_TABLE_THRESHOLD:
            # Find which section this table belongs to by checking the
            # table's position relative to section breaks.
            # python-docx approach: we set the section that contains the
            # table to landscape orientation.
            #
            # Since pandoc produces a single-section document by default,
            # we need to add section breaks around wide tables.
            # A simpler and more reliable approach: just set all sections
            # to landscape if the doc has wide tables, or work with the
            # document body XML directly.
            landscape_count += 1

    if landscape_count == 0:
        return 0

    # Strategy: If any wide tables exist, set the entire document to
    # landscape. This is the most reliable approach — inserting per-table
    # section breaks via python-docx XML manipulation is fragile and can
    # corrupt documents. For specs that mix narrow and wide tables, the
    # landscape orientation works fine for all content.
    for section in doc.sections:
        section.orientation = WD_ORIENT.LANDSCAPE
        # Swap page dimensions: 11" wide x 8.5" tall
        section.page_width = Inches(11)
        section.page_height = Inches(8.5)

    doc.save(str(docx_path))
    return landscape_count


# --- Main --------------------------------------------------------------------


def build_all() -> None:
    """Build all 3 .docx documents from the spec markdown files."""
    print("Building .docx documents from spec suite...\n")

    for output_name, title, input_files, include_toc in DOCUMENTS:
        output_path = SPEC_DIR / output_name
        print(f"  {output_name}")
        print(f"    Sources: {len(input_files)} file(s)")

        # Stage 1: Concatenate and convert via pandoc
        md_text = concatenate_markdown(input_files)
        run_pandoc(md_text, output_path, title, include_toc)

        # Stage 2: Post-process for landscape pages
        wide_count = set_landscape_for_wide_tables(output_path)
        if wide_count > 0:
            print(f"    Landscape: {wide_count} wide table(s) → full document landscape")
        else:
            print(f"    Landscape: no wide tables, portrait orientation")

        size_kb = output_path.stat().st_size / 1024
        print(f"    Output: {size_kb:.0f} KB")
        print()

    print("Done. Generated files:")
    for output_name, *_ in DOCUMENTS:
        print(f"  docs/specs/{output_name}")


if __name__ == "__main__":
    try:
        build_all()
    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
