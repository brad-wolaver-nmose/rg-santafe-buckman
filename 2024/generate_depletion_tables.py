#!/usr/bin/env python3
"""
Stream Depletion Tables from MODFLOW Post-Processor

This script processes MODFLOW binary output files (CY2024_ghb.flx and CY2024_riv.flx)
using the sfmodflx_2245 post-processor to generate stream depletion tables for the
2024 Buckman Well Field annual report.

Scientific Basis:
- Superposition model: MODFLOW calculates depletions from 1988-2024 pumping
- Analytical residuals: Core (2003) provides pre-1988 pumping effects
- Unit conversion: cfs × days × 86400 / 43560 = acre-feet
"""

import shutil
import sys
from pathlib import Path


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Source directory containing MODFLOW flux output files
MODFLOW_OUTPUT_DIR: str = "./output/modflow/2024/modflow/"

# Destination directory for post-processor input/output
DEPLETIONS_DIR: str = "./output/modflow/2024/depletions/"

# Output directory for generated XLSX tables
OUTPUT_DIR: str = "./output/depletion/"

# Validation directory
VALIDATION_DIR: str = "./validation/"

# Processing year
YEAR: int = 2024

# Flux file names (MODFLOW binary output)
RIV_FLUX_FILE: str = "CY2024_riv.flx"
GHB_FLUX_FILE: str = "CY2024_ghb.flx"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def print_error(what_failed: str, location: str, actual: str, expected: str, context: str) -> None:
    """
    Print forensic-quality error message following CLAUDE.md standards.

    Prints error information in a structured 5-element format for debugging.

    Args:
        what_failed: Description of what operation failed
        location: Where the failure occurred (file path, function name, etc.)
        actual: The actual value that was encountered
        expected: The expected value or condition
        context: Physical interpretation or additional context
    """
    print(f"ERROR: {what_failed}")
    print(f"  Location: {location}")
    print(f"  Actual: {actual}")
    print(f"  Expected: {expected}")
    print(f"  Physical context: {context}")


# =============================================================================
# US-001: Copy Flux Files to Post-Processor Directory
# =============================================================================

def copy_flux_files() -> bool:
    """
    Copy MODFLOW flux files to the post-processor directory.

    Scientific Basis:
    - sfmodflx_2245.exe reads flux files from its working directory
    - Flux files contain monthly boundary condition flows (river and GHB)
    - Files must be accessible to post-processor for depletion calculation

    Assumptions:
    1. Source flux files exist in MODFLOW_OUTPUT_DIR
    2. Destination directory DEPLETIONS_DIR exists
    3. Post-processor sfmodflx_2245.exe is in DEPLETIONS_DIR

    Returns:
        True if both files copied successfully, False otherwise

    Raises:
        None - prints forensic error messages and returns False on failure

    Example:
        >>> success = copy_flux_files()
        Copying flux files to post-processor directory...
          CY2024_riv.flx: 31484640 bytes -> output/modflow/2024/depletions/
          CY2024_ghb.flx: 31484640 bytes -> output/modflow/2024/depletions/
        Flux files copied successfully.
        >>> success
        True
    """
    print("Copying flux files to post-processor directory...")

    source_dir = Path(MODFLOW_OUTPUT_DIR)
    dest_dir = Path(DEPLETIONS_DIR)

    # List of files to copy: (filename, description)
    flux_files = [
        (RIV_FLUX_FILE, "river boundary flux"),
        (GHB_FLUX_FILE, "general head boundary flux"),
    ]

    # Check source directory exists
    if not source_dir.exists():
        print_error(
            "Source directory not found",
            str(source_dir.resolve()),
            "Directory does not exist",
            "Directory containing MODFLOW flux output files",
            "MODFLOW model must be run first to generate flux files"
        )
        return False

    # Check destination directory exists
    if not dest_dir.exists():
        print_error(
            "Destination directory not found",
            str(dest_dir.resolve()),
            "Directory does not exist",
            "Directory containing sfmodflx_2245.exe post-processor",
            "Post-processor directory must be set up before copying files"
        )
        return False

    # Copy each flux file
    for filename, description in flux_files:
        source_path = source_dir / filename
        dest_path = dest_dir / filename

        # Check source file exists
        if not source_path.exists():
            print_error(
                f"Source flux file not found",
                str(source_path.resolve()),
                "File does not exist",
                f"{description} file from MODFLOW run",
                f"MODFLOW must generate {filename} before post-processing"
            )
            return False

        # Copy file
        try:
            shutil.copy2(source_path, dest_path)
            file_size = dest_path.stat().st_size
            print(f"  {filename}: {file_size:,} bytes -> {dest_dir}/")
        except OSError as e:
            print_error(
                f"Failed to copy flux file",
                str(source_path.resolve()),
                f"OS error: {e}",
                f"Successful copy to {dest_dir}",
                f"Check file permissions and disk space"
            )
            return False

    # Verify both files exist after copy
    for filename, description in flux_files:
        dest_path = dest_dir / filename
        if not dest_path.exists():
            print_error(
                "Flux file missing after copy",
                str(dest_path.resolve()),
                "File does not exist",
                "File should exist after shutil.copy2()",
                "Filesystem error - file may have been deleted"
            )
            return False

    print("Flux files copied successfully.")
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """
    Main entry point for stream depletion table generation.

    Returns:
        Exit code: 0 if successful, 1 if any errors occurred
    """
    print(f"=== Stream Depletion Table Generator for {YEAR} ===")
    print()

    # US-001: Copy flux files
    if not copy_flux_files():
        print("\nFailed at US-001: Copy flux files")
        return 1

    print("\n=== US-001 Complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
